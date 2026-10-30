"""POST /agent/chat - giữ đường dẫn cũ cho frontend cũ, nhưng dùng CHUNG bộ não hội thoại với /api/ai-guide.
(Trước đây route này gọi chat_service.answer() nên trả lời cứng kiểu "Ở Đà Nẵng bạn có thể dùng Grab/Be...")."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.routes.ai_guide import _compute, _get_state, _meta, full_text

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
        reply = await run_in_threadpool(_compute, message, st, payload.latitude, payload.longitude)
    except Exception:
        raise HTTPException(status_code=500, detail="Khong the xu ly yeu cau AI luc nay.")
    return {
        "reply": full_text(reply),
        "intent": reply["intent"],
        "confidence": round(float(reply["confidence"]), 3),
        "session_id": sid,
        "steps": reply["steps"],
        **_meta(reply),
    }
