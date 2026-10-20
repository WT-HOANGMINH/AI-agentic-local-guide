
from pydantic import BaseModel, Field


class IntentRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Cau hoi cua nguoi dung",
    )


class IntentResponse(BaseModel):
    intent: str
    confidence: float
