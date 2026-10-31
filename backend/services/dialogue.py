"""Bộ điều phối hội thoại: hiểu (intent + slot) -> hỏi lại nếu thiếu -> chọn địa điểm / lập lịch / chỉnh lịch -> diễn đạt."""
import re
from dataclasses import dataclass, field
from urllib.parse import quote

from backend.services import nlg, place_repo
from backend.services import planner as pl
from backend.services import planner_service
from backend.services.place_enrichment import zone_of
from backend.services.ranker import INTEREST_QUERY, MEAL_QUERY, get_ranker
from backend.services.slot_service import extract_slots, strip_accents

CATEGORY_OF = {"food": {"restaurant"}, "cafe": {"cafe"}, "attraction": {"tourist_attraction"},
               "accommodation": {"hotel", "homestay", "accommodation", "resort"}}
REMOVE_RE = re.compile(r"\b(bo|bot|xoa|loai|remove|drop|delete)\b")
ADD_RE = re.compile(r"\b(them|add|include)\b")
DAY_RE = re.compile(r"\b(?:ngay|day)\s*(\d)\b")
FLEX_RE = re.compile(r"(tuy ban|gi cung duoc|bat ky|up to you|you decide|anything)")
PERSIST = {
    "days", "interests", "budget_vnd", "budget_level", "people",
    "start_time", "early", "flexible", "zone", "include_meals",
    "meal", "food_query", "cafe_requested", "midday_rest", "companion",
}
MEAL_WINDOW = {"breakfast": ("08:00", "09:00"), "lunch": ("11:30", "13:00"), "dinner": ("18:30", "20:00")}


BYE_RE = re.compile(r"\b(cam on|thanks|thank you|tam biet|bye|het roi|khong can gi them|khong can gi nua)\b")
CLOSING_INTENTS = {"attraction", "food", "cafe", "accommodation", "itinerary", "modify_itinerary",
                   "transport", "ask_detail", "weather"}
# Từ quá chung chung: không dùng một mình để nhận ra tên địa điểm
_GENERIC = {"bai", "bien", "cau", "chua", "cho", "pho", "khu", "du", "lich", "nha", "hang", "quan",
            "ca", "phe", "cafe", "coffee", "cong", "vien", "dao", "ban", "dia", "bao", "tang", "lang",
            "hoi", "da", "nang", "di", "den", "tu", "the", "and"}


class StepList(list):
    """Danh sách bước xử lý. Mỗi bước được thêm vào sẽ gọi on_step ngay,
    để giao diện hiện tiến trình THẬT (không phải chạy xong mới kể lại)."""

    def __init__(self, on_step=None):
        super().__init__()
        self._cb = on_step

    def _emit(self, items):
        if self._cb:
            for item in items:
                try:
                    self._cb(item)
                except Exception:
                    pass

    def append(self, item):
        super().append(item)
        self._emit([item])

    def extend(self, items):
        items = list(items)
        super().extend(items)
        self._emit(items)

    def __iadd__(self, items):
        self.extend(items)
        return self


@dataclass
class State:
    slots: dict = field(default_factory=dict)
    pending: str | None = None
    pending_for: str | None = None
    asked: set = field(default_factory=set)
    plan: list = field(default_factory=list)
    lang: str = "vi"
    search_nearby: bool = False
    pos: tuple | None = None            # (lat, lng) khi người dùng cho phép chia sẻ vị trí
    route_dest: int | None = None       # id điểm đến đang chờ điểm xuất phát
    route_dest_name: str | None = None
    links: list = field(default_factory=list)   # nút liên kết gửi kèm câu trả lời (Google Maps...)
    unscheduled_places: list = field(default_factory=list)
    requested_place_ids: list = field(default_factory=list)


def is_attraction(p):
    if p.category == "tourist_attraction":
        return True
    return p.category == "shopping" and strip_accents(p.name).startswith(("cho ", "lang "))


def fits_meal(p, meal):
    ot, ct = getattr(p, "open_time", None), getattr(p, "close_time", None)
    if not meal or not ot or not ct:
        return True
    must_open_by, must_close_after = MEAL_WINDOW[meal]
    return ot <= must_open_by and ct >= must_close_after


def _slug(s):
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(s)).strip()


def _match_places(db, msg, categories=None):
    """Nhận ra địa điểm được nhắc trong câu, kể cả khi người dùng gõ thiếu
    (vd "Chùa Linh Ứng" -> "Chùa Linh Ứng Sơn Trà"). Trả về [(place, vị_trí_trong_câu)] theo thứ tự xuất hiện."""
    m = " " + _slug(msg) + " "
    hits = []
    for p in place_repo.all_active(db):
        if categories and p.category not in categories:
            continue
        toks = _slug(short(p.name)).split()
        found = None
        for n in range(len(toks), 1, -1):
            for i in range(len(toks) - n + 1):
                part = toks[i:i + n]
                gram = " ".join(part)
                if all(t in _GENERIC for t in part) or len(gram) < 5:
                    continue
                at = m.find(" " + gram + " ")
                if at >= 0:
                    found = (n, len(gram), at, n / len(toks))
                    break
            if found:
                break
        if found:
            hits.append((p, *found))
    hits.sort(key=lambda h: (-h[1], -h[4], -h[2]))
    chosen = []
    for p, n, ln, at, _cov in hits:
        span = (at, at + ln + 2)
        if any(span[0] < c[1][1] and c[1][0] < span[1] for c in chosen):
            continue                               # đã được một địa điểm khớp tốt hơn chiếm chỗ
        chosen.append((p, span))
    chosen.sort(key=lambda c: c[1][0])
    return [(p, span[0]) for p, span in chosen]


