"""Planner: gom điểm gần nhau theo ngày, xếp theo giờ mở cửa, thời lượng và thời gian di chuyển.

Tọa độ (nếu có) chỉ dùng để tính khoảng cách; thiếu tọa độ thì dùng bảng thời gian giữa các khu vực (zone).
Các con số trong _Z là ước lượng thô (xe máy/taxi, đường thông thường) - hãy đối chiếu Google Maps và chỉnh.
"""
from math import radians, sin, cos, asin, sqrt

from backend.services.place_enrichment import duration_for, parse_hours

ZONE_NAMES = {
    "trung_tam": "trung tâm", "son_tra": "biển Sơn Trà", "son_tra_ban_dao": "bán đảo Sơn Trà",
    "ngu_hanh_son": "Ngũ Hành Sơn", "hoa_vang": "Hòa Vang", "ba_na": "Bà Nà", "lien_chieu": "Liên Chiểu",
    "hoi_an": "Hội An", "my_son": "Mỹ Sơn", "cu_lao_cham": "Cù Lao Chàm",
}
BUCKET = {"morning": 0, "afternoon": 1, "sunset": 2, "night": 3}
EARLIEST = {2: 17 * 60 + 15, 3: 19 * 60}   # sunset, night: không xếp sớm hơn

_Z = {("trung_tam", "son_tra"): 15, ("trung_tam", "son_tra_ban_dao"): 35, ("trung_tam", "ngu_hanh_son"): 25,
      ("trung_tam", "hoa_vang"): 40, ("trung_tam", "ba_na"): 50, ("trung_tam", "lien_chieu"): 35,
      ("trung_tam", "hoi_an"): 45, ("trung_tam", "my_son"): 100, ("trung_tam", "cu_lao_cham"): 120,
      ("son_tra", "son_tra_ban_dao"): 20, ("son_tra", "ngu_hanh_son"): 15, ("son_tra", "hoi_an"): 40,
      ("son_tra", "ba_na"): 55, ("ngu_hanh_son", "hoi_an"): 25, ("ngu_hanh_son", "ba_na"): 55,
      ("ngu_hanh_son", "my_son"): 70, ("hoa_vang", "ba_na"): 20, ("hoa_vang", "hoi_an"): 60,
      ("lien_chieu", "ba_na"): 45, ("hoi_an", "my_son"): 60, ("hoi_an", "cu_lao_cham"): 60,
      ("son_tra_ban_dao", "hoi_an"): 60}
SAME_ZONE = {"hoi_an": 8, "ba_na": 5, "son_tra_ban_dao": 15, "cu_lao_cham": 10}


