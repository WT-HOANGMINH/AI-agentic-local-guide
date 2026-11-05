"""POST /agent/chat - giữ đường dẫn cũ cho frontend cũ, nhưng dùng CHUNG bộ não hội thoại với /api/ai-guide.
(Trước đây route này gọi chat_service.answer() nên trả lời cứng kiểu "Ở Đà Nẵng bạn có thể dùng Grab/Be...")."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.routes.ai_guide import (
    _apply_llm,
    _compute_request,
    _get_state,
    _meta,
    _full_text,
    _record_turn,
)

router = APIRouter(prefix="/agent", tags=["Agent Chat"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]*$")
    # Vi tri nguoi dung (tuy chon) de tim "gan toi" va chi duong
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


@router.post("/chat")
async def chat(payload: ChatIn):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Vui long nhap cau hoi.")
    sid, st = _get_state(payload.session_id)
    try:
        reply = await _compute_request(
            message, st, payload.latitude, payload.longitude, None
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Khong the xu ly yeu cau AI luc nay.")
    answer = await run_in_threadpool(_apply_llm, message, st, reply)
    _record_turn(st, message, answer)
    return {
        "reply": _full_text({**reply, "text": answer}),
        "intent": reply["intent"],
        "confidence": round(float(reply["confidence"]), 3),
        "session_id": sid,
        "steps": reply["steps"],
        **_meta(reply),
    }