def find_place(db, names, message):
    msg = strip_accents(message)
    cands = [c for c in (strip_accents(n) for n in names) if len(c) > 2]
    best, best_len = None, 0
    for p in place_repo.all_active(db):
        pn = strip_accents(p.name)
        hits = [len(c) for c in cands if c in pn or pn in c] + ([len(pn)] if pn in msg else [])
        if hits and max(hits) > best_len:
            best, best_len = p, max(hits)
    if best is None:
        fuzzy = _match_places(db, " ".join([message] + list(names)))
        best = fuzzy[0][0] if fuzzy else None
    return best


def merge_slots(st, slots):
    for k, v in slots.items():
        if k not in PERSIST:
            continue
        if k == "interests":
            cur = st.slots.setdefault("interests", [])
            cur.extend(i for i in v if i not in cur)
        else:
            st.slots[k] = v


# ---------- hiển thị ----------
def render_days(plan, lang, only=None):
    out = []
    for i, d in enumerate(plan):
        if only is not None and i not in only:
            continue
        out.append(f"\n{nlg.say('day', lang)} {i + 1}")
        events = [
            (s["start"], s["end"], s["name"], s["kind"])
            for s in d["stops"]
        ]
        events.extend(
            (item["start"], item["end"], item["name"], "rest")
            for item in d.get("breaks", [])
        )
        for start, end, name, kind in sorted(events):
            tag = nlg.say("meal_tag", lang) if kind == "meal" else ""
            out.append(f"  {start}–{end}  {name}{tag}")
    return "\n".join(out)


def explain(plan, lang, only=None):
    out = []
    for i, d in enumerate(plan):
        if only is not None and i != only:
            continue
        if d["saved"] >= 10:
            out.append(nlg.say("explain_saved", lang, d=i + 1, t=d["travel_min"], s=d["saved"]))
        elif d["travel_min"] == 0:
            pass                                    # chỉ một điểm: không có gì để nói về di chuyển
        elif d["zones"] and len(d["zones"]) <= 2:
            out.append(nlg.say("explain_near", lang, d=i + 1, t=d["travel_min"], zones=", ".join(d["zones"])))
        else:
            out.append(nlg.say("explain_near2", lang, d=i + 1, t=d["travel_min"]))
        if d["long"]:
            out.append(nlg.say("explain_long", lang, name=short(d["long"]["name"]), h=round(d["long"]["dur"] / 60, 1), start=d["start"]))
        if any(s["kind"] == "meal" for s in d["stops"]):
            out.append(nlg.say("explain_meal", lang, d=i + 1))
        if d["dropped"]:
            out.append(nlg.say("explain_dropped", lang, names=", ".join(d["dropped"])))
    return " ".join(out)


def short(name):
    """Tên ngắn dùng trong câu văn: bỏ phần trong ngoặc."""
    return re.sub(r"\s*\([^)]*\)", "", name).strip() or name


def brief(p):
    desc = (p.description or "").strip().split(". ")[0][:110]
    bits = [desc] if desc else []
    if p.opening_hours and "kiem tra" not in strip_accents(p.opening_hours):
        bits.append(p.opening_hours)
    return " – ".join(bits)