def to_min(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def to_str(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _g(p, name, default=None):
    v = getattr(p, name, None)
    return default if v is None else v


def zone_label(z):
    return ZONE_NAMES.get(z, z.replace("_", " ").title())


def duration(p):
    return _g(p, "duration_min") or duration_for(p.name, p.category)


def is_long(p):
    return duration(p) >= 240


def opens(p):
    opening = _g(p, "open_time")
    if not opening:
        opening, _ = parse_hours(_g(p, "opening_hours"))
    return to_min(opening or "00:00")


def closes(p):
    closing = _g(p, "close_time")
    if not closing:
        _, closing = parse_hours(_g(p, "opening_hours"))
    return to_min(closing or "23:59")


def bucket(p):
    return BUCKET.get(_g(p, "best_time"), 1)


def earliest(p):
    return EARLIEST.get(bucket(p), 0)


def has_coords(p):
    return p.latitude is not None and p.longitude is not None


def km(a, b):
    la1, lo1, la2, lo2 = map(radians, (a.latitude, a.longitude, b.latitude, b.longitude))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 12742 * asin(sqrt(h))


def _hub(z):
    return 0 if z == "trung_tam" else _Z.get(("trung_tam", z))


def zone_minutes(za, zb):
    if not za or not zb:
        return 25
    if za == zb:
        return SAME_ZONE.get(za, 10)
    for k in ((za, zb), (zb, za)):
        if k in _Z:
            return _Z[k]
    ha, hb = _hub(za), _hub(zb)          # không có trong bảng: đi qua trung tâm
    return ha + hb if ha is not None and hb is not None else 45


def travel_min(a, b):
    if a is None or b is None or a.id == b.id:
        return 0
    if has_coords(a) and has_coords(b):
        return int(km(a, b) * 1.4 / 30 * 60) + 5     # ~30 km/h, đường thực tế x1.4
    return zone_minutes(_g(a, "zone"), _g(b, "zone"))


def route_minutes(order):
    return sum(travel_min(a, b) for a, b in zip(order, order[1:]))


def order_nearest(attrs, pinned=None):
    rest, out = sorted(attrs, key=bucket), []
    if pinned is not None:
        out.append(pinned)
        rest = [p for p in rest if p.id != pinned.id]
    while rest:
        low = min(bucket(p) for p in rest)
        pool = [p for p in rest if bucket(p) == low]
        nxt = min(pool, key=lambda p: travel_min(out[-1], p)) if out else pool[0]
        rest.remove(nxt)
        out.append(nxt)
    return out


def nearest(cur, cands, avoid):
    c = [p for p in cands if p.id not in avoid]
    return min(c, key=lambda p: travel_min(cur, p)) if c else None


def build_day(
    attrs,
    foods,
    cafes=None,
    day_start="08:00",
    pinned=None,
    breakfast=None,
    avoid=(),
    _retry=False,
    cafe_stop=None,
    midday_rest=False,
):
    day_end = 22 * 60
    orig_avoid = set(avoid)
    avoid = set(avoid)
    t, cur = to_min(day_start), None
    stops, dropped, dropped_ids = [], [], []
    if pinned is None:                       # điểm cả ngày (vd Bà Nà) luôn đi đầu tiên, nếu không sẽ không còn đủ giờ
        pinned = next((p for p in attrs if is_long(p)), None)
    order = order_nearest(attrs, pinned)
    naive, smart = route_minutes(attrs), route_minutes(order)
    done = {"lunch": False, "dinner": False}
    breaks = []
    rest_added = False
    travel_total = 0

    def add(p, kind, earliest_min=0):
        nonlocal t, cur, travel_total
        tr = travel_min(cur, p)
        start = max(t + tr, earliest_min, opens(p))
        end = start + duration(p)
        if end > min(closes(p), day_end):
            return False
        stops.append({"id": p.id, "name": p.name, "kind": kind, "start": to_str(start), "end": to_str(end)})
        travel_total += tr
        t, cur = end, p
        return True

    if breakfast is not None and add(breakfast, "meal"):
        avoid.add(breakfast.id)
    if cafe_stop is not None and add(cafe_stop, "cafe", 8 * 60):
        avoid.add(cafe_stop.id)

    while order or not done["dinner"]:
        nxt = order[0] if order else None
        if midday_rest and done["lunch"] and not rest_added:
            rest_start = t
            rest_end = max(rest_start, 14 * 60)
            if rest_end > rest_start:
                breaks.append({
                    "start": to_str(rest_start),
                    "end": to_str(rest_end),
                    "name": "Nghỉ ngơi",
                })
                t = rest_end
            rest_added = True
        if not done["lunch"] and t >= 15 * 60:
            done["lunch"] = True             # đã quá giờ ăn trưa: không chèn bữa trưa lúc chiều tối
        if not done["lunch"] and not foods and t >= 11 * 60:
            done["lunch"] = True
            continue
        if not done["lunch"] and foods and t >= 11 * 60 - 15:
            f = nearest(cur or nxt, foods, avoid)
            if f and add(f, "meal", 11 * 60 + 30):
                avoid.add(f.id)
            done["lunch"] = True
            continue
        want_dinner = t >= 17 * 60 + 15 or (nxt is not None and earliest(nxt) >= 19 * 60 and done["lunch"])
        if not done["dinner"] and foods and want_dinner:
            f = nearest(cur or nxt, foods, avoid)
            if f and add(f, "meal", 18 * 60):
                avoid.add(f.id)
            done["dinner"] = True
            continue
        if nxt is None:
            break
        order.pop(0)
        if not add(nxt, "visit", earliest(nxt)):
            dropped.append(nxt.name)
            dropped_ids.append(nxt.id)
        elif is_long(nxt) and to_min(stops[-1]["start"]) <= 11 * 60 + 30 <= to_min(stops[-1]["end"]):
            done["lunch"] = True      # ăn ngay tại khu du lịch dài

    # Điểm đầu mở cửa muộn hơn giờ bắt đầu: dời giờ bắt đầu cho khớp thay vì chờ vô nghĩa.
    if stops and not breakfast and not _retry and to_min(stops[0]["start"]) - to_min(day_start) > 30:
        return build_day(
            attrs,
            foods,
            cafes,
            stops[0]["start"],
            pinned,
            None,
            orig_avoid,
            _retry=True,
            cafe_stop=cafe_stop,
            midday_rest=midday_rest,
        )

    zones = sorted({zone_label(_g(p, "zone")) for p in attrs if _g(p, "zone")})
    long_p = next((p for p in attrs if is_long(p)), None)
    return {"start": day_start, "stops": stops, "breaks": breaks, "dropped": dropped, "dropped_ids": dropped_ids,
            "travel_min": travel_total, "saved": max(0, naive - smart), "zones": zones,
            "long": {"name": long_p.name, "dur": duration(long_p)} if long_p else None}


def split_days(attrs, scores, n_days, per_day=3):
    pool, days = sorted(attrs, key=lambda p: -scores.get(p.id, 0)), []
    for _ in range(n_days):
        if not pool:
            break
        seed = pool.pop(0)
        day = [seed]
        if not is_long(seed):
            near = sorted((p for p in pool if not is_long(p)),
                          key=lambda p: travel_min(seed, p) - 40 * scores.get(p.id, 0))
            for p in near[:per_day - 1]:
                day.append(p)
                pool.remove(p)
        days.append(day)
    return days


def plan_trip(
    attrs,
    foods,
    cafes,
    scores,
    n_days,
    day_start=None,
    breakfast=None,
    cafe=None,
    midday_rest=False,
):
    out, used = [], set()
    for group in split_days(attrs, scores, n_days):
        start = day_start or ("07:00" if any(is_long(p) for p in group) else "08:00")
        res = build_day(
            group,
            foods,
            cafes,
            start,
            breakfast=breakfast if not out else None,
            avoid=used,
            cafe_stop=cafe if not out else None,
            midday_rest=midday_rest,
        )
        used |= {s["id"] for s in res["stops"] if s["kind"] == "meal"}
        res["attr_ids"] = [p.id for p in group if p.id not in res["dropped_ids"]]
        out.append(res)
    return out
