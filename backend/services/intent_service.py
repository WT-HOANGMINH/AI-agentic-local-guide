
from pathlib import Path
import joblib


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "training"
    / "models"
    / "intent_classifier.joblib"
)

VALID_INTENTS = {
    "food",
    "attraction",
    "cafe",
    "itinerary",
    "transport",
}


def load_model():
    """Nap model hoac artifact da duoc huan luyen."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Khong tim thay mo hinh AI tai: {MODEL_PATH}"
        )

    artifact = joblib.load(MODEL_PATH)

    # Model moi duoc luu trong dictionary.
    if isinstance(artifact, dict) and "model" in artifact:
        loaded_model = artifact["model"]
        labels = artifact.get("labels", [])
    else:
        # Ho tro Pipeline cu.
        loaded_model = artifact
        labels = getattr(loaded_model, "classes_", [])

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


# Chi nap model mot lan khi service duoc import.
model = load_model()


def predict_intent(text: str) -> dict:
    """Phan loai cau hoi bang model AI da huan luyen."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Cau hoi khong duoc de trong.")

    cleaned_text = text.strip()
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

    return result
