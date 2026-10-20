"""
Train bo phan loai y dinh song ngu Viet - Anh tren du lieu lon (sinh bang generate_dataset.py).

Nguyen tac danh gia TRUNG THUC:
  * intents.csv (viet tay) duoc chia 80/20. 20% nay KHONG BAO GIO dua vao train
    -> day la con so dang tin nhat ("human test").
  * synthetic_eval dung cac mau cau chua tung xuat hien luc train -> kiem tra kha nang
    khai quat, nhung van de hon cau that nen KHONG nen coi la do chinh xac thuc te.
  * Du lieu viet tay trong train duoc nhan len (--human-weight) vi chat luong cao hon.

Chay:
    python training/src/generate_dataset.py
    python training/src/train_intent_v2.py
    python training/src/train_intent_v2.py --final      # train lai tren TOAN BO du lieu viet tay de dua vao production
"""
import argparse
import re
import shutil
import unicodedata
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "training" / "data"
MODEL_DIR = PROJECT_ROOT / "training" / "models"
MODEL_PATH = MODEL_DIR / "intent_classifier.joblib"

HUMAN_PATH = DATA_DIR / "intents.csv"
SYN_TRAIN_PATH = DATA_DIR / "intents_synthetic_train.csv"
SYN_EVAL_PATH = DATA_DIR / "intents_synthetic_eval.csv"

# Bo cau kiem thu thu cong (khong dua vao train)
MANUAL_TESTS = [
    ("Tôi muốn ăn mì Quảng ngon ở Đà Nẵng", "food"),
    ("Gợi ý quán hải sản ngon gần biển Mỹ Khê", "food"),
    ("Tim quan cafe yen tinh de hoc bai", "cafe"),
    ("Quán cà phê nào có Wi-Fi tốt?", "cafe"),
    ("Tôi muốn tham quan những địa điểm nổi tiếng", "attraction"),
    ("Có địa điểm nào ngắm hoàng hôn đẹp không?", "attraction"),
    ("Lập lịch trình du lịch Đà Nẵng hai ngày", "itinerary"),
    ("Tôi có 500 nghìn, hãy lên kế hoạch đi chơi", "itinerary"),
    ("Đi từ sân bay đến cầu Rồng như thế nào?", "transport"),
    ("Nên đi xe buýt hay taxi ở Đà Nẵng?", "transport"),
    ("Where can I eat delicious Mi Quang in Da Nang?", "food"),
    ("Recommend an affordable seafood restaurant", "food"),
    ("Find a quiet cafe where I can study", "cafe"),
    ("Which coffee shop has good Wi-Fi?", "cafe"),
    ("What are the best tourist attractions in Da Nang?", "attraction"),
    ("Where can I watch the sunset?", "attraction"),
    ("Plan a two-day trip to Da Nang", "itinerary"),
    ("Create a travel plan with a limited budget", "itinerary"),
    ("How do I get from the airport to Dragon Bridge?", "transport"),
    ("Should I take a bus or a taxi?", "transport"),
    # nhan bo sung (chi co y nghia khi train voi --extra-labels)
    ("Tìm khách sạn có hồ bơi gần biển Mỹ Khê", "accommodation"),
    ("Homestay nào giá rẻ ở Hội An?", "accommodation"),
    ("Find a hotel with an ocean view", "accommodation"),
    ("I need to book a hostel for two people", "accommodation"),
    ("Ngày mai Đà Nẵng có mưa không?", "weather"),
    ("Thời tiết cuối tuần này thế nào?", "weather"),
    ("Will it rain in Da Nang tomorrow?", "weather"),
    ("What is the best season to visit Da Nang?", "weather"),
    ("Giải giúp tôi một phương trình bậc hai", "out_of_scope"),
    ("Viết cho tôi một đoạn code Python", "out_of_scope"),
    ("Who is the president of France?", "out_of_scope"),
    ("Explain machine learning to me", "out_of_scope"),
]


def norm_key(text):
    text = str(text).replace("đ", "d").replace("Đ", "D")
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text.casefold())
    return " ".join(text.split())


