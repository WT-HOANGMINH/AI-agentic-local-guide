"""Bộ điều phối hội thoại v2: hiểu (intent + slot) -> hỏi lại nếu thiếu -> chọn địa điểm / lập lịch / chỉnh lịch
-> diễn đạt có 'hồn' + gợi ý bấm chọn + liên kết bản đồ. Không dùng LLM/API bên ngoài."""
import math
import re
from dataclasses import dataclass, field

from backend.services import compose, nlg, place_repo
from backend.services import planner_service
from backend.services import planner as pl
from backend.services.ranker import INTEREST_QUERY, MEAL_QUERY, get_ranker
from backend.services.slot_service import AREA_ALIASES, area_of, extract_slots, strip_accents

CATEGORY_OF = {"food": {"restaurant"}, "cafe": {"cafe"}, "attraction": {"tourist_attraction"},
               "accommodation": {"hotel", "homestay", "accommodation", "resort"}}
REMOVE_ACC = re.compile(r"\b(bỏ|bớt|xóa|xoá|loại|remove|drop|delete)\b")
REMOVE_ASCII = re.compile(r"\b(bo|bot|xoa|loai|remove|drop|delete)\b")
ADD_ACC = re.compile(r"\b(thêm|add|include)\b")
ADD_ASCII = re.compile(r"\b(them|add|include)\b")
WALK_RE = re.compile(r"(khong|it|han che|tranh|duoi|toi da).{0,25}di bo|di bo.{0,25}(duoi|khong qua|it thoi|\d+\s*(m|met|km)\b)")
DAY_RE = re.compile(r"\b(?:ngay|day)\s*(\d)\b")
FLEX_RE = re.compile(r"(tuy ban|gi cung duoc|bat ky|up to you|you decide|anything)")
THANKS_RE = re.compile(r"\b(cam on|thanks|thank you|tam biet|bye|het roi|vay la du|du roi|khong can nua)\b")
PERSIST = {
    "days", "interests", "budget_vnd", "budget_level", "people",
    "start_time", "early", "flexible", "companion", "limit_walk",
    "meal", "dish", "wants", "wish_places", "places", "zone",
    "food_query", "include_meals", "midday_rest", "cafe_requested",
    "day_end", "stops_per_day",
}
MEAL_WINDOW = {"breakfast": ("08:00", "09:00"), "lunch": ("11:30", "13:00"), "dinner": ("18:30", "20:00")}
FRIENDLY = {"itinerary": "lập lịch trình", "food": "tìm quán ăn", "cafe": "tìm quán cà phê",
            "attraction": "tìm địa điểm tham quan", "accommodation": "tìm chỗ ở", "transport": "hỏi đường đi",
            "weather": "hỏi thời tiết", "modify_itinerary": "chỉnh lịch trình", "clarify_reply": "trả lời câu hỏi của mình",
            "greeting": "chào hỏi", "ask_detail": "hỏi chi tiết địa điểm", "out_of_scope": "hỏi ngoài phạm vi"}
CHOICE_OK = {
    "days": lambda v: type(v) is int and 1 <= v <= 7,
    "interests": lambda v: v in INTEREST_QUERY,
    "meal": lambda v: v in {"breakfast", "lunch", "dinner"},
    "companion": lambda v: v in {"couple", "family", "friends", "solo"},
    "flexible": lambda v: v is True,
}


@dataclass
class State:
    slots: dict = field(default_factory=dict)
    pending: str | None = None
    pending_for: str | None = None
    asked: set = field(default_factory=set)
    plan: list = field(default_factory=list)
    lang: str = "vi"
    pos: tuple[float, float] | None = None
    history: list[dict[str, str]] = field(default_factory=list)
    route_dest: object | None = None
    requested_place_ids: set = field(default_factory=set)
    starting_new_itinerary: bool = False


def wants_remove(msg):
    """'bỏ/bớt/xóa' - phân biệt với 'bộ' trong 'đi bộ': chỉ dùng bản không dấu khi cả câu gõ không dấu."""
    m = msg.lower()
    return bool(REMOVE_ACC.search(m) or (m.isascii() and REMOVE_ASCII.search(m)))


def wants_add(msg):
    m = msg.lower()
    return bool(ADD_ACC.search(m) or (m.isascii() and ADD_ASCII.search(m)))


def reply(text, steps, suggestions=None, links=None, closing=None):
    meta = suggestions if isinstance(suggestions, dict) else {}
    options = meta.get("options", []) if meta else (suggestions or [])
    for option in options:
        if isinstance(option, dict) and "message" not in option:
            option["message"] = option.get("text", option.get("label", ""))
    return {
        "text": text,
        "steps": steps,
        "suggestions": options,
        "suggestion_mode": meta.get("mode", "single"),
        "multi_template": meta.get("multi_template"),
        "confirm_label": meta.get("confirm_label"),
        "links": links or [],
        "closing": closing,
    }


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


def dish_match(p, dishes):
    text = strip_accents(f"{p.name} {p.description or ''}")
    return any(d in text for d in dishes)


def find_place(db, names, message):
    """Khớp tên người dùng nêu với địa điểm trong dữ liệu. Chặt để không nhận nhầm một mảnh tên:
    - cả tên địa điểm xuất hiện trong câu, hoặc
    - cụm người dùng nêu (từ 2 từ trở lên) nằm trọn, đúng ranh giới từ, trong tên địa điểm."""
    msg = " " + strip_accents(message) + " "
    cands = [c for c in (strip_accents(n).strip() for n in names) if len(c) > 2]
    best, best_len = None, 0
    for p in place_repo.all_active(db):
        pn = strip_accents(p.name).strip()
        hits = []
        if " " + pn + " " in msg:
            hits.append(len(pn))
        for c in cands:
            if " " + pn + " " in " " + c + " ":
                hits.append(len(pn))
            elif len(c.split()) >= 2 and " " + c + " " in " " + pn + " ":
                hits.append(len(c))
        if hits and max(hits) > best_len:
            best, best_len = p, max(hits)
    return best


