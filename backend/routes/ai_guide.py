"""AI Local Guide: tự huấn luyện (intent + slot) + planner + điều phối hội thoại.
Gemini (nếu có key) chỉ dùng để DIỄN ĐẠT LẠI câu trả lời đã được xác minh từ dữ liệu địa điểm."""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from backend.database import SessionLocal
from backend.services.dialogue import State, respond
from backend.services.intent_service import predict_intent
from backend.services.llm_service import is_gemini_configured, stream_grounded_answer
from backend.services.slot_service import model_ready

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ai-guide",
    tags=["AI Local Guide"],
)

SESSIONS: dict[str, State] = {}      # trong RAM: khởi động lại server là mất lịch trình đang sửa
MAX_SESSIONS = 500

if not model_ready():
    print("[AI Guide] CANH BAO: chua co training/models/slot_tagger.joblib "
          "-> chay generate_slots.py va train_slots.py de bo trich thong tin hoat dong.")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Cau hoi cua nguoi dung")
    session_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]*$")
    # Vị trí người dùng (tùy chọn, chỉ có khi họ bấm cho phép chia sẻ vị trí)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class GuideRequest(ChatRequest):
    # Giu tuong thich API cu (frontend/postman cu); hien khong dung de loc.
    max_price: int = Field(default=5, ge=1, le=5)


class ResetRequest(BaseModel):
    session_id: str


def _get_state(session_id: str | None) -> tuple[str, State]:
    sid = session_id or uuid.uuid4().hex
    if sid not in SESSIONS and len(SESSIONS) >= MAX_SESSIONS:
        SESSIONS.pop(next(iter(SESSIONS)))
    return sid, SESSIONS.setdefault(sid, State())


def _compute(message: str, st: State, lat=None, lng=None, on_step=None) -> dict:
    prediction = predict_intent(message)
    db = SessionLocal()
    try:
        reply = respond(st, message, prediction["intent"], prediction["confidence"], db,
                        lat=lat, lng=lng, on_step=on_step)
    finally:
        db.close()
    reply["intent"] = prediction["intent"]
    reply["confidence"] = prediction["confidence"]
    return reply


def full_text(reply: dict) -> str:
    """Câu trả lời + lời kết (nếu có)."""
    if reply.get("closing"):
        return f"{reply['text']}\n\n{reply['closing']}"
    return reply["text"]


def _meta(reply: dict) -> dict:
    meta = {
        "status": reply["status"],
        "suggestions": reply["suggestions"],
        "links": reply.get("links", []),
    }
    if reply.get("suggestion_mode"):
        meta["suggestion_mode"] = reply["suggestion_mode"]
        meta["multi_template"] = reply.get("multi_template")
    return meta


def _clean(message: str) -> str:
    message = message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Vui long nhap cau hoi.")
    return message


@router.post("/chat")
async def chat(req: ChatRequest):
    message = _clean(req.message)
    sid, st = _get_state(req.session_id)
    try:
        reply = await run_in_threadpool(_compute, message, st, req.latitude, req.longitude)
    except Exception as exc:
        logger.exception("AI guide error")
        raise HTTPException(status_code=500, detail="Khong the xu ly yeu cau AI luc nay.")
    return {
        "success": True,
        "reply": full_text(reply),
        "steps": reply["steps"],
        "intent": reply["intent"],
        "confidence": reply["confidence"],
        "session_id": sid,
        **_meta(reply),
    }


@router.post("/ask")
async def ask_ai_guide(req: GuideRequest):
    """Dinh dang tra ve giong ban cu de frontend/Postman cu van chay."""
    message = _clean(req.message)
    sid, st = _get_state(req.session_id)
    try:
        reply = await run_in_threadpool(_compute, message, st, req.latitude, req.longitude)
    except Exception:
        logger.exception("AI guide error")
        raise HTTPException(status_code=500, detail="Khong the xu ly yeu cau AI luc nay.")
    text = full_text(reply)
    return {
        "success": True,
        "message": text,
        "ai_answer": text,
        "intent": reply["intent"],
        "confidence": reply["confidence"],
        "places": [],
        "steps": reply["steps"],
        "session_id": sid,
        **_meta(reply),
    }


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@router.post("/chat-stream")
async def chat_stream(req: ChatRequest):
    message = _clean(req.message)
    sid, st = _get_state(req.session_id)

    async def gen():
        yield _sse({"type": "session", "session_id": sid})
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_step(text: str):          # được gọi từ luồng xử lý, đẩy tiến trình THẬT về giao diện
            loop.call_soon_threadsafe(queue.put_nowait, text)

        task = asyncio.ensure_future(
            run_in_threadpool(_compute, message, st, req.latitude, req.longitude, on_step)
        )
        try:
            while not (task.done() and queue.empty()):
                try:
                    text = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                yield _sse({"type": "step", "text": text})
            reply = await task
            meta = _meta(reply)

            use_llm = reply["status"] != "needs_clarification" and is_gemini_configured()
            if not use_llm:
                if reply["status"] != "needs_clarification":
                    logger.info("Gemini chua duoc cau hinh: tra loi bang du lieu dia phuong")
                yield _sse({"type": "result", "text": full_text(reply), "streaming": False, **meta})
            else:
                yield _sse({"type": "step", "text": "Đang hoàn thiện câu trả lời..."})
                emitted = False
                try:
                    async for token in iterate_in_threadpool(
                        stream_grounded_answer(message, reply["text"])
                    ):
                        emitted = True
                        yield _sse({"type": "token", "text": token})
                except Exception:
                    logger.exception("Gemini streaming failed")
                    if emitted:
                        yield _sse({"type": "error",
                                    "text": "Luồng trả lời bị gián đoạn. Vui lòng thử lại."})
                        emitted = None
                    else:      # chưa có chữ nào: dùng câu trả lời từ dữ liệu địa phương
                        yield _sse({"type": "result", "text": full_text(reply),
                                    "streaming": False, **meta})
                        emitted = None
                if emitted:
                    if reply.get("closing"):
                        yield _sse({"type": "token", "text": "\n\n" + reply["closing"]})
                    yield _sse({"type": "result", **meta})
                elif emitted is False:       # Gemini chạy xong nhưng không trả chữ nào
                    yield _sse({"type": "result", "text": full_text(reply),
                                "streaming": False, **meta})
            yield _sse({"type": "done"})
        except Exception:
            logger.exception("AI stream request failed")
            yield _sse({"type": "error", "text": "Mình gặp sự cố, bạn thử lại giúp mình nhé."})
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/reset")
async def reset(req: ResetRequest):
    SESSIONS.pop(req.session_id, None)
    return {"success": True}