def load_csv(path):
    df = pd.read_csv(path)
    df = df.dropna(subset=["text", "label"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip()
    return df[(df["text"] != "") & (df["label"] != "")].reset_index(drop=True)


def build_model():
    # LUU Y: khong dung ham tu viet (lambda/def) trong Pipeline, vi joblib se khong
    # nap lai duoc khi file predict_intent.py chay o module khac.
    features = FeatureUnion([
        ("word", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True, min_df=2)),
        # n-gram ky tu: chiu duoc loi go, thieu dau tieng Viet, bien the tu
        ("char", TfidfVectorizer(lowercase=True, analyzer="char_wb", ngram_range=(2, 5),
                                 sublinear_tf=True, min_df=3, max_features=300_000)),
    ])
    classifier = CalibratedClassifierCV(
        LinearSVC(C=0.5, class_weight="balanced"), cv=3
    )  # CalibratedClassifierCV cho ra predict_proba -> co confidence
    return Pipeline([("features", features), ("classifier", classifier)])


def evaluate(name, model, texts, labels, show_report=True):
    pred = model.predict(texts)
    acc = accuracy_score(labels, pred)
    f1 = f1_score(labels, pred, average="macro", zero_division=0)
    print(f"\n{'=' * 60}\n{name}: accuracy = {acc:.2%} | macro-F1 = {f1:.3f} | n = {len(labels)}\n{'=' * 60}")
    if show_report:
        print(classification_report(labels, pred, zero_division=0))
    return acc, pred


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--human-weight", type=int, default=3, help="So lan nhan du lieu viet tay trong train")
    parser.add_argument("--final", action="store_true",
                        help="Dung toan bo du lieu viet tay de train (khong con tap human test)")
    parser.add_argument("--output", type=Path, default=MODEL_PATH)
    args = parser.parse_args()

    for path in (HUMAN_PATH, SYN_TRAIN_PATH, SYN_EVAL_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Thieu {path}. Hay chay generate_dataset.py truoc.")

    human = load_csv(HUMAN_PATH).drop_duplicates(subset="text")
    syn_train = load_csv(SYN_TRAIN_PATH)
    syn_eval = load_csv(SYN_EVAL_PATH)

    if args.final:
        human_train, human_test = human, human.iloc[0:0]
    else:
        human_train, human_test = train_test_split(
            human, test_size=0.2, random_state=42, stratify=human["label"]
        )

    # Chan ro ri: bo cac cau synthetic trung voi tap human test
    test_keys = {norm_key(t) for t in human_test["text"]}
    before = len(syn_train)
    syn_train = syn_train[~syn_train["text"].map(norm_key).isin(test_keys)]
    print(f"Synthetic train: {len(syn_train)} (loai {before - len(syn_train)} cau trung tap human test)")
    print(f"Human train: {len(human_train)} x{args.human_weight} | Human test: {len(human_test)}")

    train_df = pd.concat(
        [syn_train[["text", "label"]]] + [human_train[["text", "label"]]] * args.human_weight,
        ignore_index=True,
    )
    print("\nPhan bo nhan trong train:")
    print(train_df["label"].value_counts().sort_index().to_string())

    print("\nDang train (co the mat 1-3 phut)...")
    model = build_model()
    model.fit(train_df["text"], train_df["label"])

    # ---- danh gia ----
    results = {}
    if len(human_test):
        results["human_test"], pred = evaluate("HUMAN TEST (cau viet tay, khong dung de train)",
                                               model, human_test["text"], human_test["label"])
        wrong = human_test.assign(predicted=pred)
        wrong = wrong[wrong["label"] != wrong["predicted"]]
        if len(wrong):
            print("Cac cau doan sai (de bo sung du lieu):")
            print(wrong.head(25).to_string(index=False))
        labels_sorted = sorted(set(human_test["label"]) | set(pred))
        print("\nConfusion matrix (hang = dung, cot = doan):")
        print(pd.DataFrame(confusion_matrix(human_test["label"], pred, labels=labels_sorted),
                           index=labels_sorted, columns=labels_sorted).to_string())

    results["synthetic_eval"], _ = evaluate("SYNTHETIC EVAL (mau cau chua tung thay)",
                                            model, syn_eval["text"], syn_eval["label"], show_report=False)

    known = set(train_df["label"])
    manual_df = pd.DataFrame([m for m in MANUAL_TESTS if m[1] in known], columns=["text", "expected"])
    manual_df["predicted"] = model.predict(manual_df["text"])
    manual_df["ok"] = manual_df["expected"] == manual_df["predicted"]
    print(f"\nMANUAL TEST: {manual_df['ok'].sum()}/{len(manual_df)} dung")
    print(manual_df[~manual_df["ok"]].to_string(index=False) if (~manual_df["ok"]).any() else "Tat ca deu dung.")

    # ---- luu model (cung dinh dang voi train_intent.py cu) ----
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        backup = args.output.with_suffix(".old.joblib")
        shutil.copy2(args.output, backup)
        print(f"\nDa sao luu model cu: {backup}")

    artifact = {
        "model": model,
        "labels": sorted(train_df["label"].unique().tolist()),
        "version": "bilingual-synthetic-2.0",
        "training_samples": len(train_df),
        "human_test_accuracy": results.get("human_test"),
        "synthetic_eval_accuracy": results["synthetic_eval"],
    }
    joblib.dump(artifact, args.output)
    print(f"Da luu model: {args.output}")


if __name__ == "__main__":
    main()