def phrase_around(msg, fragment):
    """Để báo 'không tìm thấy', lấy cả cụm tên viết hoa chứa mảnh được nhận diện (vd 'Rồng Vàng Hạ Long')."""
    for m in re.finditer(r"(?:[A-ZÀ-Ỹ][^\s,.;:!?]*\s?)+", msg):
        if fragment.lower() in m.group(0).lower():
            return m.group(0).strip()
    return fragment


def apply_choice(slots, choice):
    """Lựa chọn bấm chọn từ giao diện: kiểm tra chặt rồi ghi thẳng vào slot (không phụ thuộc NLU)."""
    if not isinstance(choice, dict):
        return
    slot, values = choice.get("slot"), choice.get("values")
    if slot not in CHOICE_OK or not isinstance(values, list):
        return
    ok = [v for v in values if CHOICE_OK[slot](v)]
    if not ok:
        return
    if slot == "interests":
        slots["interests"] = list(dict.fromkeys(ok))
    else:
        slots[slot] = ok[0]


def merge_slots(st, slots):
    for k, v in slots.items():
        if k == "interests":
            cur = st.slots.setdefault("interests", [])
            cur.extend(i for i in v if i not in cur)
        elif k in PERSIST:
            st.slots[k] = v


def by_id_of(db, plan):
    ids = {s["id"] for d in plan for s in d["stops"] if s["id"] is not None}
    return {p.id: p for p in place_repo.by_ids(db, ids)}


def describe_slots(slots):
    parts = []
    if slots.get("places"):
        parts.append("địa điểm: " + ", ".join(slots["places"]))
    if slots.get("dish"):
        parts.append("món: " + ", ".join(compose.DISH_LABEL.get(d, d) for d in slots["dish"]))
    if slots.get("limit_walk"):
        parts.append("hạn chế đi bộ")
    for key, label in (("meal", "bữa"), ("days", "số ngày"), ("start_time", "giờ bắt đầu"),
                       ("companion", "đi cùng"), ("budget_vnd", "ngân sách")):
        if key in slots:
            parts.append(f"{label}: {slots[key]}")
    if slots.get("wants"):
        parts.append("mong muốn: " + ", ".join({"coffee": "cà phê", "rest": "nghỉ trưa"}[w] for w in slots["wants"]))
    if slots.get("interests"):
        parts.append("sở thích: " + ", ".join(nlg.label(i, "vi") for i in slots["interests"]))
    if slots.get("early"):
        parts.append("muốn đi sớm")
    return "; ".join(parts)


# ---------- giải thích thời gian di chuyển ----------
def explain(plan, lang, only=None):
    out = []
    for i, d in enumerate(plan):
        if only is not None and i != only:
            continue
        if d["saved"] >= 10:
            out.append(nlg.say("explain_saved", lang, d=i + 1, t=d["travel_min"], s=d["saved"]))
        elif d["travel_min"] == 0:
            pass
        elif d["zones"] and len(d["zones"]) <= 2:
            out.append(nlg.say("explain_near", lang, d=i + 1, t=d["travel_min"], zones=", ".join(d["zones"])))
        else:
            out.append(nlg.say("explain_near2", lang, d=i + 1, t=d["travel_min"]))
    return " ".join(out)


def brief(p):
    desc = (p.description or "").strip().split(". ")[0][:110]
    bits = [desc] if desc else []
    if p.opening_hours and "kiem tra" not in strip_accents(p.opening_hours):
        bits.append(p.opening_hours)
    return " – ".join(bits)


