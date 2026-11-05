"""
DanangGuide AI Guide API
- Compatible with the V2 dialogue service: respond(..., choice=...)
- Keeps the existing endpoints: /chat, /ask, /chat-stream, /reset
- Keeps optional GPS coordinates and legacy max_price field
- Uses Gemini when configured, with local dialogue as a no-key fallback
- Does not fabricate tool/progress events
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import OrderedDict
from threading import RLock
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from backend.database import SessionLocal
from backend.services.dialogue import State, respond
from backend.services.intent_service import predict_intent
from backend.services.llm_service import (
    analyze_request,
    ask_llm,
    is_gemini_configured,
    stream_grounded_answer,
)
from backend.services.slot_service import model_ready

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-guide", tags=["AI Local Guide"])

# RAM session store: simple single-process session continuity.
# For production/multiple workers, move this to Redis or a database.
MAX_SESSIONS = 500
SESSION_TTL_SECONDS = 60 * 60 * 6
SESSIONS: OrderedDict[str, tuple[State, float]] = OrderedDict()
_SESSIONS_LOCK = RLock()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(
        default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]*$"
    )
    # GPS is optional and should only be sent after the user grants permission.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    # V2 interactive clarification payload, e.g.
    # {"slot": "days", "values": [2]}
    choice: dict[str, Any] | None = None


class GuideRequest(ChatRequest):
    # Kept for compatibility with older clients.
    max_price: int = Field(default=5, ge=1, le=5)


class ResetRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)


def _clean_message(message: str) -> str:
    value = (message or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="Vui lòng nhập câu hỏi.")
    return value


async def _compute_request(message, state, latitude, longitude, choice):
    args = [_compute, message, state, latitude, longitude]
    if choice is not None:
        args.append(choice)
    return await run_in_threadpool(*args)


def _prune_sessions(now: float) -> None:
    expired = [
        sid for sid, (_, last_seen) in SESSIONS.items()
        if now - last_seen > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        SESSIONS.pop(sid, None)

    while len(SESSIONS) > MAX_SESSIONS:
        SESSIONS.popitem(last=False)


def _get_state(session_id: str | None) -> tuple[str, State]:
    now = time.monotonic()
    with _SESSIONS_LOCK:
        _prune_sessions(now)
        sid = session_id or uuid.uuid4().hex
        entry = SESSIONS.get(sid)

        if entry is None:
            state = State()
        else:
            state = entry[0]

        SESSIONS[sid] = (state, now)
        SESSIONS.move_to_end(sid)
        _prune_sessions(now)
        return sid, state


def _normalise_reply(reply: Any) -> dict[str, Any]:
    """Normalize dialogue output so API clients always receive stable fields."""
    if not isinstance(reply, dict):
        raise TypeError("dialogue.respond() must return a dictionary")

    text = reply.get("text") or reply.get("reply") or reply.get("message") or ""
    if not isinstance(text, str):
        text = str(text)

    steps = reply.get("steps") or []
    suggestions = reply.get("suggestions") or []
    links = reply.get("links") or []

    # Avoid leaking malformed values to JSON clients.
    if not isinstance(steps, list):
        steps = []
    if not isinstance(suggestions, list):
        suggestions = []
    if not isinstance(links, list):
        links = []

    return {
        **reply,
        "text": text,
        "steps": steps,
        "suggestions": suggestions,
        "links": links,
        "status": reply.get("status", "ok"),
    }


def _compute(
    message: str,
    state: State,
    latitude: float | None = None,
    longitude: float | None = None,
    choice: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Let Gemini route requests when configured; otherwise use the local classifier,
    then execute only the existing dialogue capabilities.

    In V2, dialogue.respond signature is:
        respond(st, msg, intent, conf, db, choice=None)

    GPS values are stored in State.pos for compatibility with the existing
    nearby-search flow; dialogue V2 itself may or may not use them.
    """
    if latitude is not None and longitude is not None:
        state.pos = (latitude, longitude)

    analysis_failed = False
    if is_gemini_configured():
        try:
            analysis = analyze_request(message, history=state.history)
        except Exception as exc:
            analysis_failed = True
            logger.warning(
                "LLM request analysis failed (%s); using local intent classifier.",
                type(exc).__name__,
            )
            analysis = None
    else:
        analysis = None

    if analysis is None:
        prediction = predict_intent(message)
        if not isinstance(prediction, dict):
            raise TypeError("predict_intent() must return a dictionary")
        intent = prediction.get("intent", "unclear")
        confidence = float(prediction.get("confidence", 0.0) or 0.0)
    else:
        intent = (
            analysis.intent
            if analysis.requires_local_data
            else "general"
        )
        confidence = analysis.confidence

    if intent == "general":
        reply = _normalise_reply({
            "text": "",
            "steps": [],
            "suggestions": [],
            "links": [],
            "status": "completed",
        })
        reply["intent"] = intent
        reply["confidence"] = confidence
        return reply

    db = SessionLocal()
    try:
        raw_reply = respond(
            state,
            message,
            intent,
            confidence,
            db,
            choice=choice,
            lat=latitude,
            lng=longitude,
        )
        reply = _normalise_reply(raw_reply)
    finally:
        db.close()

    reply["intent"] = intent
    reply["confidence"] = confidence
    if analysis_failed:
        reply["_skip_llm"] = True
    return reply


