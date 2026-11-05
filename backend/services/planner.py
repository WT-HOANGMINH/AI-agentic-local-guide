"""Planner: gom điểm gần nhau theo ngày, xếp theo giờ mở cửa, thời lượng và thời gian di chuyển.

Tọa độ (nếu có) chỉ dùng để tính khoảng cách; thiếu tọa độ thì dùng bảng thời gian giữa các khu vực (zone).
Các con số trong _Z là ước lượng thô (xe máy/taxi, đường thông thường) - hãy đối chiếu Google Maps và chỉnh.

Thay đổi so với bản trước:
- Giờ bắt đầu mỗi điểm được làm tròn LÊN bội số 5 phút (không còn 09:29, 12:57...).
- Cuối ngày: thêm khối "Di chuyển về nơi lưu trú (ước tính)" và "Nghỉ ngơi" thay cho khối
  "thời gian tự do" chung chung. Thời gian về nơi lưu trú là ƯỚC TÍNH (tính về khu trung tâm,
  vì hệ thống chưa biết khách sạn của người dùng ở đâu).
"""
from math import radians, sin, cos, asin, sqrt
from itertools import combinations

from backend.services.place_enrichment import best_time_for, duration_for, parse_hours, zone_of

ZONE_NAMES = {
    "trung_tam": "trung tâm", "son_tra": "biển Sơn Trà", "son_tra_ban_dao": "bán đảo Sơn Trà",
    "ngu_hanh_son": "Ngũ Hành Sơn", "hoa_vang": "Hòa Vang", "ba_na": "Bà Nà", "lien_chieu": "Liên Chiểu",
    "hoi_an": "Hội An", "my_son": "Mỹ Sơn", "cu_lao_cham": "Cù Lao Chàm",
}
BUCKET = {"morning": 0, "afternoon": 1, "sunset": 2, "night": 3}
EARLIEST = {1: 13 * 60, 2: 17 * 60 + 15, 3: 19 * 60}

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


def _r5(m):
    """Làm tròn LÊN bội số 5 phút để giờ trong lịch trình tự nhiên hơn."""
    return (int(m) + 4) // 5 * 5


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


def _best_time(p):
    value = _g(p, "best_time")
    if value in BUCKET:
        return value
    return best_time_for(
        p.name,
        _g(p, "description", ""),
        to_str(opens(p)),
        p.category,
    )


def bucket(p):
    return BUCKET.get(_best_time(p), 1)


def earliest(p):
    best_time = _best_time(p)
    return EARLIEST.get(BUCKET.get(best_time), 0) if best_time else 0


