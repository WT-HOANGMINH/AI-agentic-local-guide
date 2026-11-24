"""Legacy /agent/chat route backed by the shared hybrid AI Guide dialogue."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.routes.ai_guide import (
    _apply_llm,
    _compute_request,
    _full_text,
    _get_state,
    _meta,
    _record_turn,
)

router = APIRouter(prefix="/agent", tags=["Agent Chat"])


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]*$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


@router.post("/chat")
async def chat(payload: ChatIn):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Vui lòng nhập câu hỏi.")
    sid, state = _get_state(payload.session_id)
    reply = await _compute_request(
        message,
        state,
        payload.latitude,
        payload.longitude,
        None,
    )
    answer = await run_in_threadpool(_apply_llm, message, state, reply)
    _record_turn(state, message, answer)
    return {
        "reply": _full_text({**reply, "text": answer}),
        "intent": reply["intent"],
        "confidence": round(float(reply["confidence"]), 3),
        "session_id": sid,
        "steps": reply["steps"],
        **_meta(reply),
    }