# ---------- tìm kiếm ----------
def handle_search(st, db, intent, msg, slots, place, steps):
    lang, meal = st.lang, slots.get("meal")
    cue = strip_accents(msg)
    if re.search(r"\b(gan toi|gan day|near me|nearby)\b", cue):
        if st.pos is None:
            st.pending = st.pending_for = intent
            option = compose.opt(
                "Dùng vị trí của tôi" if lang == "vi" else "Use my location",
                "__geo__",
            )
            steps.append("Chưa có vị trí được chia sẻ → chưa thể xác định địa điểm gần bạn")
            return reply(
                "Mình chưa được cấp vị trí nên chưa thể xếp địa điểm theo khoảng cách. "
                "Bạn có thể chia sẻ vị trí hoặc nêu khu vực muốn tìm."
                if lang == "vi" else
                "I don't have your location, so I can't rank nearby places yet. "
                "Share it or tell me which area to search.",
                steps,
                compose.sug([option]),
            )

        rk = get_ranker(db)
        lat, lng = st.pos
        nearby = [
            p for p in rk.places
            if p.latitude is not None and p.longitude is not None
            and p.category in CATEGORY_OF[intent]
        ]
        nearby.sort(key=lambda p: (
            (p.latitude - lat) ** 2 + (p.longitude - lng) ** 2
        ))
        nearby = nearby[:5]
        steps.append(f"Đang tìm trong dữ liệu địa điểm ({len(rk.places)} địa điểm)")
        if not nearby:
            return reply(nlg.say("no_result", lang), steps, compose.sug_menu(lang))
        lines = [
            f"{i}. {p.name} – khoảng cách đường chim bay "
            f"{math.hypot((p.latitude - lat) * 111, (p.longitude - lng) * 105):.1f} km"
            for i, p in enumerate(nearby, 1)
        ]
        return reply(
            "Các địa điểm gần vị trí bạn chia sẻ (khoảng cách đường chim bay, không phải tuyến đường):\n\n"
            + "\n".join(lines),
            steps,
            compose.sug_after_search(nearby[0].name, lang),
            compose.maps_links(
                [{"stops": [{"id": p.id, "kind": "visit"}]} for p in nearby],
                {p.id: p for p in nearby},
                lang,
            ),
        )

    if len(msg.split()) <= 3 and not slots and intent not in st.asked:
        st.asked.add(intent)
        st.pending = st.pending_for = intent
        steps.append("Câu hỏi còn thiếu thông tin → mình sẽ hỏi lại bạn")
        builder = {"food": compose.sug_meal, "cafe": compose.sug_cafe, "attraction": compose.sug_interests}.get(intent)
        return reply(nlg.say(f"ask_{intent}", lang), steps, builder(lang) if builder else None)
    st.pending = st.pending_for = None
    st.asked.discard(intent)
    rk = get_ranker(db)
    steps.append(f"Đang truy cập cơ sở dữ liệu địa điểm ({len(rk.places)} địa điểm)")
    interests = slots.get("interests", [])
    famous = intent == "attraction" and not interests and not place
    query = " ".join([msg] + [INTEREST_QUERY[i] for i in interests] + [MEAL_QUERY.get(meal, "")]
                     + slots.get("dish", []) + (["noi tieng bieu tuong"] if famous else []))
    results = rk.rank(query, k=12, categories=CATEGORY_OF[intent], anchor=place)
    steps.append("Đang xếp hạng theo mức độ phù hợp" + (f" và khoảng cách tới {compose.short(place.name)}" if place else ""))
    if meal:
        results = [p for p in results if fits_meal(p, meal)]
        steps.append(f"Đang lọc quán mở cửa phù hợp bữa {meal}: còn {len(results)} quán")
    results = results[:5 if intent == "attraction" else 4]
    if not results:
        return reply(nlg.say("no_result", lang), steps, compose.sug_menu(lang))
    lines = [nlg.search_intro(lang, compose.short(place.name) if place else "", meal)]
    lines += [f"{i}. {p.name}" + (f" – {brief(p)}" if brief(p) else "") for i, p in enumerate(results, 1)]
    if famous:
        lines.append("\n(Mình chọn theo mức độ nổi bật trong dữ liệu hiện có; đây không phải bảng xếp hạng chính thức.)")
    links = []
    for p in results[:4]:
        links += compose.place_link(p, lang)
    steps.append("Đang tạo liên kết Google Maps cho các địa điểm")
    text = "\n".join(lines) + "\n\n" + nlg.say("search_followup", lang) + " " + compose.closing(None, lang, "search")
    return reply(text, steps, compose.sug_after_search(results[0].name, lang), links)


# ---------- lập lịch ----------
def resolve_must(db, rk, names, scores):
    """Tên/khu vực người dùng nêu -> danh sách địa điểm cụ thể trong dữ liệu."""
    must, seen = [], set()
    for raw in names:
        zone, pick = area_of(raw), []
        if zone:
            cands = [p for p in rk.places if is_attraction(p) and getattr(p, "zone", None) == zone]
            if not cands:
                p = find_place(db, [raw], raw)
                cands = [p] if p else []
            longs = [p for p in cands if pl.is_long(p)]
            if longs:
                pick = [max(longs, key=lambda p: scores.get(p.id, 0))]
            else:
                budget = 0
                for p in sorted(cands, key=lambda p: -scores.get(p.id, 0)):
                    if len(pick) < 2 and budget + pl.duration(p) <= 150:
                        pick.append(p)
                        budget += pl.duration(p)
        else:
            p = find_place(db, [raw], raw)
            pick = [p] if p else []
        for p in pick:
            if p.id not in seen:
                must.append(p)
                seen.add(p.id)
    return must


def make_day_kwargs(rk, foods, dish, meal, wants, must_ids, day_end=None):
    dish_foods = [p for p in foods if dish and dish_match(p, dish)]

    def kw(group, used):
        out = {"must_ids": set(must_ids)}
        if day_end is not None:
            out["day_end"] = day_end
        full_day_attraction = any(pl.is_long(place) for place in group)
        near = None
        if meal == "breakfast" and not full_day_attraction:
            cands = rk.rank(" ".join(dish + [MEAL_QUERY["breakfast"]]), k=20, categories={"restaurant"}, exclude=used)
            cands = [p for p in cands if fits_meal(p, "breakfast")]
            if dish:
                cands = [p for p in cands if dish_match(p, dish)] or cands
            if cands:
                out["breakfast"], near = cands[0], cands[0]
                out["day_start"] = "07:00"
        elif dish and dish_foods:
            out["foods"] = dish_foods                       # bữa trưa/tối ưu tiên đúng món người dùng muốn
        if "coffee" in wants and not full_day_attraction:
            cs = rk.rank("ca phe", k=10, categories={"cafe"}, anchor=near, exclude=used)
            early = [p for p in cs if (getattr(p, "open_time", None) or "00:00") <= "08:30"] or cs
            if early:
                out["coffee"] = early[0]
        if "rest" in wants:
            out["rest_min"] = 90
        return out
    return kw


def _zone_fragment(value, zone):
    normalized = strip_accents(value).strip()
    return any(
        normalized in alias.split()
        for alias in AREA_ALIASES.get(zone, ())
    )