def place_zone(p):
    return _g(p, "zone") or zone_of(p.name, _g(p, "address", "") or "")


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
    return zone_minutes(place_zone(a), place_zone(b))


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
    day_end=None,
    coffee=None,
    rest_min=0,
):
    day_end_min = (
        22 * 60
        if day_end is None
        else to_min(day_end) if isinstance(day_end, str) else day_end
    )
    # Compatibility aliases used by the dialogue layer.
    if cafe_stop is None and coffee is not None:
        cafe_stop = coffee
    rest_duration = int(rest_min or (60 if midday_rest else 0))
    orig_avoid = set(avoid)
    avoid = set(avoid)
    t, cur = to_min(day_start), None
    stops, dropped, dropped_ids = [], [], []
    if pinned is None:                       # điểm cả ngày (vd Bà Nà) luôn đi đầu tiên, nếu không sẽ không còn đủ giờ
        pinned = next((p for p in attrs if is_long(p)), None)
    order = order_nearest(attrs, pinned)
    daytime = [p for p in order if bucket(p) < 2]
    has_afternoon_place = any(_best_time(p) == "afternoon" for p in daytime)
    afternoon_id = (
        daytime[1].id
        if day_end_min > 12 * 60 and len(daytime) >= 2 and not has_afternoon_place
        else None
    )
    naive, smart = route_minutes(attrs), route_minutes(order)
    done = {"lunch": False, "dinner": False}
    breaks = []
    rest_added = False
    travel_total = 0

    def add(p, kind, earliest_min=0):
        nonlocal t, cur, travel_total
        tr = travel_min(cur, p)
        start = _r5(max(t + tr, earliest_min, opens(p)))
        end = start + duration(p)
        if end > min(closes(p), day_end_min):
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
        if rest_duration > 0 and day_end_min > 14 * 60 and done["lunch"] and not rest_added:
            rest_start = max(t, 12 * 60)
            rest_end = min(day_end_min, rest_start + rest_duration)
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
        next_start = (
            max(t + travel_min(cur, nxt), earliest(nxt), opens(nxt),
                13 * 60 if nxt is not None and nxt.id == afternoon_id else 0)
            if nxt is not None
            else 0
        )
        needs_afternoon_lunch = (
            nxt is not None
            and (nxt.id == afternoon_id or _best_time(nxt) == "afternoon")
            and next_start >= 12 * 60
        )
        if (
            not done["lunch"]
            and foods
            and (
                t >= 11 * 60 - 15
                or (nxt is None and t < 11 * 60 + 15)
                or (t < 11 * 60 + 15 and needs_afternoon_lunch)
            )
        ):
            f = nearest(cur or nxt, foods, avoid)
            if f and add(f, "meal", 11 * 60 + 30):
                avoid.add(f.id)
            done["lunch"] = True
            continue
        want_dinner = (
            t >= 17 * 60 + 15
            or (nxt is not None and earliest(nxt) >= 19 * 60 and done["lunch"])
            or nxt is None
        )
        if not done["dinner"] and foods and want_dinner:
            f = nearest(cur or nxt, foods, avoid)
            if f and add(f, "meal", 18 * 60):
                avoid.add(f.id)
            done["dinner"] = True
            continue
        if nxt is None:
            break
        order.pop(0)
        visit_start = max(
            earliest(nxt),
            13 * 60 if nxt.id == afternoon_id else 0,
        )
        if not add(nxt, "visit", visit_start):
            dropped.append(nxt.name)
            dropped_ids.append(nxt.id)
        elif is_long(nxt) and to_min(stops[-1]["start"]) <= 11 * 60 + 30 <= to_min(stops[-1]["end"]):
            done["lunch"] = True      # ăn ngay tại khu du lịch dài

    has_evening_visit = any(
        stop["kind"] == "visit" and to_min(stop["start"]) >= 19 * 60
        for stop in stops
    )
    return_min = 0
    if stops and not has_evening_visit and day_end_min >= 18 * 60:
        # Cuối ngày: về nơi lưu trú rồi nghỉ ngơi. Chưa biết khách sạn ở đâu nên
        # thời gian về là ƯỚC TÍNH, tính về khu trung tâm.
        last_end = max(to_min(stop["end"]) for stop in stops)
        if last_end < 22 * 60:
            return_min = max(10, _r5(zone_minutes(place_zone(cur), "trung_tam"))) if cur is not None else 15
            back_end = last_end + return_min
            breaks.append({
                "start": to_str(last_end),
                "end": to_str(back_end),
                "name": f"Di chuyển về nơi lưu trú (ước tính ~{return_min} phút)",
            })
            had_dinner = any(
                stop["kind"] == "meal" and to_min(stop["start"]) >= 17 * 60
                for stop in stops
            )
            rest_end = min(22 * 60, max(back_end + 30, 21 * 60))
            if back_end < rest_end:
                breaks.append({
                    "start": to_str(back_end),
                    "end": to_str(rest_end),
                    "name": "Nghỉ ngơi, tắm rửa tại nơi lưu trú"
                    + ("" if had_dinner else " (có thể ăn tối nhẹ gần đó)"),
                })
            evening_start = max(rest_end, 19 * 60)
            if evening_start < day_end_min:
                breaks.append({
                    "start": to_str(evening_start),
                    "end": to_str(day_end_min),
                    "name": "Thời gian tự do buổi tối (nghỉ ngơi hoặc khám phá gần nơi lưu trú)",
                })
    elif day_end_min >= 21 * 60 and not has_evening_visit:
        # Ngày không có điểm nào xếp được: giữ khối thời gian tự do như trước.
        evening_start = 19 * 60
        evening_end = min(day_end_min, 21 * 60)
        if evening_start < evening_end:
            breaks.append({
                "start": to_str(evening_start),
                "end": to_str(evening_end),
                "name": "Thời gian tự do buổi tối (nghỉ ngơi hoặc khám phá gần nơi lưu trú)",
            })

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
            day_end=day_end_min,
            rest_min=rest_duration,
        )

    zones = sorted({zone_label(place_zone(p)) for p in attrs if place_zone(p)})
    long_p = next((p for p in attrs if is_long(p)), None)
    return {"start": day_start, "stops": stops, "breaks": breaks, "dropped": dropped, "dropped_ids": dropped_ids,
            "travel_min": travel_total, "saved": max(0, naive - smart), "zones": zones,
            "return_min": return_min,
            "long": {"name": long_p.name, "dur": duration(long_p)} if long_p else None}