def _apply_llm(message: str, state: State, reply: dict[str, Any]) -> str:
    if reply.get("_skip_llm") or not is_gemini_configured():
        return reply["text"]
    if reply.get("status") == "needs_clarification" or reply.get("intent") == "greeting":
        return reply["text"]
    if reply.get("intent") in {"general", "out_of_scope", "unclear"}:
        answer = ask_llm(message, history=state.history)
    else:
        answer = ask_llm(
            message,
            history=state.history,
            grounded_answer=reply["text"],
        )
    reply["text"] = answer
    return answer


def _full_text(reply: dict[str, Any]) -> str:
    text = reply.get("text", "")
    closing = reply.get("closing")
    if closing and closing not in text:
        return f"{text}\n\n{closing}"
    return text


def _meta(reply: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": reply.get("status", "ok"),
        "suggestions": reply.get("suggestions", []),
        "links": reply.get("links", []),
    }
    for key in ("suggestion_mode", "multi_template", "confirm_label"):
        if reply.get(key) is not None:
            result[key] = reply[key]
    if reply.get("itinerary") is not None:
        result["itinerary"] = reply["itinerary"]
    return result


def _record_turn(state: State, message: str, answer: str) -> None:
    state.history.extend([
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer},
    ])
    del state.history[:-12]


def _response_payload(reply: dict[str, Any], session_id: str) -> dict[str, Any]:
    answer = _full_text(reply)
    return {
        "success": True,
        "reply": answer,
        "message": answer,       # legacy client compatibility
        "ai_answer": answer,     # legacy client compatibility
        "steps": reply["steps"],
        "intent": reply["intent"],
        "confidence": reply["confidence"],
        "session_id": session_id,
        "places": reply.get("places", []),
        **_meta(reply),
    }