def itinerary_data(st, msg, by_id):
    activities = []
    for day_number, day in enumerate(st.plan, 1):
        stops = list(day["stops"])
        for item in day.get("breaks", []):
            stops.append({
                **item,
                "id": None,
                "kind": "break",
            })
        day_items = []
        for order, stop in enumerate(sorted(stops, key=lambda x: pl.to_min(x["start"])), 1):
            place = by_id.get(stop.get("id"))
            day_items.append({
                "order": order,
                "kind": stop.get("kind", "activity"),
                "place_id": getattr(place, "id", None),
                "title": stop.get("name") or getattr(place, "name", "Hoạt động tự do"),
                "start_time": stop.get("start"),
                "end_time": stop.get("end"),
                "description": getattr(place, "description", None),
                "address": getattr(place, "address", None),
                "estimated_cost_vnd": None,
                "transport_minutes_from_previous": stop.get("travel"),
            })
        activities.append({
            "day_number": day_number,
            "estimated_travel_minutes": day.get("travel_min"),
            "items": day_items,
        })

    preferences = {
        key: st.slots[key]
        for key in ("interests", "wants", "dish", "companion", "limit_walk", "zone")
        if key in st.slots
    }
    original_request = "\n".join(
        [item["content"] for item in st.history if item.get("role") == "user"] + [msg]
    )
    return {
        "title": f"Lịch trình Đà Nẵng {len(st.plan)} ngày",
        "description": "Lịch trình được tạo từ cuộc trò chuyện DaNang Guide.",
        "original_request": original_request,
        "travel_date": st.slots.get("travel_date"),
        "duration_days": len(st.plan),
        "travelers": st.slots.get("people"),
        "budget": {
            "amount": st.slots.get("budget_vnd"),
            "currency": "VND",
            "level": st.slots.get("budget_level"),
        },
        "preferences": preferences,
        "days": activities,
        "verified_data_only": True,
    }


def handle_itinerary(st, db, place, steps, msg):
    lang, s, assumed = st.lang, st.slots, False
    wish_places, dish = s.get("wish_places", []), s.get("dish", [])
    wants, meal = s.get("wants", []), s.get("wish_meal")
    if wish_places:
        ranker = get_ranker(db)
        preliminary_scores = ranker.score_map(" ".join(wish_places))
        st.requested_place_ids = {
            item.id for item in resolve_must(db, ranker, wish_places, preliminary_scores)
        }
    rich = (
        len(wish_places) + len(dish) + len(wants) + (1 if meal else 0) >= 1
        or bool(s.get("day_end") or s.get("stops_per_day"))
    )

    if "days" not in s:
        if "days" in st.asked:
            st.pending, st.pending_for = "days", "itinerary"
            steps.append("Bạn đã nêu thêm yêu cầu → mình vẫn cần biết số ngày")
            return reply(nlg.say("ask_days", lang), steps, compose.sug_days(lang))
        if rich:
            s["days"], assumed = 1, True
        else:
            st.asked.add("days")
            st.pending, st.pending_for = "days", "itinerary"
            steps.append("Thiếu số ngày → mình sẽ hỏi lại bạn")
            return reply(nlg.say("ask_days", lang), steps, compose.sug_days(lang))
    if not rich and not s.get("interests") and not s.get("flexible") and "interests" not in st.asked:
        st.asked.add("interests")
        st.pending, st.pending_for = "interests", "itinerary"
        steps.append("Chưa rõ sở thích → mình sẽ hỏi lại bạn")
        return reply(nlg.say("ask_interest", lang), steps, compose.sug_interests(lang))

    st.pending = st.pending_for = None
    rk = get_ranker(db)
    steps.append(f"Đang truy cập cơ sở dữ liệu địa điểm ({len(rk.places)} địa điểm)")
    interests = s.get("interests", [])
    scores = rk.score_map(" ".join(INTEREST_QUERY[i] for i in interests) or "noi tieng pho bien")
    attrs = [p for p in rk.places if is_attraction(p)]
    must = resolve_must(db, rk, wish_places, scores)
    st.requested_place_ids = {p.id for p in must}
    if must:
        steps.append("Đã khớp địa điểm bạn nêu: " + ", ".join(compose.short(p.name) for p in must))
    for p in must:
        scores[p.id] = 2.0
    low = s.get("budget_level") == "low" or (s.get("budget_vnd") or 10 ** 9) <= 500_000
    foods = [p for p in rk.places if p.category == "restaurant" and (not low or (p.price_level or 2) <= 2)]
    cafes = [p for p in rk.places if p.category == "cafe"]
    n_days = min(int(s["days"]), 7)
    start = s.get("start_time") or ("06:30" if s.get("early") else None)
    steps.append("Đang ước tính thời gian di chuyển giữa các khu vực")
    steps.append("Đang tìm kiếm địa điểm phù hợp với yêu cầu")
    per_day = int(s.get("stops_per_day", 4))
    groups = (
        [must] if (must and n_days == 1)
        else pl.split_days(attrs, scores, n_days, per_day=per_day)
    )
    steps.append("Đang xếp lịch theo giờ mở cửa, thời lượng tham quan và bữa ăn")
    kwfn = make_day_kwargs(
        rk, foods, dish, meal, wants, [p.id for p in must], day_end=s.get("day_end")
    )
    st.plan = pl.plan_groups([g for g in groups if g], foods, cafes, start, kwfn)
    if not st.plan:
        return reply(nlg.say("no_result", lang), steps, compose.sug_menu(lang))
    for k in ("days", "start_time", "early"):
        s.pop(k, None)
    st.asked -= {"days", "interests"}
    st.starting_new_itinerary = False

    by_id = by_id_of(db, st.plan)
    companion = s.get("companion")
    who = compose.who(lang, companion)
    scope = ("một ngày" if lang == "vi" else "a day") if len(st.plan) == 1 else (
        f"{len(st.plan)} ngày" if lang == "vi" else f"{len(st.plan)} days")
    summary = compose.wishes_summary({"dish": dish, "meal": meal, "wants": wants}, [w.title() for w in wish_places], lang)
    if summary:
        intro = (f"Mình đã sắp xếp {scope} thật trọn vẹn cho {who} rồi nhé! Mình hiểu {who} muốn: {summary}."
                 if lang == "vi" else f"I've put together {scope} for {who}! Here's what I understood: {summary}.")
    else:
        topic = ""
        if interests:
            labs = ", ".join(nlg.label(i, lang) for i in interests)
            topic = f" (ưu tiên: {labs})" if lang == "vi" else f" (focus: {labs})"
        intro = nlg.say("plan_intro", lang, n=len(st.plan), topic=topic)
    parts = [intro]
    if assumed:
        parts.append("Bạn chưa nói số ngày nên mình tạm xếp trong 1 ngày; nếu muốn chia ra nhiều ngày, bạn chọn bên dưới nhé."
                     if lang == "vi" else "You didn't say how many days, so I assumed 1; pick another length below to split it up.")
    elif not interests and not rich:
        parts.append(nlg.say("plan_popular", lang))
    if s.get("limit_walk"):
        parts.append("Mình ghi nhận bạn muốn hạn chế đi bộ nên ưu tiên các điểm gần nhau và di chuyển bằng xe; "
                     "tuy nhiên dữ liệu hiện chưa có khoảng cách đi bộ trong từng điểm nên mình chưa kiểm chứng được "
                     "quãng đi bộ cụ thể." if lang == "vi" else
                     "I noted you want to limit walking, so I favored nearby stops and travel by vehicle; I can't verify "
                     "the walking distance inside each site with the current data.")
    parts.append(compose.render_plan(st.plan, None, by_id, lang))
    notes = " ".join(x for x in (compose.why_lines(st.plan, None, by_id, lang), explain(st.plan, lang)) if x)
    if notes:
        parts += ["", notes]
    tips = compose.tips_for(st.plan, by_id, lang)
    parts += ["", ("Mẹo nhỏ:" if lang == "vi" else "Quick tips:")] + [f"• {t}" for t in tips]
    parts += ["", compose.closing(companion, lang)]
    steps.append("Đang tạo liên kết Google Maps cho các điểm dừng")
    result = reply(
        "\n".join(parts),
        steps,
        compose.sug_after_plan(st.plan, by_id, lang, assumed),
        compose.maps_links(st.plan, by_id, lang),
    )
    result["itinerary"] = itinerary_data(st, msg, by_id)
    return result


