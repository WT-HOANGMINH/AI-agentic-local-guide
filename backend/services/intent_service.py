
import os
from pathlib import Path
from functools import lru_cache
import joblib
import re

from backend.services.slot_service import strip_accents


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = (
    PROJECT_ROOT / "training" / "models" / "intent_classifier.joblib"
)
MODEL_PATH = Path(os.getenv("INTENT_MODEL_PATH") or DEFAULT_MODEL_PATH).expanduser()


VALID_INTENTS = {
    "food",
    "attraction",
    "cafe",
    "itinerary",
    "transport",
    "accommodation",
    "weather",
    "out_of_scope",
    # y dinh hoi thoai (them boi add_dialogue_data.py)
    "modify_itinerary",
    "clarify_reply",
    "greeting",
    "ask_detail",
}


@lru_cache(maxsize=1)
def load_model():
    """Nap model hoac artifact da duoc huan luyen."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Khong tim thay mo hinh AI tai: {MODEL_PATH}"
        )

    artifact = joblib.load(MODEL_PATH)

    # Model moi duoc luu trong dictionary.
    if isinstance(artifact, dict):
        loaded_model = artifact.get("model")
        labels = artifact.get("labels", [])
        if loaded_model is None:
            loaded_model = artifact.get("pipeline")
    else:
        # Ho tro Pipeline cu.
        loaded_model = artifact
        labels = getattr(loaded_model, "classes_", [])

    if loaded_model is None:
        raise ValueError("Artifact khong chua model phan loai y dinh.")

    model_labels = set(str(label) for label in labels)

    if not model_labels:
        model_labels = set(
            str(label)
            for label in getattr(loaded_model, "classes_", [])
        )

    if model_labels and not model_labels.issubset(VALID_INTENTS):
        raise ValueError(
            f"Model chua nhan y dinh khong hop le: {model_labels}"
        )

    return loaded_model

def predict_intent(text: str) -> dict:
    """Phan loai cau hoi bang model AI da huan luyen."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Cau hoi khong duoc de trong.")

    cleaned_text = text.strip()

    # Chi tai model khi co yeu cau dau tien
    model = load_model()

    predicted_label = str(model.predict([cleaned_text])[0])

    if predicted_label not in VALID_INTENTS:
        raise ValueError("Model tra ve nhan y dinh khong hop le.")

    result = {
        "intent": predicted_label,
        "confidence": 0.0,
    }

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba([cleaned_text])[0]
        result["confidence"] = round(
            float(max(probabilities)),
            4,
        )

    normalized = strip_accents(cleaned_text)
    rules = (
        (r"\b(lap lich trinh|lich trinh|ke hoach du lich|plan (a )?trip|itinerary)\b", "itinerary"),
        (r"\b(thoi tiet|du bao|mua ngay mai|weather|forecast)\b", "weather"),
        (r"\b(dia diem|diem du lich|noi tieng|tham quan|attraction|famous places)\b", "attraction"),
        (r"\b(quan an|an gi|mon an|am thuc|an sang|an trua|an toi|food|restaurant)\b", "food"),
        (r"\b(quan ca phe|cafe|coffee shop)\b", "cafe"),
        (r"\b(di lai|phuong tien|xe buyt|taxi|how to get|transport)\b", "transport"),
        (r"\b(xin chao|chao ban|hello|hi there)\b", "greeting"),
    )
    for pattern, intent in rules:
        if re.search(pattern, normalized):
            result["intent"] = intent
            result["confidence"] = max(result["confidence"], 0.9)
            break

    return result