# ---------- xử lý từng loại yêu cầu ----------
def handle_search(st, db, intent, msg, slots, place, steps):
    lang, meal = st.lang, slots.get("meal")
    normalized = strip_accents(msg)
    near_requested = bool(
        re.search(r"\b(gan toi|gan day|near me|nearby)\b", normalized)
    ) or (st.pending == "location" and st.pos is not None and "vi tri" in normalized)
    if near_requested and place is None and st.pos is not None:
        category = sorted(CATEGORY_OF[intent])[0]
        steps.append("Đang tìm địa điểm gần vị trí của bạn...")
        st.pending = st.pending_for = None
        st.search_nearby = False
        return planner_service.nearby(db, category, st.pos[0], st.pos[1], lang == "vi")
    if near_requested and place is None:
        st.pending = "location"
        st.pending_for = intent
        st.search_nearby = True
        steps.append("Cần điểm xuất phát để tìm địa điểm gần bạn")
        return (
            "Bạn muốn tìm gần khu vực hoặc địa điểm nào? Mình chưa được cấp vị trí hiện tại của bạn."
            if lang == "vi"
            else "Which area or landmark should I search near? I don't have your current location."
        )

    if len(msg.split()) <= 3 and not slots and intent not in st.asked:
        st.asked.add(intent)
        st.pending = st.pending_for = intent
        steps.append("Câu hỏi còn thiếu thông tin → hỏi lại người dùng")
        return nlg.say(f"ask_{intent}", lang)
    st.pending = st.pending_for = None
    use_nearby_anchor = near_requested or st.search_nearby
    st.search_nearby = False
    st.asked.discard(intent)
    steps.append("Đang truy cập cơ sở dữ liệu địa điểm...")
    rk = get_ranker(db)
    query = " ".join([msg] + [INTEREST_QUERY[i] for i in slots.get("interests", [])] + [MEAL_QUERY.get(meal, "")])
    results = rk.rank(
        query,
        k=12,
        categories=CATEGORY_OF[intent],
        anchor=place if use_nearby_anchor else None,
    )
    steps.append(f"Đang xếp hạng {len(rk.places)} địa điểm theo yêu cầu" + (f", ưu tiên gần {place.name}" if place else ""))
    if meal:
        results = [p for p in results if fits_meal(p, meal)]
        steps.append(f"Lọc quán mở cửa phù hợp bữa {meal}: còn {len(results)} quán")
    if intent == "attraction" and re.search(
        r"\b(danh gia cao|rating|highest rated|top rated)\b", normalized
    ):
        results = sorted(
            (
                candidate for candidate in rk.places
                if candidate.category in CATEGORY_OF["attraction"]
                and candidate.rating is not None
            ),
            key=lambda candidate: candidate.rating,
            reverse=True,
        )
    results = results[:5 if intent == "attraction" else 4]
    if not results:
        return nlg.say("no_result", lang)
    lines = [nlg.search_intro(lang, place.name if place else "", meal)]
    lines += [f"{i}. {p.name}" + (f" – {brief(p)}" if brief(p) else "") for i, p in enumerate(results, 1)]
    return "\n".join(lines) + "\n\n" + nlg.say("search_followup", lang)


def handle_itinerary(st, db, place, steps, requested_places=()):
    lang, s, assumed = st.lang, st.slots, False
    if "days" not in s:
        if st.plan:
            s["days"] = len(st.plan)
        elif not s.get("flexible"):
            already_asked = "days" in st.asked
            st.asked.add("days")
            both = (
                not already_asked
                and not s.get("interests")
                and "interests" not in st.asked
            )
            if both:
                st.asked.add("interests")
            st.pending, st.pending_for = "days", "itinerary"
            steps.append("Thiếu số ngày" + (" và sở thích" if both else "") + " → hỏi lại người dùng")
            return nlg.say("ask_days_interest" if both else "ask_days", lang)
        else:
            s["days"], assumed = 1, True
    has_requested_content = bool(
        s.get("interests")
        or s.get("flexible")
        or requested_places
        or s.get("food_query")
        or s.get("cafe_requested")
    )
    if not has_requested_content:
        st.asked.add("interests")
        st.pending, st.pending_for = "interests", "itinerary"
        steps.append("Chưa rõ sở thích → hỏi lại người dùng")
        return nlg.say("ask_interest", lang)

    st.pending = st.pending_for = None
    steps.append("Đang truy cập cơ sở dữ liệu địa điểm...")
    rk = get_ranker(db)
    interests = s.get("interests", [])
    scores = rk.score_map(" ".join(INTEREST_QUERY[i] for i in interests) or "noi tieng pho bien")
    for requested in requested_places:
        scores[requested.id] = 2.0
    if place is not None and place.category == "tourist_attraction":
        scores[place.id] = 2.0
    selected_zone = s.get("zone")

    def in_zone(p):
        if not selected_zone:
            return True
        actual_zone = getattr(p, "zone", None) or zone_of(p.name, p.address or "")
        if selected_zone == "son_tra":
            return actual_zone in {"son_tra", "son_tra_ban_dao"}
        return actual_zone == selected_zone

    attrs = [p for p in rk.places if is_attraction(p) and in_zone(p)]
    low = s.get("budget_level") == "low" or (s.get("budget_vnd") or 10 ** 9) <= 500_000
    foods = [
        p for p in rk.places
        if p.category == "restaurant" and in_zone(p)
        and (not low or (p.price_level or 2) <= 2)
    ] if s.get("include_meals", True) else []
    cafes = [p for p in rk.places if p.category == "cafe" and in_zone(p)]
    if selected_zone and not attrs:
        return nlg.say("no_result", lang)
    start = s.get("start_time") or ("06:30" if s.get("early") else None)
    breakfast = None
    if s.get("meal") == "breakfast" and s.get("food_query"):
        food_scores = rk.score_map(s["food_query"])
        breakfast_options = [p for p in foods if fits_meal(p, "breakfast")]
        breakfast = max(
            breakfast_options,
            key=lambda p: food_scores.get(p.id, 0),
            default=None,
        )
    cafe = None
    if s.get("cafe_requested") and cafes:
        cafe = max(cafes, key=lambda p: p.rating or 0)
    st.plan = pl.plan_trip(
        attrs,
        foods,
        cafes,
        scores,
        int(s["days"]),
        start,
        breakfast=breakfast,
        cafe=cafe,
        midday_rest=bool(s.get("midday_rest")),
    )
    scheduled_ids = {
        place_id for day in st.plan for place_id in day["attr_ids"]
    }
    st.unscheduled_places = [
        short(p.name) for p in requested_places if p.id not in scheduled_ids
    ]
    if not st.plan:
        return nlg.say("no_result", lang)
    n_stops = sum(len(d["attr_ids"]) for d in st.plan)
    steps += [f"Chọn {n_stops} điểm trong {len(attrs)} địa điểm theo sở thích",
              "Gom các điểm gần nhau vào cùng một ngày",
              "Xếp theo giờ mở cửa, thời lượng tham quan và thời gian di chuyển"]
    for k in ("days", "start_time", "early"):
        s.pop(k, None)
    st.asked -= {"days", "interests"}

    topic = ""
    if interests:
        labs = ", ".join(nlg.label(i, lang) for i in interests)
        topic = f" (ưu tiên: {labs})" if lang == "vi" else f" (focus: {labs})"
    parts = [nlg.say("plan_intro", lang, n=len(st.plan), topic=topic)]
    if assumed:
        parts.append(nlg.say("plan_assumed", lang))
    if not interests:
        parts.append(nlg.say("plan_popular", lang))
    if s.get("companion") == "couple":
        parts.append("Mình đã ghi nhận chuyến đi của hai bạn, nên lịch trình sẽ ưu tiên nhịp đi vừa phải và có thời gian nghỉ nhé.")
    elif s.get("companion") == "family":
        parts.append("Mình sẽ ưu tiên lịch trình thoải mái để cả nhà có thời gian nghỉ giữa các điểm.")
    if breakfast:
        parts.append(f"Mình đã xếp bữa sáng với {short(breakfast.name)} theo món bạn thích.")
    if cafe:
        parts.append(f"Mình cũng chừa một điểm dừng cà phê: {short(cafe.name)}.")
    if st.unscheduled_places:
        parts.append(
            "Mình chưa xếp vừa "
            + ", ".join(st.unscheduled_places)
            + " vào lịch này để tránh lịch trình quá gấp. Bạn có thể thêm ngày hoặc chọn điểm ưu tiên nhé."
        )
    parts += [render_days(st.plan, lang), "", explain(st.plan, lang), "", nlg.say("plan_followup", lang)]
    if selected_zone:
        parts.append(
            f"Khu vực ưu tiên: {pl.zone_label(selected_zone)}."
            if lang == "vi"
            else f"Preferred area: {pl.zone_label(selected_zone)}."
        )
    return "\n".join(parts)