def replan_day(db, st, idx, pinned_id=None, start=None, remove_id=None, add_ids=(), breakfast=None, coffee=None,
               rest_min=None):
    day = st.plan[idx]
    opts = dict(day.get("opts") or {})
    ids = [i for i in day["attr_ids"] if i != remove_id] + [i for i in add_ids if i not in day["attr_ids"]]
    by_id = {p.id: p for p in place_repo.by_ids(db, ids)}
    attrs = [by_id[i] for i in ids if i in by_id]
    foods = place_repo.restaurants(db)
    avoid = {s["id"] for j, d in enumerate(st.plan) if j != idx for s in d["stops"] if s["kind"] == "meal"}
    if breakfast is None and opts.get("breakfast_id"):
        breakfast = place_repo.get(db, opts["breakfast_id"])
    if coffee is None and opts.get("coffee_id"):
        coffee = place_repo.get(db, opts["coffee_id"])
    if breakfast is not None:
        opts["breakfast_id"] = breakfast.id
    if coffee is not None:
        opts["coffee_id"] = coffee.id
    if rest_min is not None:
        opts["rest_min"] = rest_min
    pinned = by_id.get(pinned_id)
    must_ids = set(opts.get("must_ids") or [])
    long_in = next((p for p in attrs if pl.is_long(p)), None)
    displaced = []
    if long_in is not None and len(attrs) > 1:      # điểm cả ngày chiếm trọn ngày, trừ các điểm người dùng yêu cầu rõ
        displaced = [p for p in attrs if p.id != long_in.id and p.id not in must_ids]
        attrs = [p for p in attrs if p not in displaced]
        pinned = pinned or long_in
    if start is None and pinned and pl.is_long(pinned) and pl.to_min(day["start"]) >= 7 * 60 + 30 and not breakfast:
        start = "07:00"
    res = pl.build_day(attrs, foods, None, start or day["start"], pinned=pinned, breakfast=breakfast, avoid=avoid,
                       coffee=coffee, rest_min=opts.get("rest_min", 0))
    gone = set(res["dropped_ids"]) | {p.id for p in displaced}
    res["attr_ids"] = [i for i in ids if i not in gone]
    res["dropped_ids"] = res["dropped_ids"] + [p.id for p in displaced]
    res["dropped"] = res["dropped"] + [p.name for p in displaced]
    res["opts"] = opts
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
                continue
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
    steps.append(f"Đang truy cập lịch trình hiện tại ({len(st.plan)} ngày) để chỉnh")

    if wants_remove(msg):
        if not place:
            return reply(nlg.say("modify_which", lang), steps, compose.sug_remove(st.plan, lang))
        idx = _day_of(st, place.id)
        if idx is None:
            return reply(nlg.say("not_in_plan", lang, name=compose.short(place.name)), steps)
        replan_day(db, st, idx, remove_id=place.id)
        head = nlg.say("modify_removed", lang, name=compose.short(place.name), d=idx + 1)
    elif wants_add(msg) and slots.get("meal") == "breakfast":
        pick = rk.rank(MEAL_QUERY["breakfast"], k=12, categories={"restaurant"}, anchor=anchor, exclude=avoid)
        pick = [p for p in pick if fits_meal(p, "breakfast")]
        if not pick:
            return reply(nlg.say("no_result", lang), steps)
        replan_day(db, st, idx, breakfast=pick[0])
        head = nlg.say("modify_added", lang, name=compose.short(pick[0].name), d=idx + 1)
    elif wants_add(msg) and wants_cafe and not place:
        pick = rk.rank("ca phe view dep", k=1, categories={"cafe"}, anchor=anchor, exclude=avoid)
        if not pick:
            return reply(nlg.say("no_result", lang), steps)
        replan_day(db, st, idx, coffee=pick[0])
        head = nlg.say("modify_added", lang, name=compose.short(pick[0].name), d=idx + 1)
    elif wants_add(msg) and place:
        have = _day_of(st, place.id)
        if have is not None:
            return reply(nlg.say("already_in_plan", lang, name=compose.short(place.name), d=have + 1), steps)
        if not m:
            def gap(i):
                ids = st.plan[i]["attr_ids"]
                return pl.travel_min(place_repo.get(db, ids[0]) if ids else None, place)
            idx = min(range(len(st.plan)), key=gap)
        replan_day(db, st, idx, add_ids=[place.id])
        head = nlg.say("modify_added", lang, name=compose.short(place.name), d=idx + 1)
    else:
        new_start = slots.get("start_time") or ("06:30" if slots.get("early") else None)
        if not place and not new_start:
            return reply(nlg.say("modify_which_time", lang), steps)
        extra = [place.id] if place and _day_of(st, place.id) is None else []
        res = replan_day(db, st, idx, pinned_id=place.id if place else None, start=new_start, add_ids=extra)
        pin = (f" ({compose.short(place.name)} đi đầu tiên)" if lang == "vi" else f" ({compose.short(place.name)} first)") if place else ""
        head = nlg.say("modify_time", lang, d=idx + 1, pin=pin, start=res["start"])
        first = res["stops"][0] if res["stops"] else None
        if place and first and first["id"] == place.id and getattr(place, "open_time", None) == first["start"]:
            head += " " + nlg.say("earliest", lang, name=compose.short(place.name), t=first["start"])
    steps.append(f"Đang xếp lại ngày {idx + 1} với ràng buộc mới")

    moved = relocate_dropped(db, st, idx)
    changed = [idx] + sorted({d - 1 for _, d in moved})
    by_id = by_id_of(db, st.plan)
    notes = " ".join(x for x in (compose.why_lines(st.plan, [idx], by_id, lang),
                                 explain(st.plan, lang, idx)) if x)
    parts = [head, compose.render_plan(st.plan, changed, by_id, lang)]
    if notes:
        parts += ["", notes]
    parts += [nlg.say("moved", lang, name=compose.short(n), d=d) for n, d in moved]
    parts += ["", "Bạn cần mình chỉnh gì nữa không?" if lang == "vi" else "Anything else you'd like to change?"]
    steps.append("Đang tạo liên kết Google Maps cho các điểm dừng")
    result = reply(
        "\n".join(parts),
        steps,
        compose.sug_after_plan(st.plan, by_id, lang),
        compose.maps_links([st.plan[i] for i in changed], by_id, lang),
    )
    result["itinerary"] = itinerary_data(st, msg, by_id)
    return result


