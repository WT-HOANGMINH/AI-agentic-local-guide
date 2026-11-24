"""
DanangGuide AI Guide API
- Compatible with the V2 dialogue service: respond(..., choice=...)
- Keeps the existing endpoints: /chat, /ask, /chat-stream, /reset, /health
- Keeps optional GPS coordinates and legacy max_price field
- Hybrid routing: the trained local models (LinearSVC intent + slot tagger) run first; the local
  Ollama LLM is only consulted when the local classifier is unsure or the message is a short
  follow-up, and to phrase answers naturally from verified data
- If Ollama is unavailable, slow or returns something unsafe, the verified local answer is used
- Does not fabricate tool/progress events
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from collections import OrderedDict
from threading import RLock
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from backend.database import SessionLocal
from backend.services import nlg
from backend.services import dialogue
from backend.services.dialogue import State, respond
from backend.services.intent_service import predict_intent
from backend.services.llm_service import (
    OllamaError,
    analyze_request,
    ask_llm,
    check_ollama_connection,
    is_ollama_available,
    stream_general_answer,
    stream_grounded_answer,
)
from backend.services.llm_text import contains_unexpected_script, grounded_output_is_safe
from backend.services.slot_service import model_ready, strip_accents
from backend.services.weather_chat import looks_like_weather, maybe_weather_reply

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-guide", tags=["AI Local Guide"])

# RAM session store: simple single-process session continuity.
# For production/multiple workers, move this to Redis or a database.
MAX_SESSIONS = 500
SESSION_TTL_SECONDS = 60 * 60 * 6
SESSIONS: OrderedDict[str, tuple[State, float]] = OrderedDict()
_SESSIONS_LOCK = RLock()

# --- LLM routing / rewriting policy (xem .env.example) ---------------------------------
def _env_number(name: str, default, cast):
    try:
        return cast(os.getenv(name) or default)
    except ValueError:
        logger.warning("Giá trị %s không hợp lệ; dùng mặc định %s.", name, default)
        return default


# Chỉ hỏi Ollama phân tích ý định khi mô hình ML cục bộ có độ tin cậy dưới ngưỡng này.
ROUTER_CONFIDENCE_THRESHOLD = _env_number("OLLAMA_ROUTER_THRESHOLD", 0.7, float)
# Tin nhắn ngắn (<= số từ này) trong hội thoại đang diễn ra có thể là câu nối tiếp ("còn chỗ nào khác không?").
SHORT_FOLLOWUP_WORDS = 5
# Dữ liệu đã xác minh dài hơn ngưỡng này được giữ nguyên văn thay vì nhờ mô hình nhỏ viết lại.
REWRITE_MAX_CHARS = _env_number("OLLAMA_REWRITE_MAX_CHARS", 1500, int)

GENERAL_INTENTS = {"general", "out_of_scope", "unclear"}

_GENERAL_FALLBACK = {
    "vi": (
        "Mình chưa trả lời được câu này vì trợ lý AI đang không khả dụng. "
        "Bạn thử hỏi về địa điểm, quán ăn, quán cà phê, lịch trình hoặc thời tiết ở Đà Nẵng nhé."
    ),
    "en": (
        "I can't answer that right now because the AI assistant is unavailable. "
        "Try asking about places, food, cafes, itineraries or the weather in Da Nang."
    ),
}


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

    @model_validator(mode="after")
    def validate_coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self


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


# ---------------------------------------------------------------------------
# Định tuyến ý định: ML cục bộ trước, Ollama bổ trợ
# ---------------------------------------------------------------------------

def _local_intent(message: str) -> tuple[str | None, float]:
    """Mô hình ML đã huấn luyện (LinearSVC + TF-IDF). Trả (None, 0) nếu mô hình không dùng được."""
    try:
        prediction = predict_intent(message)
        if not isinstance(prediction, dict):
            raise TypeError("predict_intent() must return a dictionary")
        return (
            str(prediction.get("intent") or "unclear"),
            float(prediction.get("confidence", 0.0) or 0.0),
        )
    except Exception as exc:
        logger.warning("Local intent classifier unavailable (%s: %s).", type(exc).__name__, exc)
        return None, 0.0


def _should_route_with_llm(
    message: str, state: State, local_intent: str | None, local_conf: float
) -> bool:
    """Chỉ tốn một lần gọi LLM khi nó thật sự giúp được."""
    if not is_ollama_available():
        return False
    if local_intent is None:
        return True
    words = len(message.split())
    # Dialogue manager tự hiểu câu trả lời cho câu hỏi nó vừa đặt (số ngày, sở thích...).
    if state.pending_for and words <= 8:
        return False
    if local_conf < ROUTER_CONFIDENCE_THRESHOLD:
        return True
    return bool(state.history) and words <= SHORT_FOLLOWUP_WORDS and local_conf < 0.9


def _route(message: str, state: State) -> tuple[str, float, str]:
    """Trả về (intent, confidence, nguồn: 'local' | 'ollama')."""
    local_intent, local_conf = _local_intent(message)

    if _should_route_with_llm(message, state, local_intent, local_conf):
        try:
            analysis = analyze_request(message, history=state.history)
        except Exception as exc:
            logger.warning(
                "Ollama request analysis failed (%s: %s); using local classifier.",
                type(exc).__name__, exc,
            )
        else:
            # Ý định khác 'general' luôn là khả năng cục bộ (kể cả khi mô hình nhỏ quên đặt
            # requires_local_data) để dữ liệu địa điểm vẫn do backend cung cấp, không do LLM bịa.
            return analysis.intent, analysis.confidence, "ollama"

    return local_intent or "unclear", local_conf, "local"


def _compute(
    message: str,
    state: State,
    latitude: float | None = None,
    longitude: float | None = None,
    choice: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Route the request (local ML first, Ollama when needed), then execute only the existing
    dialogue capabilities.

    In V2, dialogue.respond signature is:
        respond(st, msg, intent, conf, db, choice=None)

    GPS values are stored in State.pos for compatibility with the existing
    nearby-search flow; dialogue V2 itself may or may not use them.
    """
    if latitude is not None and longitude is not None:
        state.pos = (latitude, longitude)

    intent, confidence, router_source = _route(message, state)

    weather_requested = intent == "weather" or looks_like_weather(message)
    if not weather_requested and dialogue.is_current_location_request(message):
        intent = dialogue.current_location_intent(message, intent)
        confidence = max(confidence, 0.95)
        router_source = "local"
    if weather_requested:
        intent = "weather"

    if intent == "general" and not weather_requested:
        # Không cần dữ liệu địa phương: Ollama sẽ trả lời; nếu không dùng được thì giữ câu dự phòng này.
        lang = nlg.detect_lang(message, state.lang)
        reply = _normalise_reply({
            "text": _GENERAL_FALLBACK.get(lang, _GENERAL_FALLBACK["vi"]),
            "steps": [],
            "suggestions": [],
            "links": [],
            "status": "completed",
        })
        reply["intent"] = intent
        reply["confidence"] = confidence
        reply["router"] = router_source
        return reply

    db = SessionLocal()
    try:
        cue = strip_accents(message)
        itinerary_weather = weather_requested and bool(state.plan) and any(
            phrase in cue for phrase in ("lich trinh", "ke hoach", "neu mua")
        )
        if weather_requested and not itinerary_weather:
            raw_reply = maybe_weather_reply(message, intent, state, db)
            if raw_reply is None:
                raise RuntimeError("Weather request was not handled by the weather service.")
        else:
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
    reply["router"] = router_source
    return reply