def replan_day(db, st, idx, pinned_id=None, start=None, remove_id=None, add_ids=(), breakfast=None):
    day = st.plan[idx]
    ids = [i for i in day["attr_ids"] if i != remove_id] + [i for i in add_ids if i not in day["attr_ids"]]
    by_id = {p.id: p for p in place_repo.by_ids(db, ids)}
    attrs = [by_id[i] for i in ids if i in by_id]
    foods = place_repo.restaurants(db)
    avoid = {s["id"] for j, d in enumerate(st.plan) if j != idx for s in d["stops"] if s["kind"] == "meal"}
    pinned = by_id.get(pinned_id)
    long_in = next((p for p in attrs if pl.is_long(p)), None)
    displaced = []
    if long_in is not None and len(attrs) > 1:      # điểm cả ngày chiếm trọn ngày: các điểm khác dời sang ngày khác
        displaced = [p for p in attrs if p.id != long_in.id]
        attrs, pinned = [long_in], long_in
    if start is None and pinned and pl.is_long(pinned) and pl.to_min(day["start"]) >= 7 * 60 + 30:
        start = "07:00"
    res = pl.build_day(attrs, foods, None, start or day["start"], pinned=pinned, breakfast=breakfast, avoid=avoid)
    gone = set(res["dropped_ids"]) | {p.id for p in displaced}
    res["attr_ids"] = [i for i in ids if i not in gone]
    res["dropped_ids"] = res["dropped_ids"] + [p.id for p in displaced]
    res["dropped"] = res["dropped"] + [p.name for p in displaced]
    st.plan[idx] = res
    return res


def relocate_dropped(db, st, idx):
    moved, res = [], st.plan[idx]
    for pid, name in list(zip(res["dropped_ids"], res["dropped"])):
        p = place_repo.get(db, pid)
        for j, d in enumerate(st.plan):
            if j == idx or len(d["attr_ids"]) >= 3 or pl.is_long(p):
                continue
            if any(pl.is_long(x) for x in place_repo.by_ids(db, d["attr_ids"])):
                continue                              # ngày đã có điểm cả ngày
            r = replan_day(db, st, j, add_ids=[pid])
            if pid in r["attr_ids"]:
                moved.append((name, j + 1))
                res["dropped"].remove(name)
                break
    return moved


def _day_of(st, pid):
    return next((i for i, d in enumerate(st.plan) if pid in d["attr_ids"]), None)


