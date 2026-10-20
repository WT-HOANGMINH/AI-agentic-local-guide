
from fastapi import APIRouter, HTTPException

from backend.schemas.intent import IntentRequest, IntentResponse
from backend.services.intent_service import predict_intent

router = APIRouter(prefix="/api/intents", tags=["AI Intent Classification"])


@router.post("/predict", response_model=IntentResponse)
def predict_user_intent(request: IntentRequest):
    try:
        result = predict_intent(request.text)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