# ---------------------------------------------------------------------------
# Diễn đạt câu trả lời bằng Ollama (có kiểm tra an toàn và dự phòng)
# ---------------------------------------------------------------------------

def _llm_mode(reply: dict[str, Any]) -> str:
    """'skip' = giữ nguyên câu trả lời cục bộ; 'general' = LLM trả lời tự do; 'grounded' = LLM diễn đạt dữ liệu."""
    if (
        reply.get("_skip_llm")
        or reply.get("status") == "needs_clarification"
        or reply.get("intent") == "greeting"
    ):
        return "skip"
    if not is_ollama_available():
        return "skip"
    if reply.get("intent") in GENERAL_INTENTS:
        return "general"
    if len(reply.get("text") or "") > REWRITE_MAX_CHARS:
        return "skip"  # dữ liệu dài (lịch trình...): giữ nguyên văn đã xác minh
    return "grounded"


def _check_generated(mode: str, local_text: str, generated: str, message: str, history) -> None:
    """Ném OllamaError nếu câu trả lời của mô hình không đáng tin; khi đó dùng bản cục bộ."""
    if not generated.strip():
        raise OllamaError("Mô hình không trả về nội dung.")
    if mode == "grounded":
        if not grounded_output_is_safe(local_text, generated, message, history):
            raise OllamaError("Câu trả lời của mô hình không giữ đúng dữ liệu đã xác minh.")
    elif contains_unexpected_script(generated, message):
        raise OllamaError("Câu trả lời của mô hình lẫn ký tự ngoài ngôn ngữ mong đợi.")