def handle_modify(st, db, msg, slots, place, steps):
    lang, cue = st.lang, strip_accents(msg)
    m = DAY_RE.search(cue)
    idx = int(m.group(1)) - 1 if m else None
    if place and idx is None:
        idx = _day_of(st, place.id)
    if idx is None or idx >= len(st.plan):
        idx = 0
    rk = get_ranker(db)
    first_ids = st.plan[idx]["attr_ids"]
    anchor = place_repo.get(db, first_ids[0]) if first_ids else None
    avoid = {s["id"] for d in st.plan for s in d["stops"]}
    wants_cafe = re.search(r"(cafe|ca phe|coffee)", cue)

    if REMOVE_RE.search(cue):
        if not place:
            return nlg.say("modify_which", lang)
        idx = _day_of(st, place.id)
        if idx is None:
            return nlg.say("not_in_plan", lang, name=place.name)
        replan_day(db, st, idx, remove_id=place.id)
        head = nlg.say("modify_removed", lang, name=place.name, d=idx + 1)
    elif ADD_RE.search(cue) and slots.get("meal") == "breakfast":
        pick = rk.rank(MEAL_QUERY["breakfast"], k=12, categories={"restaurant"}, anchor=anchor, exclude=avoid)
        pick = [p for p in pick if fits_meal(p, "breakfast")]
        if not pick:
            return nlg.say("no_result", lang)
        replan_day(db, st, idx, breakfast=pick[0])
        head = nlg.say("modify_added", lang, name=short(pick[0].name), d=idx + 1)
    elif ADD_RE.search(cue) and wants_cafe and not place:
        pick = rk.rank("ca phe view dep", k=1, categories={"cafe"}, anchor=anchor, exclude=avoid)
        if not pick:
            return nlg.say("no_result", lang)
        replan_day(db, st, idx, add_ids=[pick[0].id])
        head = nlg.say("modify_added", lang, name=short(pick[0].name), d=idx + 1)
    elif ADD_RE.search(cue) and place:
        have = _day_of(st, place.id)
        if have is not None:
            return nlg.say("already_in_plan", lang, name=place.name, d=have + 1)
        if not m:   # chọn ngày có điểm đầu tiên gần địa điểm này nhất
            def gap(i):
                ids = st.plan[i]["attr_ids"]
                return pl.travel_min(place_repo.get(db, ids[0]) if ids else None, place)
            idx = min(range(len(st.plan)), key=gap)
        replan_day(db, st, idx, add_ids=[place.id])
        head = nlg.say("modify_added", lang, name=short(place.name), d=idx + 1)
    else:
        new_start = slots.get("start_time") or ("06:30" if slots.get("early") else None)
        if not place and not new_start:
            return nlg.say("modify_which_time", lang)
        extra = [place.id] if place and _day_of(st, place.id) is None else []   # chưa có trong lịch: thêm luôn
        res = replan_day(db, st, idx, pinned_id=place.id if place else None, start=new_start, add_ids=extra)
        pin = (f" ({short(place.name)} đi đầu tiên)" if lang == "vi" else f" ({short(place.name)} first)") if place else ""
        head = nlg.say("modify_time", lang, d=idx + 1, pin=pin, start=res["start"])
        first = res["stops"][0] if res["stops"] else None
        if place and first and first["id"] == place.id and getattr(place, "open_time", None) == first["start"]:
            head += " " + nlg.say("earliest", lang, name=short(place.name), t=first["start"])
    steps.append(f"Xếp lại ngày {idx + 1} với ràng buộc mới")

    moved = relocate_dropped(db, st, idx)
    changed = [idx] + sorted({d - 1 for _, d in moved})
    parts = [head, render_days(st.plan, lang, changed), "", explain(st.plan, lang, idx)]
    parts += [nlg.say("moved", lang, name=n, d=d) for n, d in moved]
    return "\n".join(parts)


def _maps_url(dest, origin=None):
    """Liên kết chỉ đường Google Maps (không cần API key). Google tự tính đường tối ưu theo giao thông thực tế."""
    def point(x):
        if isinstance(x, tuple):
            return f"{x[0]},{x[1]}"
        if isinstance(x, str):
            return quote(x + " Đà Nẵng")
        if pl.has_coords(x):
            return f"{x.latitude},{x.longitude}"
        return quote(f"{short(x.name)} Đà Nẵng")

    url = "https://www.google.com/maps/dir/?api=1&destination=" + point(dest)
    if origin is not None:
        url += "&origin=" + point(origin)
    return url