def handle_transport(st, db, msg, slots, place, steps):
    lang = st.lang
    cue = strip_accents(msg)
    match = re.search(
        r"\b(?:từ|tu|from)\s+(.+?)\s+\b(?:đến|den|to)\s+(.+?)(?:\s+(?:đường|duong|thế nào|the nao|bao xa).*)?$",
        msg,
        re.IGNORECASE,
    )
    origin_text = match.group(1).strip() if match else None
    destination_text = match.group(2).strip() if match else None
    destination = find_place(db, slots.get("places", []), msg) or find_place(db, [], msg) or place
    origin = find_place(db, [origin_text], origin_text or "") if origin_text else None

    if destination is None and st.route_dest is not None:
        destination = place_repo.get(db, st.route_dest)
    if destination is None:
        st.pending = st.pending_for = "transport"
        return reply(nlg.say("ask_transport", lang), steps)

    dest_name = compose.short(destination.name)
    dest_query = (
        f"{destination.latitude},{destination.longitude}"
        if pl.has_coords(destination) else f"{dest_name}, Đà Nẵng"
    )

    if st.pos is not None:
        lat, lng = st.pos
        if pl.has_coords(destination):
            km = math.hypot((destination.latitude - lat) * 111, (destination.longitude - lng) * 105)
            minutes = round(km * 1.4 / 30 * 60) + 5
            text = nlg.say("route_gps", lang, b=dest_name, k=round(km, 1), t=minutes)
            text += " " + nlg.say("route_note", lang)
            origin_query = f"{lat},{lng}"
        else:
            text = nlg.say("route_text_origin", lang, a="vị trí của bạn", b=dest_name)
            origin_query = f"{lat},{lng}"
        st.pending = st.pending_for = None
        st.route_dest = None
        steps.append(f"Đang ước tính quãng đường tới {dest_name} từ tọa độ đã chia sẻ")
        return reply(
            text,
            steps,
            links=compose.route_link(origin_query, dest_query, lang),
            closing=compose.closing(None, lang, "search"),
        )

    if origin_text:
        origin_label = origin_text
        if origin is not None:
            origin_label = compose.short(origin.name)
            origin_query = (
                f"{origin.latitude},{origin.longitude}"
                if pl.has_coords(origin) else origin_label + ", Đà Nẵng"
            )
            if pl.has_coords(origin) and pl.has_coords(destination):
                km = pl.km(origin, destination)
                minutes = pl.travel_min(origin, destination)
                text = nlg.say(
                    "route", lang, a=origin_label, b=dest_name,
                    k=round(km, 1), t=minutes,
                ) + " " + nlg.say("route_note", lang)
            else:
                text = nlg.say("route_text_origin", lang, a=origin_label, b=dest_name)
        else:
            origin_query = origin_text
            text = nlg.say("route_text_origin", lang, a=origin_label, b=dest_name)
        st.pending = st.pending_for = None
        st.route_dest = None
        steps.append(f"Đang tạo chỉ đường từ {origin_label} đến {dest_name}")
        return reply(
            text,
            steps,
            links=compose.route_link(origin_query, dest_query, lang),
            closing=compose.closing(None, lang, "search"),
        )

    st.route_dest = destination.id
    st.pending = st.pending_for = "transport"
    label = "Dùng vị trí của tôi" if lang == "vi" else "Use my location"
    option = compose.opt(label, "__geo__")
    text = nlg.say("ask_origin", lang, name=dest_name)
    steps.append(f"Đã tìm thấy điểm đến {dest_name}; đang chờ điểm xuất phát")
    return reply(
        text,
        steps,
        compose.sug([option]),
        compose.route_link("Đà Nẵng", dest_query, lang),
    )


