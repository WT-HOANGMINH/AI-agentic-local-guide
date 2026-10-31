"""Huấn luyện bộ trích thông tin (gán nhãn từng từ).  Chạy: python training/src/train_slots.py"""
import json
import random
import sys
from pathlib import Path

import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.services.slot_service import token_features   # noqa: E402

DATA = ROOT / "training" / "data" / "slots_train.jsonl"
MODEL = ROOT / "training" / "models" / "slot_tagger.joblib"

# Câu viết tay để kiểm tra thật (không có trong dữ liệu sinh). Hãy thêm câu của riêng bạn.
HAND_TESTS = [
    ("mình muốn đi Bà Nà từ sớm", {"PLACE": "Bà Nà", "TIME": "sớm"}),
    ("lịch trình 3 ngày thích biển", {"DAYS": "3 ngày", "INTEREST": "biển"}),
    ("ăn sáng gần Mỹ Khê", {"MEAL": "ăn sáng", "PLACE": "Mỹ Khê"}),
    ("thêm bữa sáng vào ngày 1", {"MEAL": "bữa sáng"}),
    ("xuất phát lúc 6h", {"TIME": "6h"}),
    ("2 ngày", {"DAYS": "2 ngày"}),
    ("ngan sach 500k cho 4 nguoi", {"BUDGET": "500k", "PEOPLE": "4 nguoi"}),
    ("start at 6am and go to Hoi An", {"TIME": "6am", "PLACE": "Hoi An"}),
    ("plan 2 days for 2 people", {"DAYS": "2 days", "PEOPLE": "2 people"}),
    ("bỏ Cầu Rồng khỏi lịch trình", {"PLACE": "Cầu Rồng"}),
    ("tôi thích văn hóa và ẩm thực", {"INTEREST": "văn hóa"}),
    ("Ngũ Hành Sơn mở cửa mấy giờ", {"PLACE": "Ngũ Hành Sơn"}),
]


def flat(rows):
    X, y = [], []
    for r in rows:
        for i, t in enumerate(r["tags"]):
            X.append(token_features(r["tokens"], i))
            y.append(t)
    return X, y


def main():
    if not DATA.exists():
        raise SystemExit("Thiếu slots_train.jsonl. Hãy chạy generate_slots.py trước.")
    rows = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
    random.Random(1).shuffle(rows)
    cut = int(len(rows) * 0.8)
    Xtr, ytr = flat(rows[:cut])
    Xte, yte = flat(rows[cut:])
    model = make_pipeline(DictVectorizer(), LogisticRegression(max_iter=1000, C=5.0))
    model.fit(Xtr, ytr)
    print("== Tập kiểm thử SINH TỰ ĐỘNG (cùng khuôn mẫu, nên điểm cao là bình thường) ==")
    print(classification_report(yte, model.predict(Xte), zero_division=0))

    MODEL.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL)
    print("Đã lưu:", MODEL)

    from backend.services.slot_service import tag          # nạp lại sau khi lưu
    ok = 0
    print("\n== Câu VIẾT TAY (con số đáng tin hơn) ==")
    for text, expected in HAND_TESTS:
        got = {}
        for kind, val in tag(text):
            got.setdefault(kind, val)
        hit = all(got.get(k) == v for k, v in expected.items())
        ok += hit
        print(("OK  " if hit else "SAI ") + text, "->", tag(text))
    print(f"\nĐúng {ok}/{len(HAND_TESTS)} câu viết tay ({ok / len(HAND_TESTS):.0%}). Hãy thêm câu của bạn vào HAND_TESTS.")


if __name__ == "__main__":
    main()
