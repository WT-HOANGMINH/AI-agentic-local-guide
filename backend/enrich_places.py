"""Bo sung du lieu cho planner (gio mo/dong, khu vuc, thoi luong, khung gio dep) tu du lieu da co.

Chay tu thu muc goc du an (MySQL phai dang chay):
    python -m backend.enrich_places                 # bo sung du lieu
    python -m backend.enrich_places --merge-bana    # bo sung + gop 3 dong Ba Na thanh 1

An toan: tu sao luu bang truoc, chi dien o dang NULL (khong ghi de phan ban da sua tay).
"""
import sys
from collections import Counter
from datetime import datetime

from sqlalchemy import inspect, text

from backend.database import engine
from backend.services.place_enrichment import best_time_for, duration_for, parse_hours, zone_of

NEW_COLS = {"duration_min": "INTEGER", "open_time": "VARCHAR(5)", "close_time": "VARCHAR(5)",
            "best_time": "VARCHAR(20)", "zone": "VARCHAR(30)"}

# Gop Cau Vang / Lang Phap / Chua Linh Ung Ba Na thanh mot chuyen di ca ngay (dung gio & gia ve co san trong du lieu).
BANA = {
    "name": "Sun World Bà Nà Hills (Cầu Vàng, Làng Pháp, Chùa Linh Ứng)",
    "category": "tourist_attraction",
    "address": "Sun World Bà Nà Hills, Thôn An Sơn, Xã Hòa Ninh, Huyện Hòa Vang, Đà Nẵng",
    "description": ("Khu du lịch trên núi gồm Cầu Vàng, Làng Pháp và Chùa Linh Ứng Bà Nà. "
                    "Vé cáp treo Bà Nà: 900.000 VNĐ (theo dữ liệu hiện có, cần kiểm tra lại)."),
    "price_level": 4,
    "opening_hours": "08:00 - 17:00",
}
BANA_OLD_IDS = (828, 842, 843)   # id theo bang ban gui: Chua Linh Ung Ba Na, Cau Vang, Lang Phap


def main(merge_bana=False):
    print("Ket noi:", engine.url.render_as_string(hide_password=True))
    if engine.dialect.name == "sqlite" and "--allow-sqlite" not in sys.argv:
        raise SystemExit("Dang dung SQLite du phong (MySQL chua chay?). Hay bat MySQL roi chay lai, "
                         "hoac them --allow-sqlite neu day that su la CSDL ban muon.")
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM places")).scalar()
    if not total:
        raise SystemExit("Bang places dang rong: khong co gi de bo sung.")

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    have = {c["name"] for c in inspect(engine).get_columns("places")}
    with engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE places_backup_before_enrich_{ts} AS SELECT * FROM places"))
        for col, typ in NEW_COLS.items():
            if col not in have:
                conn.execute(text(f"ALTER TABLE places ADD COLUMN {col} {typ}"))

        if merge_bana:
            exists = conn.execute(text("SELECT COUNT(*) FROM places WHERE name = :n"), {"n": BANA["name"]}).scalar()
            if exists:
                print("Dong Ba Na gop da ton tai: bo qua.")
            else:
                old = conn.execute(text(
                    "SELECT id, name FROM places WHERE id IN (828, 842, 843) AND is_active = 1 "
                    "AND category = 'tourist_attraction'")).all()
                print("Se an cac dong cu:", [f"{i}:{n}" for i, n in old])
                conn.execute(text(
                    "UPDATE places SET is_active = 0 WHERE id IN (828, 842, 843) AND category = 'tourist_attraction'"))
                conn.execute(text(
                    "INSERT INTO places (name, category, address, description, price_level, opening_hours, is_active) "
                    "VALUES (:name, :category, :address, :description, :price_level, :opening_hours, 1)"), BANA)
                print("Da gop Ba Na thanh 1 dong.")

        rows = conn.execute(text(
            "SELECT id, name, category, address, description, opening_hours, duration_min, "
            "open_time, close_time, best_time, zone, is_active FROM places")).mappings().all()
        zones, missing = Counter(), []
        for r in rows:
            ot, ct = parse_hours(r["opening_hours"])
            new = {
                "open_time": r["open_time"] or ot,
                "close_time": r["close_time"] or ct,
                "zone": r["zone"] or zone_of(r["name"], r["address"]),
                "duration_min": r["duration_min"] or duration_for(r["name"], r["category"]),
            }
            new["best_time"] = r["best_time"] or best_time_for(r["name"], r["description"], new["open_time"], r["category"])
            conn.execute(text(
                "UPDATE places SET open_time=:open_time, close_time=:close_time, zone=:zone, "
                "duration_min=:duration_min, best_time=:best_time WHERE id=:id"), {**new, "id": r["id"]})
            if r["is_active"]:
                zones[new["zone"] or "(chua ro)"] += 1
                if not new["zone"]:
                    missing.append(f"{r['id']}:{r['name']}")

    print(f"Da xu ly {len(rows)} dong. Sao luu: places_backup_before_enrich_{ts}")
    for z, n in zones.most_common():
        print(f"  zone {z}: {n}")
    if missing:
        print(f"Con {len(missing)} dong chua suy ra duoc zone (hay sua tay), vi du:", missing[:15])


if __name__ == "__main__":
    main(merge_bana="--merge-bana" in sys.argv)