def handle_transport(st, db, msg, slots, steps):
    lang = st.lang
    steps.append("Đang tìm địa điểm trong dữ liệu...")
    m = " " + _slug(msg) + " "
    matches = _match_places(db, msg)
    if not matches:
        for n in slots.get("places", []):
            p = find_place(db, [n], "")
            if p:
                matches.append((p, m.find(" " + _slug(n) + " ")))
    dest_mem = place_repo.get(db, st.route_dest) if st.route_dest else None

    origin = dest = None
    i_den = m.find(" den ")
    from_part = re.search(r" tu (.+?) den ", m)
    if from_part and i_den >= 0:                       # "từ A đến B"
        before = [p for p, at in matches if at < i_den]
        after = [p for p, at in matches if at > i_den]
        if before:
            origin = before[0]
        else:
            raw = re.search(r"(?i)\b(?:từ|tu)\s+(.+?)\s+(?:đến|den)\b", msg)
            origin = raw.group(1).strip() if raw else from_part.group(1).strip()
        dest = after[0] if after else dest_mem
    elif len(matches) >= 2:
        origin, dest = matches[0][0], matches[1][0]
    elif len(matches) == 1:
        p = matches[0][0]
        if dest_mem is not None and p.id != dest_mem.id:
            origin, dest = p, dest_mem                  # vừa chọn điểm xuất phát cho điểm đến đã nhớ
        else:
            dest, origin = p, st.pos
    elif dest_mem is not None:
        dest = dest_mem
        if st.pos:
            origin = st.pos
        elif st.pending == "origin" and not slots and 2 <= len(msg.strip()) <= 80:
            origin = msg.strip()                        # điểm xuất phát chưa có trong dữ liệu: dùng chữ người dùng gõ

    if dest is None:
        st.pending = st.pending_for = "transport"
        return nlg.say("ask_transport", lang)

    b = short(dest.name)
    if origin is None:
        st.pending, st.pending_for = "origin", "transport"
        st.route_dest, st.route_dest_name = dest.id, b
        st.links.append({"label": f"Mở Google Maps tới {b}", "url": _maps_url(dest)})
        steps.append(f"Đã nhận ra điểm đến: {b}")
        return nlg.say("ask_origin", lang, name=b)

    st.pending = st.pending_for = None
    st.route_dest = st.route_dest_name = None
    steps.append("Đang ước tính quãng đường...")
    steps.append("Đang tạo liên kết chỉ đường Google Maps...")
    st.links.append({"label": "Mở chỉ đường trên Google Maps", "url": _maps_url(dest, origin)})

    if isinstance(origin, str):
        return nlg.say("route_text_origin", lang, a=origin, b=b)
    if isinstance(origin, tuple):
        if not pl.has_coords(dest):
            return nlg.say("route_text_origin", lang, a="vị trí của bạn", b=b)
        km = planner_service.road_km(origin, (dest.latitude, dest.longitude))
        t = round(km / planner_service.SPEED_BIKE * 60) + 3
        return nlg.say("route_gps", lang, b=b, k=round(km, 1), t=t) + "\n" + nlg.say("route_note", lang)
    a = short(origin.name)
    t = pl.travel_min(origin, dest)
    if pl.has_coords(origin) and pl.has_coords(dest):
        text = nlg.say("route", lang, a=a, b=b, k=round(pl.km(origin, dest) * 1.35, 1), t=t)
    else:
        text = nlg.say("route_est", lang, a=a, b=b, t=t)
    return text + "\n" + nlg.say("route_note", lang)


def handle_detail(st, db, place):
    if not place:
        st.pending = st.pending_for = "ask_detail"
        return nlg.say("ask_which_place", st.lang)
    st.pending = st.pending_for = None
    vi = st.lang == "vi"
    lines = [place.name]
    if place.description:
        lines.append(place.description)
    if getattr(place, "open_time", None) and getattr(place, "close_time", None):
        lines.append(f"{'Giờ mở cửa' if vi else 'Hours'}: {place.open_time}–{place.close_time}")
    elif place.opening_hours:
        lines.append(f"{'Giờ mở cửa' if vi else 'Hours'}: {place.opening_hours}")
    if place.price_level:
        lines.append(f"{'Mức giá' if vi else 'Price level'}: {place.price_level}/5")
    if place.address:
        lines.append(f"{'Địa chỉ' if vi else 'Address'}: {place.address}")
    lines.append("Thông tin có thể thay đổi, bạn nên kiểm tra lại trước khi đi." if vi
                 else "Details may change; please double-check before you go.")
    return "\n".join(lines)


