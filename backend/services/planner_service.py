"""
Planner: lap lich trinh theo gio, thoi tiet va quang duong.

- Du lieu dia diem (ten, toa do, gio mo cua, rating) lay tu DB.
- Khoang cach / thoi gian di chuyen / thoi tiet do code tinh, khong de LLM tu bia.
- Quang duong la UOC LUONG (duong chim bay x 1.35), chua phai duong that.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta
from math import asin, cos, radians, sin, sqrt

import httpx
from sqlalchemy.orm import Session

from backend.models.place import Place

DANANG = (16.0544, 108.2022)
HOIAN = (15.8794, 108.3279)

ROAD_FACTOR = 1.35          # duong thuc te ~ 1.35 x duong chim bay
SPEED_BIKE = 28             # km/h xe may trong thanh pho
SPEED_CAR = 35              # km/h o to / Grab
LATEST_START = 22 * 60      # khong xep hoat dong bat dau sau 22:00

# Khung gio trong ngay:
# t = gio bat dau, dur = thoi luong (phut), cats = nhom dia diem
TEMPLATE = [
    dict(t="07:00", label="Ăn sáng", cats=["restaurant"], dur=60),
    dict(t="08:30", label="Mua sắm / chợ", cats=["shopping"], dur=90, exclude=["dem"]),
    dict(t="10:15", label="Tham quan văn hóa", cats=["tourist_attraction"], dur=105,
         kws=["pho co", "chua", "bao tang", "nha tho", "lang", "cau", "ngu hanh"]),
    dict(t="12:00", label="Ăn trưa", cats=["restaurant"], dur=75),
    dict(t="13:30", label="Nghỉ ngơi", rest=True, until="16:00"),
    dict(t="16:00", label="Tham quan buổi chiều", cats=["tourist_attraction"], dur=120,
         afternoon=True),
    dict(t="18:30", label="Ăn tối", cats=["restaurant"], dur=75),
    dict(t="20:00", label="Cà phê / chợ đêm", cats=["shopping", "cafe"], dur=90,
         kws=["dem", "ca phe"]),
]

# Dia diem ngoai troi (de canh bao mua)
OUTDOOR = ["bien", "ban dao", "deo", "rung", "ngu hanh", "ba na", "cau vang",
           "my son", "lang", "cau rong"]

# Tu khoa nguoi dung nhac -> dia diem can dua vao buoi chieu
FORCE_KEYS = ["ba na", "my son", "ngu hanh", "son tra", "hai van"]


# ---------------------------------------------------------------
# Tien ich
# ---------------------------------------------------------------
def fold(s: str) -> str:
    s = (s or "").replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def haversine(a, b) -> float:
    la1, lo1, la2, lo2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(min(1.0, h)))


def coord(p):
    if p.latitude is not None and p.longitude is not None:
        return (p.latitude, p.longitude)
    return None


def road_km(a, b) -> float:
    return haversine(a, b) * ROAD_FACTOR


def tmin(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def blob(p) -> str:
    return fold(f"{p.name} {p.address or ''} {p.description or ''}")


def is_outdoor(p) -> bool:
    return any(k in blob(p) for k in OUTDOOR)


def area_of(p) -> str:
    b = blob(p)
    if "hoi an" in b:
        return "hoi an"
    if "my son" in b or "duy phu" in b:
        return "my son"
    return "da nang"


# ---------------------------------------------------------------
# Thoi tiet (Open-Meteo)
# ---------------------------------------------------------------
def fetch_weather(lat, lng, days):
    try:
        r = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lng,
                "daily": "temperature_2m_max,temperature_2m_min,"
                         "precipitation_probability_max,precipitation_sum",
                "hourly": "precipitation_probability",
                "timezone": "Asia/Ho_Chi_Minh",
                "forecast_days": min(max(days, 1), 7),
            },
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        out = []
        for i, day in enumerate(d["daily"]["time"]):
            out.append(dict(
                date=day,
                tmax=d["daily"]["temperature_2m_max"][i],
                tmin=d["daily"]["temperature_2m_min"][i],
                rain_prob=d["daily"]["precipitation_probability_max"][i] or 0,
                rain_mm=d["daily"]["precipitation_sum"][i] or 0,
                hours=d["hourly"]["precipitation_probability"][i * 24:(i + 1) * 24],
            ))
        return out
    except Exception:
        return None


def day_advice(w):
    """Tra ve (loi khuyen, co_mua_khong)."""
    if not w:
        return "Chưa lấy được dự báo thời tiết, bạn nên kiểm tra lại trước khi đi.", False
    if w["rain_prob"] >= 60 or w["rain_mm"] >= 5:
        return ("Khả năng mưa cao: nên đi ô tô/Grab, mang áo mưa, "
                "ưu tiên điểm trong nhà.", True)
    if (w["tmax"] or 0) >= 35:
        return ("Trời nắng nóng: đi xe máy nhớ mũ, kem chống nắng; "
                "tránh ngoài trời 11:00–15:00.", False)
    return "Thời tiết thuận lợi, đi xe máy được.", False


def _hour_rain(w, hour):
    if not w:
        return False
    hours = w.get("hours") or []
    if 0 <= hour < len(hours) and hours[hour] is not None:
        return hours[hour] >= 60
    return False


# ---------------------------------------------------------------
# Chon dia diem
# ---------------------------------------------------------------
def _pool(places, slot, area, used, rainy_hour):
    pool = [p for p in places if p.category in slot["cats"]]
    pool = [p for p in pool if not any(k in blob(p) for k in slot.get("exclude", []))]

    in_area = [p for p in pool if area_of(p) == area]
    pool = in_area or pool

    if slot.get("kws"):
        hit = [p for p in pool if any(k in blob(p) for k in slot["kws"])]
        pool = hit or pool

    fresh = [p for p in pool if p.id not in used]
    pool = fresh or pool

    if rainy_hour:
        indoor = [p for p in pool if not is_outdoor(p)]
        pool = indoor or pool
    return pool


def _best(pool, pos):
    """Uu tien rating cao va gan diem truoc."""
    def score(p):
        r = getattr(p, "rating", None) or 3.5
        place_coords = coord(p)
        distance_penalty = (
            road_km(pos, place_coords) * 0.3
            if pos is not None and place_coords is not None
            else 0
        )
        return r * 2 - distance_penalty
    return max(pool, key=score) if pool else None


def _forced_places(places, folded):
    """Dia diem nguoi dung nhac dich danh (vd 'Ba Na') -> dua vao buoi chieu."""
    out = []
    for p in places:
        name = fold(p.name)
        hit = name in folded or any(k in folded and k in name for k in FORCE_KEYS)
        if hit and p not in out:
            out.append(p)
    return out


# ---------------------------------------------------------------
# Lich trinh
# ---------------------------------------------------------------
def build_itinerary(db: Session, message: str, vi: bool = True, lat=None, lng=None) -> str:
    folded = fold(message)

    m = re.search(r"(\d)\s*(?:ngay|day)", folded)
    days = min(max(int(m.group(1)), 1), 7) if m else 1

    places = db.query(Place).filter(Place.is_active == True).all()  # noqa: E712
    if not places:
        return "Chưa có dữ liệu địa điểm. Hãy chạy: python -X utf8 -m backend.seed_places"

    area = "hoi an" if "hoi an" in folded else "da nang"
    has_gps = lat is not None and lng is not None
    start = (lat, lng) if has_gps else (HOIAN if area == "hoi an" else DANANG)

    forced = _forced_places(places, folded)
    used = {p.id for p in forced}
    missing_coordinates = False

    weather = fetch_weather(start[0], start[1], days)

    out = [f"Lịch trình gợi ý {days} ngày:"]

    for d in range(days):
        w = weather[d] if weather and d < len(weather) else None
        if w:
            try:
                d_date = datetime.strptime(w["date"], "%Y-%m-%d").strftime("%d/%m")
            except ValueError:
                d_date = w["date"]
        else:
            d_date = (date.today() + timedelta(days=d)).strftime("%d/%m")

        advice, rainy_day = day_advice(w)
        out.append(f"\n=== Ngày {d + 1} ({d_date}) ===")
        if w:
            out.append(f"Thời tiết: {w['tmin']:.0f}–{w['tmax']:.0f}°C, "
                       f"khả năng mưa {w['rain_prob']}%")
        out.append(f"Gợi ý di chuyển: {advice}")

        pos, t, first = start, 0, True

        for slot in TEMPLATE:
            s = max(tmin(slot["t"]), t)

            # --- nghi trua ---
            if slot.get("rest"):
                end = tmin(slot["until"])
                if s < end:
                    out.append(f"\n{hhmm(s)}–{hhmm(end)}  Nghỉ ngơi tại khách sạn/quán cà phê, "
                               "tránh nắng giữa trưa")
                    t = end
                continue

            if s >= LATEST_START:
                continue

            rainy = _hour_rain(w, min(s // 60, 23))
            dur = slot["dur"]

            # --- chon dia diem ---
            if slot.get("afternoon") and forced:
                p, dur = forced.pop(0), 180
            else:
                p = _best(_pool(places, slot, area, used, rainy), pos)
            if not p:
                continue
            used.add(p.id)

            # --- di chuyen ---
            place_coords = coord(p)
            km = road_km(pos, place_coords) if pos and place_coords else None
            by_car = rainy_day or (km is not None and km > 15)
            minutes = (
                round(km / (SPEED_CAR if by_car else SPEED_BIKE) * 60) + 3
                if km is not None
                else 0
            )
            s = max(s, t + minutes)
            e = s + dur

            out.append(f"\n{hhmm(s)}–{hhmm(e)}  {slot['label']}: {p.name}")
            if p.address:
                out.append(f"   Địa chỉ: {p.address}")
            if p.opening_hours:
                out.append(f"   Giờ mở cửa: {p.opening_hours}")
            r = getattr(p, "rating", None)
            if r:
                out.append(f"   Đánh giá: {r}/5")

            origin = ("vị trí của bạn" if (first and has_gps)
                      else "điểm xuất phát" if first else "điểm trước")
            if km is not None:
                out.append(f"   Di chuyển từ {origin}: {km:.1f} km, khoảng {minutes} phút "
                           f"({'ô tô/Grab' if by_car else 'xe máy'})")
            else:
                missing_coordinates = True
                out.append("   Chưa có tọa độ chính xác để ước tính quãng đường.")

            if rainy and is_outdoor(p):
                out.append("   Lưu ý: dự báo có thể mưa vào giờ này, mang theo áo mưa.")

            pos, t, first = place_coords, e, False

    if missing_coordinates:
        out.append(
            "\nMột số địa điểm chưa có tọa độ nên chưa thể ước tính quãng đường "
            "hoặc thời gian di chuyển; vui lòng kiểm tra bản đồ trước khi đi."
        )
    else:
        out.append("\nQuãng đường và thời gian di chuyển là ước tính; "
                   "bạn nên kiểm tra bản đồ trước khi đi.")
    return "\n".join(out)


# ---------------------------------------------------------------
# "Gan day" + rating cao
# ---------------------------------------------------------------
def nearby(db: Session, category: str, lat: float, lng: float, vi: bool = True,
           limit: int = 5, radius: float = 6.0) -> str:
    rows = db.query(Place).filter(
        Place.is_active == True, Place.category == category  # noqa: E712
    ).all()

    cand = []
    for p in rows:
        c = coord(p)
        if c:
            km = haversine((lat, lng), c)
            if km <= radius:
                cand.append((p, km))

    if not cand:
        if not any(coord(p) for p in rows):
            return (
                "Chưa có tọa độ địa điểm để tìm nơi gần bạn. "
                "Vui lòng kiểm tra danh sách địa điểm sau khi được bổ sung vị trí."
                if vi else
                "No place coordinates are available for nearby search yet."
            )
        return f"Không có địa điểm phù hợp trong bán kính {radius:.0f} km quanh bạn."

    # rating cao truoc, cung rating thi gan hon
    cand.sort(key=lambda x: (-(getattr(x[0], "rating", None) or 0), x[1]))

    has_rating = any(getattr(p, "rating", None) for p, _ in cand)
    lines = ["Gần bạn nhất" + (", ưu tiên đánh giá cao:" if has_rating else ":"), ""]

    for i, (p, km) in enumerate(cand[:limit], 1):
        r = getattr(p, "rating", None)
        lines.append(f"{i}. {p.name}" + (f" ({r}/5)" if r else ""))
        mins = round(km * ROAD_FACTOR / SPEED_BIKE * 60) + 3
        lines.append(f"   Cách bạn {km:.1f} km (~{mins} phút xe máy)")
        if p.address:
            lines.append(f"   Địa chỉ: {p.address}")
        if p.opening_hours:
            lines.append(f"   Giờ mở cửa: {p.opening_hours}")

    return "\n".join(lines)


# ---------------------------------------------------------------
# Thoi tiet
# ---------------------------------------------------------------
def weather_text(lat=None, lng=None, days: int = 3) -> str:
    if lat is None or lng is None:
        lat, lng = DANANG
    ws = fetch_weather(lat, lng, days)
    if not ws:
        return "Mình chưa lấy được dự báo thời tiết lúc này."

    lines = ["Dự báo thời tiết:"]
    for w in ws:
        lines.append(f"- {w['date']}: {w['tmin']:.0f}–{w['tmax']:.0f}°C, "
                     f"mưa {w['rain_prob']}%. {day_advice(w)[0]}")
    return "\n".join(lines)
