import inspect

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.chat_service import answer

router = APIRouter(prefix="/agent", tags=["Agent Chat"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Vi tri nguoi dung (tuy chon) de tim "gan toi" va lap lich trinh
    latitude: float | None = None
    longitude: float | None = None


@router.post("/chat")
def chat(payload: ChatIn, db: Session = Depends(get_db)):
    message = payload.message.strip()

    # Neu chat_service.answer() da ho tro lat/lng (sau khi them planner_service)
    # thi truyen kem vi tri; neu chua thi goi nhu cu de khong bi loi.
    params = inspect.signature(answer).parameters

    if "lat" in params and "lng" in params:
        return answer(message, db, payload.latitude, payload.longitude)

    return answer(message, db)