def conversation_suggestions(intent, st):
    def option(option_id, label, message, **extra):
        return {"id": option_id, "label": label, "message": message, **extra}

    geo = option("use-location", "📍 Dùng vị trí của tôi", "__geo__")

    if st.pending == "origin":
        d = st.route_dest_name or "đó"
        return [
            geo,
            option("from-dragon", "Từ Cầu Rồng", f"Từ Cầu Rồng đến {d}"),
            option("from-mykhe", "Từ biển Mỹ Khê", f"Từ biển Mỹ Khê đến {d}"),
            option("from-airport", "Từ sân bay", f"Từ sân bay Đà Nẵng đến {d}"),
        ]

    if st.pending == "location":
        return [
            geo,
            option("near-dragon-bridge", "Gần Cầu Rồng", "Tìm địa điểm gần Cầu Rồng"),
            option("near-my-khe", "Gần biển Mỹ Khê", "Tìm địa điểm gần biển Mỹ Khê"),
            option("near-son-tra", "Gần Sơn Trà", "Tìm địa điểm gần Bán đảo Sơn Trà"),
        ]

    if st.pending_for == "itinerary":
        if st.pending == "days":
            return [
                option("one-day", "1 ngày", "Lịch trình 1 ngày"),
                option("two-day", "2 ngày", "Lịch trình 2 ngày"),
                option("three-day", "3 ngày", "Lịch trình 3 ngày"),
                option("flexible", "Bạn tự đề xuất giúp tôi", "Tùy bạn, lịch trình 1 ngày"),
            ]
        if st.pending == "interests":      # chọn nhiều (tick) rồi bấm Gửi
            return [
                option("beach", "Biển", "biển"),
                option("nature", "Thiên nhiên", "thiên nhiên"),
                option("culture", "Văn hóa", "văn hóa"),
                option("food", "Ẩm thực", "ẩm thực"),
                option("sunset", "Hoàng hôn", "hoàng hôn"),
                option("photo", "Chụp ảnh check-in", "chụp ảnh check-in"),
                option("flexible", "Tùy bạn", "Tùy bạn", exclusive=True),
            ]

    if st.pending_for == intent and st.pending == intent:      # câu hỏi quá ngắn: gợi ý hướng trả lời
        if intent == "attraction":
            return [
                option("a-beach", "Biển", "Gợi ý 5 địa điểm biển đẹp ở Đà Nẵng"),
                option("a-nature", "Thiên nhiên", "Gợi ý 5 địa điểm thiên nhiên ở Đà Nẵng"),
                option("a-culture", "Văn hóa, lịch sử", "Gợi ý 5 địa điểm văn hóa lịch sử ở Đà Nẵng"),
                option("a-popular", "Nổi tiếng nhất", "Gợi ý 5 địa điểm nổi tiếng ở Đà Nẵng"),
                option("a-near", "Gần tôi", "Tìm địa điểm gần tôi"),
            ]
        if intent == "food":
            return [
                option("f-breakfast", "Ăn sáng", "Gợi ý quán ăn sáng ở Đà Nẵng"),
                option("f-lunch", "Ăn trưa", "Gợi ý quán ăn trưa ở Đà Nẵng"),
                option("f-dinner", "Ăn tối", "Gợi ý quán ăn tối ở Đà Nẵng"),
                option("f-near", "Gần tôi", "Tìm quán ăn gần tôi"),
            ]
        if intent == "cafe":
            return [
                option("c-view", "Cà phê view đẹp", "Gợi ý quán cà phê view đẹp ở Đà Nẵng"),
                option("c-work", "Cà phê làm việc", "Gợi ý quán cà phê yên tĩnh để làm việc ở Đà Nẵng"),
                option("c-near", "Gần tôi", "Tìm quán cà phê gần tôi"),
            ]

    if intent == "attraction":
        return [
            option("popular", "Nổi bật nhất", "Gợi ý 5 địa điểm nổi tiếng ở Đà Nẵng"),
            option("highest-rated", "Được đánh giá cao", "Gợi ý 5 địa điểm được đánh giá cao nhất ở Đà Nẵng"),
            option("nearby", "Gần tôi", "Tìm 5 địa điểm nổi tiếng gần tôi nhất"),
            option("nature", "Thiên nhiên", "Gợi ý 5 địa điểm thiên nhiên nổi tiếng ở Đà Nẵng"),
            option("culture", "Văn hóa, lịch sử", "Gợi ý 5 địa điểm văn hóa lịch sử ở Đà Nẵng"),
        ]

    if intent in ("food", "cafe"):
        what = "quán ăn" if intent == "food" else "quán cà phê"
        return [
            option("nearby", "Gần tôi", f"Tìm {what} gần tôi"),
            option("more", "Gợi ý chỗ khác", f"Gợi ý thêm {what} khác ở Đà Nẵng"),
            option("plan", "Lên lịch trình", "Lập lịch trình du lịch Đà Nẵng"),
        ]

    if intent == "itinerary" and st.plan:
        options = [
            option("breakfast", "Thêm bữa sáng ngày 1", "Thêm bữa sáng vào ngày 1"),
            option("no-meals", "Chỉ tập trung tham quan", "Không xếp bữa ăn, chỉ tập trung tham quan"),
            option("son-tra", "Ưu tiên Sơn Trà", "Đổi lịch trình, tập trung Sơn Trà"),
            option("city-center", "Ưu tiên trung tâm", "Đổi lịch trình, tập trung trung tâm Đà Nẵng"),
            option("weather", "Xem thời tiết", "Thời tiết Đà Nẵng mấy ngày tới thế nào?"),
        ]
        if st.unscheduled_places:
            options.insert(
                0,
                option(
                    "add-day",
                    "Thêm ngày cho " + ", ".join(st.unscheduled_places),
                    f"Lịch trình {len(st.plan) + 1} ngày",
                ),
            )
        return options

    if intent in ("transport", "weather", "ask_detail"):
        return [
            option("plan", "Lên lịch trình", "Lập lịch trình du lịch Đà Nẵng"),
            option("famous", "Địa điểm nổi tiếng", "Gợi ý 5 địa điểm nổi tiếng ở Đà Nẵng"),
            option("bye", "Không, cảm ơn", "Không cần gì thêm, cảm ơn bạn"),
        ]

    if intent in ("greeting", "unclear"):
        return [
            option("ask-attractions", "Tìm địa điểm", "Gợi ý 5 địa điểm nổi tiếng ở Đà Nẵng"),
            option("ask-food", "Tìm món ăn", "Gợi ý món ăn đặc sản Đà Nẵng"),
            option("ask-cafe", "Quán cà phê", "Gợi ý quán cà phê đẹp ở Đà Nẵng"),
            option("ask-itinerary", "Lên lịch trình", "Lập lịch trình du lịch Đà Nẵng"),
        ]

    return []


def _result(st, steps, text, status, intent, closing=None):
    out = {
        "steps": list(steps),
        "text": text,
        "status": status,
        "suggestions": conversation_suggestions(intent, st),
        "closing": closing,
        "links": list(st.links),
    }
    if st.pending == "interests":
        out["suggestion_mode"] = "multi"
        out["multi_template"] = "Mình thích {items}"
    return out


