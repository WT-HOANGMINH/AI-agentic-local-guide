"""Xuất tên địa điểm từ DB ra training/data/place_names.txt để sinh dữ liệu huấn luyện bộ trích thông tin.
Chạy từ thư mục gốc dự án:  python training/src/export_place_names.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal          # noqa: E402
from backend.models.place import Place              # noqa: E402

PREFIXES = ["bãi biển ", "nhà hàng ", "khu du lịch ", "kdl ", "công viên ", "chùa ", "chợ đêm ", "quán "]
ALIASES = ["Bà Nà", "Bà Nà Hills", "Sơn Trà", "Hội An", "Mỹ Khê", "Ngũ Hành Sơn", "Cầu Rồng", "Hải Vân",
           "Cù Lao Chàm", "Mỹ Sơn", "Chợ Hàn", "Cầu Vàng", "Phố cổ Hội An", "Bán đảo Sơn Trà"]


def main():
    db = SessionLocal()
    try:
        names = [row[0] for row in db.query(Place.name).all()]
    finally:
        db.close()
    out = set(ALIASES)
    for name in names:
        name = name.strip()
        if not name:
            continue
        out.add(name)
        short = re.sub(r"\s*\([^)]*\)", "", name).strip()      # bỏ phần trong ngoặc
        if short:
            out.add(short)
        low = short.lower()
        for pre in PREFIXES:
            if low.startswith(pre) and len(short.split()) - len(pre.split()) >= 2:
                out.add(short[len(pre):].strip())
    path = ROOT / "training" / "data" / "place_names.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(sorted(out)), encoding="utf-8")
    print(f"Đã ghi {len(out)} tên (từ {len(names)} địa điểm) -> {path}")


if __name__ == "__main__":
    main()
