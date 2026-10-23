from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.chat_service import answer

router = APIRouter(prefix="/agent", tags=["Agent Chat"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@router.post("/chat")
def chat(payload: ChatIn, db: Session = Depends(get_db)):
    return answer(payload.message.strip(), db)