def handle_weather(st, steps):
    steps.append("Đang truy cập dự báo thời tiết từ Open-Meteo")
    lat, lng = st.pos if st.pos is not None else (None, None)
    text = planner_service.weather_text(lat, lng)
    return reply(text, steps)


def handle_detail(st, db, place, steps):
    if not place:
        st.pending = st.pending_for = "ask_detail"
        return reply(nlg.say("ask_which_place", st.lang), steps)
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
    ticket_info = getattr(place, "ticket_info", None)
    ticket_source_url = getattr(place, "ticket_source_url", None)
    if ticket_info:
        lines.append(f"{'Thông tin vé' if vi else 'Ticket information'}: {ticket_info}")
        if ticket_source_url:
            lines.append(f"{'Nguồn' if vi else 'Source'}: {ticket_source_url}")
    prices = getattr(place, "prices", None) or []
    if prices:
        lines.append("Giá đã xác minh:" if vi else "Verified prices:")
        for price in prices:
            price_range = (
                f"{price.price_min_vnd:,} VND"
                if price.price_min_vnd == price.price_max_vnd
                else f"{price.price_min_vnd:,}–{price.price_max_vnd:,} VND"
            )
            source_note = (
                f"nguồn: {price.source_url}; xác minh ngày {price.verified_at}"
                if vi else
                f"source: {price.source_url}; verified {price.verified_at}"
            )
            lines.append(
                f"- {price.item_name}: {price_range} / {price.unit} ({source_note})"
            )
    else:
        lines.append(
            "Chưa có giá cụ thể kèm nguồn xác minh trong dữ liệu."
            if vi else "No specific source-verified price is available in the data."
        )
    if place.address:
        lines.append(f"{'Địa chỉ' if vi else 'Address'}: {place.address}")
    lines.append("Thông tin có thể thay đổi, bạn nên kiểm tra lại trước khi đi." if vi
                 else "Details may change; please double-check before you go.")
    lines.append(compose.closing(None, st.lang, "search"))
    steps.append(f"Đang truy cập thông tin chi tiết của {compose.short(place.name)}")
    return reply("\n".join(lines), steps, compose.sug_place(compose.short(place.name), st.lang),
                 compose.place_link(place, st.lang))


# ---------- hàm chính ----------
def respond(st, msg, intent, conf, db, choice=None, lat=None, lng=None, on_step=None):
    """Điểm vào chính. Trả về {text, steps, suggestions, links}."""
    if lat is not None and lng is not None:
        st.pos = (lat, lng)
    missing = []
    res = _respond(st, msg, intent, conf, db, choice, missing)
    if missing and res:
        names = ", ".join(f"“{m}”" for m in missing)
        note = (f"Mình chưa tìm thấy {names} trong dữ liệu địa điểm hiện có nên chưa thể đưa vào hoặc cung cấp "
                f"thông tin về nơi này (mình không muốn đoán bừa).\n\n" if st.lang == "vi" else
                f"I couldn't find {names} in my place data, so I can't include it or share details (I don't want to guess).\n\n")
        res["text"] = note + res["text"]
    res["status"] = "needs_clarification" if st.pending_for else "completed"
    if on_step is not None:
        for step in res.get("steps", []):
            on_step(step)
    return res