def split_days(attrs, scores, n_days, per_day=4):
    pool, days = sorted(attrs, key=lambda p: -scores.get(p.id, 0)), []
    for _ in range(n_days):
        if not pool:
            break
        seed = pool.pop(0)
        day = [seed]
        if not is_long(seed):
            for target_bucket in (0, 1, 3):
                if len(day) >= per_day:
                    break
                candidates = [
                    p for p in pool
                    if not is_long(p) and bucket(p) == target_bucket
                ]
                if candidates:
                    candidate = min(
                        candidates,
                        key=lambda p: travel_min(seed, p) - 40 * scores.get(p.id, 0),
                    )
                    day.append(candidate)
                    pool.remove(candidate)
            while len(day) < per_day:
                candidates = [p for p in pool if not is_long(p)]
                if not candidates:
                    break
                candidate = min(
                    candidates,
                    key=lambda p: travel_min(seed, p) - 40 * scores.get(p.id, 0),
                )
                day.append(candidate)
                pool.remove(candidate)
        days.append(day)
    return days


def split_morning_days(attrs, scores, n_days, per_day, day_start, day_end):
    pool, days = list(attrs), []
    for _ in range(n_days):
        if not pool:
            break
        candidates = sorted(pool, key=lambda p: -scores.get(p.id, 0))[:18]
        best_group, best_value = None, None
        for size in range(min(per_day, len(candidates)), 0, -1):
            for group in combinations(candidates, size):
                result = build_day(
                    group,
                    [],
                    day_start=day_start or "08:00",
                    day_end=day_end,
                )
                scheduled = {
                    stop["id"] for stop in result["stops"] if stop["kind"] == "visit"
                }
                if len(scheduled) != size:
                    continue
                ordered = order_nearest(group)
                value = (
                    sum(scores.get(place.id, 0) for place in group),
                    -route_minutes(ordered),
                )
                if best_value is None or value > best_value:
                    best_group, best_value = group, value
            if best_group is not None:
                break
        if best_group is None:
            best_group = (candidates[0],)
        days.append(list(best_group))
        selected = {place.id for place in best_group}
        pool = [place for place in pool if place.id not in selected]
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
    day_end=None,
    per_day=4,
):
    out, used = [], set()
    day_end_min = (
        22 * 60
        if day_end is None
        else to_min(day_end) if isinstance(day_end, str) else day_end
    )
    eligible = [
        p for p in attrs
        if max(to_min(day_start or "08:00"), earliest(p), opens(p)) + duration(p) <= day_end_min
    ]
    if day_end_min <= 12 * 60:
        start_min = to_min(day_start or "08:00")
        visit_budget = max(0, day_end_min - start_min)
        max_duration = visit_budget // max(per_day - 1, 1)
        compact = [p for p in eligible if duration(p) <= max_duration]
        if len(compact) >= per_day:
            eligible = compact
    day_count = max(1, n_days)
    day_capacity = min(per_day, max(1, (len(eligible) + day_count - 1) // day_count))
    if day_end_min <= 12 * 60:
        groups = split_morning_days(
            eligible, scores, day_count, day_capacity, day_start, day_end_min
        )
    else:
        groups = split_days(eligible, scores, day_count, day_capacity)
    for group in groups:
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
            day_end=day_end_min,
        )
        used |= {s["id"] for s in res["stops"] if s["kind"] == "meal"}
        res["attr_ids"] = [p.id for p in group if p.id not in res["dropped_ids"]]
        out.append(res)
    return out

# ---------------------------------------------------------------------------
# Compatibility layer for the V2 dialogue service.
# The newer dialogue calls plan_groups(..., day_kwargs=...) and build_day(...,
# coffee=..., rest_min=...). These adapters keep that API while reusing the
# advanced time-window / travel-aware scheduler above.
# ---------------------------------------------------------------------------

def plan_groups(groups, foods, cafes=None, day_start=None, day_kwargs=None):
    out, used_meals = [], set()
    for group in groups:
        if not group:
            continue
        kw = dict(day_kwargs(group, used_meals)) if day_kwargs else {}
        day_foods = kw.pop("foods", foods)
        must_ids = set(kw.pop("must_ids", ()))
        custom_start = kw.pop("day_start", None)
        start = day_start or custom_start or (
            "07:00" if any(is_long(p) for p in group) else "08:00"
        )
        # V2's "coffee" and "rest_min" names are accepted by build_day.
        result = build_day(
            group, day_foods, cafes, start,
            avoid=used_meals, **kw
        )
        used_meals.update(
            stop["id"] for stop in result["stops"]
            if stop.get("kind") == "meal" and stop.get("id") is not None
        )
        result["attr_ids"] = [
            p.id for p in group if p.id not in set(result["dropped_ids"])
        ]
        result["opts"] = {
            "breakfast_id": getattr(kw.get("breakfast"), "id", None),
            "coffee_id": getattr(kw.get("coffee"), "id", None),
            "rest_min": int(kw.get("rest_min", 0) or 0),
            "must_ids": sorted(must_ids),
        }
        out.append(result)
    return out
