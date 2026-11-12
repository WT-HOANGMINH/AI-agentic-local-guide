"""
Gắn nhãn thời tiết cho bảng places.

  python -m backend.enrich_weather_profile            # chạy thử, chỉ in kết quả
  python -m backend.enrich_weather_profile --apply    # ghi vào DB

- Tự thêm cột places.weather_profile nếu chưa có (VARCHAR(20), NULL).
- Chỉ điền các dòng đang NULL, KHÔNG ghi đè nhãn bạn đã sửa tay.
- Nhãn: indoor | outdoor | weather_dependent
- Đây là phân loại tự động theo category + từ khóa trong tên/mô tả/địa chỉ:
  chỉ xấp xỉ, hãy rà lại danh sách "weather_dependent" và các dòng lạ.
- NHỚ BACKUP bảng places trước khi --apply.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter


def _strip(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text) is not None


OUTDOOR = (r"\b(bien|bai|thac|suoi|song|nui|deo|ban dao|son tra|ngu hanh son|ba na|"
           r"cong vien|cau|hai dang|rung|ghenh|dinh|cap treo|lang chai|mui)\b")
INDOOR_ATTRACTION = (r"\b(bao tang|museum|nha hat|rap|trung tam thuong mai|aeon|vincom|"
                     r"lotte|aquarium|thuy cung|escape|game|khu vui choi trong nha)\b")
SEMI_OUTDOOR_ATTRACTION = r"\b(chua|nha tho|cho|lang|pho co|di tich|thanh)\b"
OUTDOORISH_FOOD = r"\b(view bien|ngoai troi|san vuon|garden|rooftop|bai bien|ven song)\b"


def classify(name: str, category: str, description: str = "", address: str = "") -> str:
    n = _strip(name)
    blob = _strip(f"{name} {description} {address}")
    cat = (category or "").strip()

    if cat in ("restaurant", "cafe"):
        return "weather_dependent" if _has(OUTDOORISH_FOOD, blob) else "indoor"

    if cat == "shopping":
        return "weather_dependent" if _has(r"\b(cho|cho dem|pho)\b", n) else "indoor"

    # tourist_attraction và các loại khác
    if _has(INDOOR_ATTRACTION, n):
        return "indoor"
    if _has(OUTDOOR, n):
        return "outdoor"
    if _has(SEMI_OUTDOOR_ATTRACTION, n):
        return "weather_dependent"
    if _has(OUTDOOR, blob):
        return "outdoor"
    return "weather_dependent"  # không chắc: coi là phụ thuộc thời tiết, an toàn hơn


def _ensure_column(engine) -> bool:
    from sqlalchemy import inspect, text
    cols = {c["name"] for c in inspect(engine).get_columns("places")}
    if "weather_profile" in cols:
        return False
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE places ADD COLUMN weather_profile VARCHAR(20) NULL"))
    return True


def main(apply: bool) -> None:
    from sqlalchemy import inspect, text

    from backend.database import SessionLocal, engine

    if apply and _ensure_column(engine):
        print("Đã thêm cột places.weather_profile")

    has_col = "weather_profile" in {c["name"] for c in inspect(engine).get_columns("places")}
    if not has_col:
        print("(chạy thử) cột weather_profile chưa có, sẽ được thêm khi dùng --apply")

    db = SessionLocal()
    try:
        sql = "SELECT id, name, category, description, address, " + \
              ("weather_profile" if has_col else "NULL") + " FROM places WHERE is_active = 1"
        rows = db.execute(text(sql)).fetchall()

        counts, todo, review = Counter(), [], []
        for pid, name, cat, desc, addr, current in rows:
            if current:
                counts[f"(giữ nguyên) {current}"] += 1
                continue
            label = classify(name, cat, desc or "", addr or "")
            counts[label] += 1
            todo.append((label, pid))
            if label == "weather_dependent" and cat == "tourist_attraction":
                review.append(f"  #{pid} {name}")

        print("Kết quả phân loại:", dict(counts))
        if review:
            print(f"Cần rà tay ({len(review)} điểm tham quan chưa rõ trong nhà / ngoài trời):")
            print("\n".join(review[:40]))

        if apply:
            for label, pid in todo:
                db.execute(text("UPDATE places SET weather_profile = :l WHERE id = :i"),
                           {"l": label, "i": pid})
            db.commit()
            print(f"Đã cập nhật {len(todo)} dòng.")
        else:
            print("Đây là chạy thử, chưa ghi gì. Dùng --apply để ghi.")
    finally:
        db.close()


if __name__ == "__main__":
    main("--apply" in sys.argv)