def _respond(st, msg, intent, conf, db, choice, missing_box):
    lang = st.lang = nlg.detect_lang(msg, st.lang)
    slots, _ = extract_slots(msg)
    apply_choice(slots, choice)
    if st.pending_for == "transport" and re.search(
        r"\b(?:từ|tu|from)\s+.+?\s+(?:đến|den|to)\s+.+",
        msg,
        re.IGNORECASE,
    ):
        intent = "transport"
    if st.pending_for == "itinerary" and any(
        key in slots for key in ("places", "dish", "wants", "days", "interests", "companion", "budget_vnd")
    ):
        intent = "itinerary"
    if "days" in slots and intent in CATEGORY_OF and any(
        key in slots for key in ("dish", "wants", "places", "interests")
    ):
        intent = "itinerary"
    if intent == "itinerary" and st.plan and not slots:
        st.slots.clear()
        st.starting_new_itinerary = True
    raw_places = slots.get("places", [])
    if raw_places:                                   # chỉ giữ tên khớp được với dữ liệu; còn lại báo thẳng là không tìm thấy
        zone_fragments = {
            sp for sp in raw_places
            if slots.get("zone") and _zone_fragment(sp, slots["zone"])
        }
        known = [
            sp for sp in raw_places
            if area_of(sp)
            or find_place(db, [sp], sp)
        ]
        missing_box[:] = list(dict.fromkeys(
            phrase_around(msg, sp)
            for sp in raw_places
            if sp not in known and sp not in zone_fragments
        ))
        if known:
            slots["places"] = known
        else:
            slots.pop("places")
    cue, words = strip_accents(msg), len(msg.split())
    if FLEX_RE.search(cue):
        slots["flexible"] = True
    if WALK_RE.search(cue):
        slots["limit_walk"] = True
    steps = [f"Đang phân tích câu hỏi → bạn muốn {FRIENDLY.get(intent, 'được hỗ trợ')} (độ tin cậy {conf:.0%})"]
    info = describe_slots(slots)
    if info:
        steps.append("Đã nhận diện yêu cầu: " + info)
    if missing_box:
        steps.append("Không tìm thấy trong dữ liệu địa điểm: " + ", ".join(missing_box))

    if THANKS_RE.search(cue) and not slots and words <= 8:
        st.pending = st.pending_for = None
        return reply(compose.closing(st.slots.get("companion"), lang, "bye"), steps)

    explicit_intents = {
        "accommodation", "ask_detail", "attraction", "cafe", "food",
        "itinerary", "transport", "weather",
    }
    if st.pending_for == "clarify_reply" and intent in explicit_intents:
        st.pending = st.pending_for = None
    elif st.pending_for and (
        intent == "clarify_reply"
        or (words <= 6 and slots)
        or st.pending_for == "itinerary" and any(
            key in slots for key in ("places", "dish", "wants", "days", "interests", "companion", "budget_vnd")
        )
    ):
        intent = st.pending_for                      # tin nhắn ngắn / lựa chọn bấm = trả lời câu hỏi vừa đặt
    elif intent == "clarify_reply":
        intent = "itinerary" if "days" in slots else ("attraction" if slots.get("interests") else "unclear")
    if intent == "modify_itinerary" and not st.plan:
        intent = "itinerary"

    is_modify = bool(st.plan) and not (intent == "itinerary" and "days" in slots) and bool(
        intent == "modify_itinerary" or wants_remove(msg) or wants_add(msg)
        or "early" in slots or "start_time" in slots)
    if not is_modify:
        merge_slots(st, slots)
        if intent == "itinerary" and (slots.get("places") or slots.get("dish") or slots.get("wants")):
            # Explicitly replace list-like wishes; do not accumulate stale constraints.
            st.slots["wish_places"] = list(slots.get("places", []))
            st.slots["dish"] = list(slots.get("dish", []))
            st.slots["wants"] = list(slots.get("wants", []))
            if "meal" in slots:
                st.slots["wish_meal"] = slots["meal"]

    place = None
    if slots.get("places") or intent in {"ask_detail", "modify_itinerary"}:
        place = find_place(db, slots.get("places", []), msg)
        if place:
            steps.append(f"Đã nhận ra địa điểm trong dữ liệu: {compose.short(place.name)}")

    if conf < 0.40 and not slots and not st.plan and not st.pending_for:
        st.pending = st.pending_for = "clarify_reply"
        return reply(nlg.say("ask_unclear", lang), steps, compose.sug_menu(lang))

    # chỉ nhắc tên một địa điểm / khu vực: hỏi lại xem người dùng cần gì
    only_place = (bool(slots.get("places")) and not (set(slots) - {"places"}) and words <= 4
                  and not st.pending_for and intent not in {"ask_detail", "transport", "modify_itinerary", "itinerary"})
    if only_place and not is_modify:
        label = compose.short(place.name) if place else slots["places"][0].title()
        steps.append("Bạn chỉ nhắc tên địa điểm → mình sẽ hỏi bạn muốn biết điều gì")
        text = (f"Bạn muốn mình giúp gì về {label}? Mình có thể cho bạn biết giờ mở cửa và giá vé, "
                f"xếp vào lịch trình hoặc gợi ý chỗ ăn gần đó." if lang == "vi" else
                f"What would you like to know about {label}? I can share hours and tickets, add it to an itinerary, "
                f"or suggest food nearby.")
        return reply(text, steps, compose.sug_place(label, lang), compose.place_link(place, lang) if place else None)

    if is_modify:
        return handle_modify(st, db, msg, slots, place, steps)
    if intent == "greeting":
        return reply(nlg.say("greet", lang), steps, compose.sug_menu(lang))
    if intent == "out_of_scope":
        return reply(nlg.say("offscope", lang), steps, compose.sug_menu(lang))
    if intent == "itinerary":
        return handle_itinerary(st, db, place, steps, msg)
    if intent in CATEGORY_OF:
        return handle_search(st, db, intent, msg, slots, place, steps)
    if intent == "transport":
        return handle_transport(st, db, msg, slots, place, steps)
    if intent == "ask_detail":
        return handle_detail(st, db, place, steps)
    if intent == "weather":
        return handle_weather(st, steps)
    return reply(nlg.say("ask_unclear", lang), steps, compose.sug_menu(lang))