@router.post("/chat")
async def chat(req: ChatRequest):
    message = _clean_message(req.message)
    sid, state = _get_state(req.session_id)

    try:
        reply = await _compute_request(
            message,
            state,
            req.latitude,
            req.longitude,
            req.choice,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("AI Guide /chat failed")
        raise HTTPException(
            status_code=500,
            detail="Không thể xử lý yêu cầu lúc này. Vui lòng thử lại.",
        ) from exc

    answer = await run_in_threadpool(_apply_llm, message, state, reply)
    _record_turn(state, message, answer)
    return _response_payload(reply, sid)


@router.post("/ask")
async def ask_ai_guide(req: GuideRequest):
    """Legacy endpoint retained for older frontend/Postman integrations."""
    message = _clean_message(req.message)
    sid, state = _get_state(req.session_id)

    try:
        reply = await _compute_request(
            message,
            state,
            req.latitude,
            req.longitude,
            req.choice,
        )
    except Exception as exc:
        logger.exception("AI Guide /ask failed")
        raise HTTPException(
            status_code=500,
            detail="Không thể xử lý yêu cầu lúc này. Vui lòng thử lại.",
        ) from exc

    answer = await run_in_threadpool(_apply_llm, message, state, reply)
    _record_turn(state, message, answer)
    return _response_payload(reply, sid)


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"


@router.post("/chat-stream")
async def chat_stream(req: ChatRequest):
    """
    SSE-compatible endpoint.

    The current dialogue engine returns a completed response rather than
    yielding tokens. Therefore this endpoint sends actual completed steps and
    answer content; it deliberately does not invent live tool progress or
    pretend that local text generation is token streaming.
    """
    message = _clean_message(req.message)
    sid, state = _get_state(req.session_id)

    async def event_generator():
        yield _sse({"type": "session", "session_id": sid})

        try:
            reply = await _compute_request(
                message,
                state,
                req.latitude,
                req.longitude,
                req.choice,
            )

            answer_parts = []
            streamed_model = False
            if is_gemini_configured():
                if (
                    reply.get("_skip_llm")
                    or reply.get("status") == "needs_clarification"
                    or reply.get("intent") == "greeting"
                ):
                    answer_parts.append(reply["text"])
                elif reply.get("intent") in {"general", "out_of_scope", "unclear"}:
                    answer_parts.append(await run_in_threadpool(
                        ask_llm, message, state.history
                    ))
                else:
                    stream = stream_grounded_answer(
                        message,
                        reply["text"],
                        history=state.history,
                    )
                    async for part in iterate_in_threadpool(stream):
                        answer_parts.append(part)
                        streamed_model = True
                        yield _sse({"type": "token", "text": part, "streaming": True})
                reply["text"] = "".join(answer_parts).strip()
                if not reply["text"]:
                    raise RuntimeError("LLM không tạo được câu trả lời.")

            # Steps are emitted after dialogue execution because respond()
            # currently returns a list and has no live on_step callback.
            for step in reply.get("steps", []):
                yield _sse({"type": "step", "text": str(step)})

            if reply.get("links"):
                yield _sse({"type": "links", "items": reply["links"]})

            if reply.get("suggestions"):
                yield _sse({
                    "type": "suggestions",
                    "mode": reply.get("suggestion_mode", "single"),
                    "options": reply["suggestions"],
                    "confirm_label": reply.get("confirm_label"),
                })

            answer = _full_text(reply)

            # Retain V1-style result metadata for clients that consume it.
            yield _sse({
                "type": "result",
                "text": answer,
                "streaming": streamed_model,
                "intent": reply.get("intent"),
                "confidence": reply.get("confidence"),
                **_meta(reply),
            })
            _record_turn(state, message, answer)
            yield _sse({"type": "done", "session_id": sid})

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI Guide /chat-stream failed")
            yield _sse({
                "type": "error",
                "text": "Mình gặp sự cố khi xử lý yêu cầu. Bạn thử lại giúp mình nhé.",
            })
            yield _sse({"type": "done", "session_id": sid})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/reset")
async def reset(req: ResetRequest):
    with _SESSIONS_LOCK:
        SESSIONS.pop(req.session_id, None)
    return {"success": True, "session_id": req.session_id}


@router.get("/health")
async def health():
    """Lightweight diagnostic endpoint; does not query the database."""
    ready = False
    try:
        ready = bool(model_ready())
    except Exception:
        logger.exception("Could not check slot model readiness")

    return {
        "success": True,
        "service": "ai-guide",
        "slot_model_ready": ready,
        "session_storage": "memory",
        "llm_enabled": is_gemini_configured(),
        "note": "LLM contextualizes replies when configured; local data and planning remain the source of verified travel facts.",
    }


if not model_ready():
    logger.warning(
        "Slot model is not ready. Run training/src/generate_slots.py "
        "and training/src/train_slots.py before testing full dialogue extraction."
    )
