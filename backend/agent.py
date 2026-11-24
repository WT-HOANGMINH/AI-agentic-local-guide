import inspect

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.database import SessionLocal
from backend.services.chat_service import answer
from backend.services.llm_service import ask_llm, check_ollama_connection

router = APIRouter(prefix="/agent", tags=["Agent Chat"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Vi tri nguoi dung (tuy chon) de tim "gan toi" va lap lich trinh
    latitude: float | None = None
    longitude: float | None = None


@router.post("/chat")
def chat(payload: ChatIn, db: Session = Depends(get_db)):
    message = payload.message.strip()
    params = inspect.signature(answer).parameters
    local_result = (
        answer(message, db, payload.latitude, payload.longitude)
        if "lat" in params and "lng" in params
        else answer(message, db)
    )

    status = check_ollama_connection()
    if status["available"]:
        try:
            generated = ask_llm(
                message,
                grounded_answer=str(local_result.get("reply") or ""),
            )
            if generated.strip():
                local_result["reply"] = generated.strip()
                local_result["source"] = "ollama_hybrid"
        except Exception:
            local_result["source"] = "scikit_learn_local"
    else:
        local_result["source"] = "scikit_learn_local"
    return local_result


def ask_agent(message: str) -> str:
    """Compatibility function for legacy recommendation route."""
    status = check_ollama_connection()
    if not status["available"]:
        raise RuntimeError(status["error"] or "Ollama không khả dụng.")
    db = SessionLocal()
    try:
        local_result = chat(ChatIn(message=message), db=db)
        return str(local_result.get("reply") or "")
    finally:
        db.close()