def _apply_llm(message: str, state: State, reply: dict[str, Any]) -> str:
    mode = _llm_mode(reply)
    if mode == "skip":
        return reply["text"]

    local_text = reply["text"]
    try:
        if mode == "general":
            answer = ask_llm(message, history=state.history)
        else:
            answer = ask_llm(message, history=state.history, grounded_answer=local_text)
        _check_generated(mode, local_text, answer, message, state.history)
    except Exception as exc:
        logger.warning(
            "Ollama answer not used (%s: %s); returning the local verified answer.",
            type(exc).__name__, exc,
        )
        return local_text

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
    if reply.get("weather") is not None:
        result["weather"] = reply["weather"]
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
        "message": answer,      # legacy client compatibility
        "ai_answer": answer,    # legacy client compatibility
        "steps": reply["steps"],
        "intent": reply["intent"],
        "confidence": reply["confidence"],
        "router": reply.get("router", "local"),
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


def _completed_step_text(step: Any) -> str:
    text = str(step)
    if text.startswith("Đang "):
        text = "Đã " + text[len("Đang "):]
    return re.sub(r"\s+\(\d+ địa điểm\)$", "", text)


@router.post("/chat-stream")
async def chat_stream(req: ChatRequest):
    """
    SSE-compatible endpoint (giao thức không đổi: session, status, step, token, links,
    suggestions, result, error, done).

    Request/analysis statuses are emitted before their work starts. Completed
    dialogue steps are sent only after the dialogue has returned. Token events are only
    sent for text really produced by the local LLM; if that text is rejected or the LLM
    fails midway, the final `result` event carries the verified local answer and the
    frontend replaces what was streamed.
    """
    message = _clean_message(req.message)
    sid, state = _get_state(req.session_id)

    async def event_generator():
        yield _sse({"type": "session", "session_id": sid})

        try:
            yield _sse({
                "type": "status",
                "phase": "received",
                "text": "Đã nhận yêu cầu.",
            })
            yield _sse({
                "type": "status",
                "phase": "analyzing",
                "text": "Đang phân tích yêu cầu và kiểm tra dữ liệu phù hợp…",
            })
            reply = await _compute_request(
                message,
                state,
                req.latitude,
                req.longitude,
                req.choice,
            )

            yield _sse({
                "type": "status",
                "phase": "analyzed",
                "text": "Đã hoàn thành phân tích và tra cứu dữ liệu.",
            })
            for step in reply.get("steps", []):
                yield _sse({
                    "type": "step",
                    "text": _completed_step_text(step),
                    "completed": True,
                })

            streamed_model = False
            mode = await run_in_threadpool(_llm_mode, reply)
            if mode != "skip":
                local_text = reply["text"]
                yield _sse({
                    "type": "status",
                    "phase": "generating",
                    "text": "Đang tạo câu trả lời bằng mô hình AI cục bộ…",
                })
                parts: list[str] = []
                try:
                    if mode == "general":
                        stream = stream_general_answer(message, history=state.history)
                    else:
                        stream = stream_grounded_answer(message, local_text, history=state.history)
                    async for part in iterate_in_threadpool(stream):
                        parts.append(part)
                        streamed_model = True
                        yield _sse({"type": "token", "text": part, "streaming": True})

                    generated = "".join(parts).strip()
                    _check_generated(mode, local_text, generated, message, state.history)
                    reply["text"] = generated
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "Ollama streaming not used (%s: %s); returning the local verified answer.",
                        type(exc).__name__, exc,
                    )
                    # reply["text"] vẫn là câu trả lời cục bộ đã xác minh.

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
                "router": reply.get("router", "local"),
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

    llm = await run_in_threadpool(check_ollama_connection)

    return {
        "success": True,
        "service": "ai-guide",
        "slot_model_ready": ready,
        "session_storage": "memory",
        "llm_provider": "ollama",
        "llm_enabled": llm["available"],
        "llm_model": llm["model"],
        "llm_base_url": llm["base_url"],
        "llm_error": llm["error"],
        "note": (
            "Local ML models route requests first; the local Ollama LLM only helps with "
            "ambiguous requests and natural phrasing. Verified travel facts always come "
            "from the database and weather service."
        ),
    }


if not model_ready():
    logger.warning(
        "Slot model is not ready. Run training/src/generate_slots.py "
        "and training/src/train_slots.py before testing full dialogue extraction."
    )