# ---------- hàm chính ----------
def respond(st, msg, intent, conf, db, lat=None, lng=None, on_step=None):
    steps = StepList(on_step)
    steps.append("Đang phân tích yêu cầu của bạn...")
    st.links = []
    if lat is not None and lng is not None:
        st.pos = (float(lat), float(lng))
    lang = st.lang = nlg.detect_lang(msg, st.lang)
    slots, _ = extract_slots(msg)
    cue, words = strip_accents(msg), len(msg.split())
    if FLEX_RE.search(cue):
        slots["flexible"] = True

    # lời cảm ơn / tạm biệt
    if BYE_RE.search(cue) and words <= 8 and not slots:
        st.pending = st.pending_for = None
        st.route_dest = st.route_dest_name = None
        return _result(st, steps, nlg.say("farewell", lang), "completed", "bye")

    if st.pending == "origin" and intent not in {"itinerary", "weather", "greeting", "out_of_scope"}:
        intent = "transport"                         # đang chờ điểm xuất phát
    elif st.pending == "location" and st.pos and "vi tri" in cue:
        intent = st.pending_for                      # vừa chia sẻ vị trí
    elif st.pending_for and (
        intent == "clarify_reply"
        or (words <= 6 and slots)
        or (conf < 0.6 and intent not in {"greeting", "out_of_scope"})
    ):
        intent = st.pending_for                      # tin nhắn ngắn = trả lời câu hỏi vừa đặt
    elif intent == "clarify_reply":
        intent = "itinerary" if "days" in slots else ("attraction" if slots.get("interests") else "unclear")
    if st.plan and slots.get("zone"):
        intent = "itinerary"
    if st.plan and re.search(
        r"\b(khong xep bua an|chi tap trung tham quan|bo cac bua an)\b", cue
    ):
        st.slots["include_meals"] = False
        intent = "itinerary"
    elif st.plan and re.search(
        r"\b(doi lich trinh|uu tien khu vuc)\b", cue
    ):
        intent = "itinerary"
    if intent == "modify_itinerary" and not st.plan:
        intent = "itinerary"

    is_modify = bool(st.plan) and not (intent == "itinerary" and "days" in slots) and bool(
        intent == "modify_itinerary" or REMOVE_RE.search(cue) or ADD_RE.search(cue)
        or "early" in slots or "start_time" in slots)
    if not is_modify:
        merge_slots(st, slots)

    bits = []
    if slots.get("days"):
        bits.append(f"{slots['days']} ngày")
    if slots.get("interests"):
        bits.append("sở thích " + ", ".join(nlg.label(i, lang) for i in slots["interests"]))
    if slots.get("zone"):
        bits.append("khu vực " + pl.zone_label(slots["zone"]))
    if slots.get("places"):
        bits.append("địa điểm " + ", ".join(slots["places"]))
    if bits:
        steps.append("Đã hiểu: " + "; ".join(bits))

    matched_places = _match_places(
        db,
        msg,
        {"tourist_attraction"} if intent == "itinerary" else None,
    )
    if matched_places:
        slots["places"] = [short(matched[0].name) for matched in matched_places]
    else:
        slots.pop("places", None)
    if intent == "itinerary" or st.pending_for == "itinerary":
        for matched, _ in matched_places:
            if (
                matched.category == "tourist_attraction"
                and matched.id not in st.requested_place_ids
            ):
                st.requested_place_ids.append(matched.id)
    place = None
    if slots.get("places") or intent in {"ask_detail", "modify_itinerary"}:
        place = find_place(db, slots.get("places", []), msg)
        if place:
            steps.append(f"Nhận ra địa điểm trong dữ liệu: {place.name}")

    if conf < 0.40 and not slots and not st.plan and not st.pending_for:
        return _result(st, steps, nlg.say("ask_unclear", lang), "needs_clarification", "unclear")

    if is_modify:
        text = handle_modify(st, db, msg, slots, place, steps)
    elif intent == "greeting":
        text = nlg.say("greet", lang)
    elif intent == "out_of_scope":
        text = nlg.say("offscope", lang)
    elif intent == "itinerary":
        required_places = [
            found for place_id in st.requested_place_ids
            if (found := place_repo.get(db, place_id)) is not None
        ]
        text = handle_itinerary(st, db, place, steps, required_places)
    elif intent in CATEGORY_OF:
        text = handle_search(st, db, intent, msg, slots, place, steps)
    elif intent == "transport":
        text = handle_transport(st, db, msg, slots, steps)
    elif intent == "ask_detail":
        text = handle_detail(st, db, place)
    elif intent == "weather":
        steps.append("Đang truy cập dữ liệu thời tiết Open-Meteo...")
        text = planner_service.weather_text(*(st.pos or ()))
    else:
        text = nlg.say("ask_unclear", lang)

    status = "needs_clarification" if st.pending_for else "completed"
    closing = nlg.say("closing", lang) if status == "completed" and (is_modify or intent in CLOSING_INTENTS) else None
    return _result(st, steps, text, status, intent, closing)
