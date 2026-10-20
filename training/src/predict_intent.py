
from pathlib import Path
import joblib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "training" / "models" / "intent_classifier.joblib"


class IntentPredictor:
    """Tai model da train va du doan y dinh nguoi dung."""

    def __init__(self, model_path=MODEL_PATH):
        if not model_path.exists():
            raise FileNotFoundError(
                f"Khong tim thay model: {model_path}. "
                "Hay chay training/src/train_intent.py truoc."
            )

        artifact = joblib.load(model_path)

        # Ho tro ca artifact moi va Pipeline cu
        if isinstance(artifact, dict) and "model" in artifact:
            self.model = artifact["model"]
            self.labels = artifact.get("labels", [])
        else:
            self.model = artifact
            self.labels = list(getattr(self.model, "classes_", []))

    def predict(self, text: str) -> dict:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Cau hoi khong duoc de trong.")

        label = str(self.model.predict([text.strip()])[0])

        result = {
            "text": text.strip(),
            "intent": label,
        }

        # Them confidence neu model ho tro predict_proba
        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba([text.strip()])[0]
            result["confidence"] = round(float(max(probabilities)), 4)

        return result


def predict_intent(text: str) -> dict:
    """Ham tien ich de module khac goi."""
    predictor = IntentPredictor()
    return predictor.predict(text)


if __name__ == "__main__":
    predictor = IntentPredictor()

    print("Nhap cau hoi bang tieng Viet hoac tieng Anh.")
    print("Nhap 'exit' de thoat.")

    while True:
        try:
            text = input("\nYou: ").strip()

            if text.casefold() in {"exit", "quit"}:
                break

            if not text:
                continue

            result = predictor.predict(text)
            print("Intent:", result["intent"])

            if "confidence" in result:
                print("Confidence:", result["confidence"])

        except (KeyboardInterrupt, EOFError):
            print("\nDa thoat.")
            break
        except ValueError as error:
            print("Loi:", error)
