
from pathlib import Path
import re
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "training" / "data" / "intents.csv"
MODEL_DIR = PROJECT_ROOT / "training" / "models"
MODEL_PATH = MODEL_DIR / "intent_classifier.joblib"


# Bo cau kiem thu thu cong: khong dung de huan luyen model
MANUAL_TESTS = [
    ("Tôi muốn ăn mì Quảng ngon ở Đà Nẵng", "food", "vi"),
    ("Gợi ý quán hải sản ngon gần biển Mỹ Khê", "food", "vi"),
    ("Tìm quán cà phê yên tĩnh để học bài", "cafe", "vi"),
    ("Quán cà phê nào có Wi-Fi tốt?", "cafe", "vi"),
    ("Tôi muốn tham quan những địa điểm nổi tiếng", "attraction", "vi"),
    ("Có địa điểm nào ngắm hoàng hôn đẹp không?", "attraction", "vi"),
    ("Lập lịch trình du lịch Đà Nẵng hai ngày", "itinerary", "vi"),
    ("Tôi có 500 nghìn, hãy lên kế hoạch đi chơi", "itinerary", "vi"),
    ("Đi từ sân bay đến cầu Rồng như thế nào?", "transport", "vi"),
    ("Nên đi xe buýt hay taxi ở Đà Nẵng?", "transport", "vi"),

    ("Where can I eat delicious Mi Quang in Da Nang?", "food", "en"),
    ("Recommend an affordable seafood restaurant", "food", "en"),
    ("Find a quiet cafe where I can study", "cafe", "en"),
    ("Which coffee shop has good Wi-Fi?", "cafe", "en"),
    ("What are the best tourist attractions in Da Nang?", "attraction", "en"),
    ("Where can I watch the sunset?", "attraction", "en"),
    ("Plan a two-day trip to Da Nang", "itinerary", "en"),
    ("Create a travel plan with a limited budget", "itinerary", "en"),
    ("How do I get from the airport to Dragon Bridge?", "transport", "en"),
    ("Should I take a bus or a taxi?", "transport", "en"),
]


def normalize_text(text):
    return " ".join(str(text).strip().casefold().split()).rstrip(".,!?;:")


def detect_language(text):
    """Nhan dien don gian phuc vu danh gia thu cong."""
    if re.search(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệ"
                 r"íìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]",
                 text.casefold()):
        return "vi"
    return "en"


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Khong tim thay dataset: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)

    if not {"text", "label"}.issubset(df.columns):
        raise ValueError("Dataset phai co hai cot text va label.")

    df = df.dropna(subset=["text", "label"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip()
    df = df[(df["text"] != "") & (df["label"] != "")]

    # Loai bo cau trung lap sau khi chuan hoa
    df["_normalized"] = df["text"].map(normalize_text)
    duplicate_count = int(df["_normalized"].duplicated().sum())
    df = df.drop_duplicates(subset="_normalized", keep="first")
    df = df.drop(columns="_normalized")

    if df["label"].nunique() < 2:
        raise ValueError("Can it nhat hai nhan de huan luyen.")

    if df["label"].value_counts().min() < 2:
        raise ValueError("Moi nhan can it nhat hai mau.")

    # Phan loai ngon ngu mang tinh heuristic, dung de thong ke
    df["language_estimate"] = df["text"].map(detect_language)

    print("=" * 60)
    print("DATASET SUMMARY")
    print("=" * 60)
    print(f"Total samples after deduplication: {len(df)}")
    print(f"Duplicate rows removed: {duplicate_count}")
    print("\nSamples per label:")
    print(df["label"].value_counts().sort_index().to_string())
    print("\nEstimated language distribution:")
    print(df["language_estimate"].value_counts().to_string())

    # Chia train/test theo nhan
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"],
        df["label"],
        test_size=0.2,
        random_state=42,
        stratify=df["label"],
    )

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                strip_accents=None,
                sublinear_tf=True,
            ),
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=2000,
                random_state=42,
                class_weight="balanced",
            ),
        ),
    ])

    print("\nTraining model...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    print("\n" + "=" * 60)
    print("HELD-OUT TEST RESULTS")
    print("=" * 60)
    print(f"Accuracy: {accuracy_score(y_test, predictions):.2%}")
    print("\nClassification report:")
    print(classification_report(
        y_test,
        predictions,
        zero_division=0,
    ))

    # Danh gia bo cau kiem thu thu cong
    test_texts = [item[0] for item in MANUAL_TESTS]
    expected = [item[1] for item in MANUAL_TESTS]
    languages = [item[2] for item in MANUAL_TESTS]
    manual_predictions = model.predict(test_texts)

    manual_results = pd.DataFrame({
        "text": test_texts,
        "language": languages,
        "expected": expected,
        "predicted": manual_predictions,
    })
    manual_results["correct"] = (
        manual_results["expected"] == manual_results["predicted"]
    )

    print("\n" + "=" * 60)
    print("MANUAL BILINGUAL TEST")
    print("=" * 60)
    print(manual_results.to_string(index=False))

    print("\nManual accuracy by language:")
    for language, group in manual_results.groupby("language"):
        accuracy = group["correct"].mean()
        print(f"{language}: {accuracy:.2%} ({group['correct'].sum()}/{len(group)})")

    # Luu model va metadata
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    artifact = {
        "model": model,
        "labels": sorted(df["label"].unique().tolist()),
        "version": "bilingual-baseline-1.0",
        "training_samples": len(df),
        "test_accuracy": float(accuracy_score(y_test, predictions)),
    }
    joblib.dump(artifact, MODEL_PATH)

    print("\n" + "=" * 60)
    print("MODEL SAVED")
    print(f"Path: {MODEL_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
