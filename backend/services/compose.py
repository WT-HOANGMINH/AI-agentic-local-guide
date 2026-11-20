"""Dựng câu trả lời có 'hồn': mở đầu theo ngữ cảnh, lịch trình theo buổi, lý do sắp xếp, mẹo, lời chúc,
các lựa chọn bấm chọn (suggestions) và liên kết Google Maps. Mọi con số lấy từ dữ liệu/planner, không bịa."""
import random
import re
import urllib.parse

from backend.services import planner as pl
from backend.services.slot_service import DISH_LABEL, strip_accents

WHO = {"couple": ("hai bạn", "the two of you"), "family": ("cả nhà", "your family"),
       "friends": ("cả nhóm", "your group"), "solo": ("bạn", "you")}
ZONE_TIPS = {  # mẹo chung (kiến thức phổ biến, không phải dữ liệu xác minh)
    "ba_na": ("Trên Bà Nà thường mát hơn dưới phố, bạn nên mang theo áo khoác mỏng và giày dễ đi bộ.",
              "It is usually cooler up on Ba Na, so bring a light jacket and comfortable shoes."),
    "son_tra_ban_dao": ("Đường lên bán đảo Sơn Trà nhiều dốc và khúc cua, hãy đi chậm, nhất là khi trời tối.",
                        "The Son Tra peninsula roads are steep and winding; ride slowly, especially after dark."),
    "hoi_an": ("Phố cổ Hội An thường đẹp nhất vào chiều tối khi đèn lồng được thắp lên.",
               "Hoi An's old town is often most beautiful in the evening when the lanterns are lit."),
    "cu_lao_cham": ("Tàu ra đảo phụ thuộc vào thời tiết, bạn nên kiểm tra lại lịch tàu trước khi đi.",
                    "Boats to the island depend on the weather; check the schedule before you go."),
}
PERIODS = [(11 * 60, "Buổi sáng", "Morning"), (14 * 60, "Buổi trưa", "Midday"),
           (17 * 60 + 30, "Buổi chiều", "Afternoon"), (24 * 60 + 1, "Buổi tối", "Evening")]


def pick(vi, en, lang):
    return random.choice(vi if lang == "vi" else en)


def who(lang, companion):
    vi, en = WHO.get(companion, ("bạn", "you"))
    return vi if lang == "vi" else en


def short(name):
    return re.sub(r"\s*\([^)]*\)", "", name or "").strip() or (name or "")


def join_list(items, lang):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + (" và " if lang == "vi" else " and ") + items[-1]


# ---------- tóm tắt những gì AI đã hiểu ----------
def wishes_summary(slots, place_labels, lang):
    parts = list(place_labels)
    dish = [DISH_LABEL.get(d, d) for d in slots.get("dish", [])]
    meal = slots.get("meal")
    when = {"breakfast": ("buổi sáng", "for breakfast"), "lunch": ("buổi trưa", "for lunch"),
            "dinner": ("buổi tối", "for dinner")}.get(meal)
    if dish:
        parts.append(("ăn " + join_list(dish, lang) + (" " + when[0] if when else "")) if lang == "vi"
                     else ("try " + join_list(dish, lang) + (" " + when[1] if when else "")))
    elif meal:
        parts.append(({"breakfast": "ăn sáng", "lunch": "ăn trưa", "dinner": "ăn tối"}[meal]) if lang == "vi"
                     else {"breakfast": "breakfast", "lunch": "lunch", "dinner": "dinner"}[meal])
    names = {"coffee": ("uống cà phê", "have coffee"), "rest": ("nghỉ trưa", "a midday rest")}
    for w in slots.get("wants", []):
        parts.append(names[w][0 if lang == "vi" else 1])
    return join_list(parts, lang)


# ---------- lịch trình ----------
def kind_label(stop, lang):
    k, h = stop["kind"], pl.to_min(stop["start"])
    if k == "meal":
        vi = "Ăn sáng" if h < 10 * 60 else ("Ăn trưa" if h < 15 * 60 else "Ăn tối")
        en = "Breakfast" if h < 10 * 60 else ("Lunch" if h < 15 * 60 else "Dinner")
    else:
        vi, en = {"visit": ("Tham quan", "Visit"), "cafe": ("Cà phê", "Coffee"),
                  "rest": ("Nghỉ ngơi", "Rest")}.get(k, ("", ""))
    return vi if lang == "vi" else en


def detail_line(p, stop, lang):
    if stop["kind"] == "rest":
        return ("Nghỉ ngơi lấy lại sức (khách sạn hoặc một quán cà phê điều hòa gần đó)." if lang == "vi"
                else "Time to recharge (your hotel or an air-conditioned cafe nearby).")
    if p is None:
        return ""
    bits = []
    desc = (p.description or "").strip()
    first = re.split(r"\.\s", desc)[0].rstrip(".")
    if first:
        bits.append(first[:110])
    ticket = re.search(r"Vé.{0,60}?(?:VNĐ|VND|[Mm]iễn phí)", desc)
    if ticket and ticket.group(0).strip() not in first:
        bits.append(ticket.group(0).strip())
    ot, ct = getattr(p, "open_time", None), getattr(p, "close_time", None)
    if ot and ct and not (ot == "00:00" and ct == "23:59"):
        bits.append(("Mở cửa " if lang == "vi" else "Open ") + f"{ot}–{ct}")
    return ". ".join(bits)


def render_plan(plan, only, by_id, lang):
    multi = len(plan) > 1
    lines = []
    for i, day in enumerate(plan):
        if only is not None and i not in only:
            continue
        if multi:
            lines.append(f"\n{'Ngày' if lang == 'vi' else 'Day'} {i + 1}")
        else:
            lines.append("")
        current = None
        entries = [
            (item["start"], 0, item) for item in day["stops"]
        ] + [
            (item["start"], 1, item) for item in day.get("breaks", [])
        ]
        for _, entry_type, item in sorted(entries, key=lambda entry: (entry[0], entry[1])):
            per = next(p for p in PERIODS if pl.to_min(item["start"]) < p[0])
            label = per[1] if lang == "vi" else per[2]
            if label != current:
                lines.append(f"\n{label}")
                current = label
            if entry_type:
                lines.append(f"• {item['start']}–{item['end']} | {item['name']}")
                continue
            s = item
            lines.append(f"• {s['start']}–{s['end']} | {kind_label(s, lang)}"
                         + (f": {short(s['name'])}" if s["kind"] != "rest" else ""))
            detail = detail_line(by_id.get(s["id"]), s, lang)
            if detail:
                lines.append(f"   {detail}")
            if s.get("travel", 0) >= 20:
                lines.append(("   (Di chuyển khoảng %d phút từ điểm trước, ước tính)" if lang == "vi"
                              else "   (About %d min travel from the previous stop, estimated)") % s["travel"])
        if day["dropped"]:
            lines.append("\n" + (("Chưa xếp vừa trong lịch: %s. Bạn có thể thêm một ngày nữa để đi các điểm này.")
                                 if lang == "vi" else ("Didn't fit in the plan: %s. You could add another day for them."))
                         % ", ".join(short(n) for n in day["dropped"]))
    return "\n".join(lines).strip("\n")


def why_lines(plan, only, by_id, lang):
    out = []
    for i, day in enumerate(plan):
        if only is not None and i not in only:
            continue
        for s in day["stops"]:
            p = by_id.get(s["id"])
            if p is not None and s["kind"] == "visit" and pl.is_long(p):
                ot, ct = getattr(p, "open_time", None), getattr(p, "close_time", None)
                hours = f" và mở cửa {ot}–{ct}" if ot and ct else ""
                out.append(f"{short(p.name)} cần khoảng {round(pl.duration(p) / 60, 1)} giờ{hours} nên mình xếp từ sáng."
                           if lang == "vi" else
                           f"{short(p.name)} needs about {round(pl.duration(p) / 60, 1)} hours"
                           f"{' and is open ' + ot + '-' + ct if ot and ct else ''}, so I put it early in the day.")
        if any(s["kind"] == "rest" for s in day["stops"]):
            out.append("Khối nghỉ ngơi được xếp ngay sau đoạn đi xa để bạn lấy lại sức." if lang == "vi"
                       else "The rest block comes right after the long outing so you can recover.")
    return " ".join(out)


def tips_for(plan, by_id, lang):
    zones = []
    for day in plan:
        for s in day["stops"]:
            p = by_id.get(s["id"])
            z = getattr(p, "zone", None) if p is not None else None
            if z in ZONE_TIPS and z not in zones:
                zones.append(z)
    tips = [ZONE_TIPS[z][0 if lang == "vi" else 1] for z in zones]
    tips.append("Bạn có thể thuê xe máy để chủ động, hoặc đặt taxi/xe công nghệ cho các đoạn đi xa."
                if lang == "vi" else "Rent a scooter for freedom, or book a taxi/ride-hailing for the longer legs.")
    return tips


def closing(companion, lang, kind="plan"):
    if kind == "bye":
        return pick(["Rất vui được giúp bạn! Chúc bạn có một chuyến đi thật vui vẻ, nếu cần chỉnh lịch trình cứ quay lại nhé.",
                    "Không có gì ạ! Chúc bạn đi chơi thật vui vẻ và có nhiều kỷ niệm đẹp ở Đà Nẵng nhé."],
                    ["Happy to help! Have a wonderful trip, and come back anytime to adjust the plan."], lang)
    if kind == "search":
        return pick(["Bạn cần mình giúp gì nữa không?", "Bạn cần mình hỗ trợ thêm điều gì nữa không?"],
                    ["Is there anything else I can help you with?"], lang)
    wish = {"couple": ("Chúc hai bạn có một ngày thật ngọt ngào và đáng nhớ!", "Wishing you both a sweet, memorable day!"),
            "family": ("Chúc cả nhà có một chuyến đi thật vui và an toàn!", "Wishing your family a fun and safe trip!"),
            "friends": ("Chúc cả nhóm có một chuyến đi thật vui!", "Have a great trip, everyone!"),
            "solo": ("Chúc bạn có một chuyến đi thật thoải mái và nhiều trải nghiệm đẹp!", "Wishing you a relaxing trip full of great experiences!")
            }.get(companion, ("Chúc bạn đi chơi một ngày thật vui vẻ!", "Have a great day out!"))
    ask = ("Bạn cần mình chỉnh giờ giấc hay giúp thêm điều gì nữa không?" if lang == "vi"
           else "Want me to adjust the timing or help with anything else?")
    return f"{wish[0 if lang == 'vi' else 1]} {ask}"


# ---------- liên kết Google Maps (chỉ là đường dẫn tìm kiếm, không gọi API) ----------
def maps_links(plan, by_id, lang, limit=8):
    links, seen = [], set()
    for day in plan:
        for s in day["stops"]:
            p = by_id.get(s["id"])
            if p is None or s["id"] in seen or s["kind"] == "rest":
                continue
            seen.add(s["id"])
            if p.latitude is not None and p.longitude is not None:
                q = f"{p.latitude},{p.longitude}"
            else:
                q = f"{short(p.name)} Đà Nẵng"
            links.append({"label": (f"Xem {short(p.name)} trên Google Maps" if lang == "vi"
                                    else f"{short(p.name)} on Google Maps"),
                          "url": "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q)})
            if len(links) >= limit:
                return links
    return links


def place_link(p, lang):
    return maps_links([{"stops": [{"id": p.id, "kind": "visit"}]}], {p.id: p}, lang)


def route_link(origin, destination, lang="vi"):
    params = urllib.parse.urlencode({
        "api": "1",
        "origin": origin,
        "destination": destination,
    }, safe=",")
    return [{
        "label": "Mở chỉ đường Google Maps" if lang == "vi" else "Open directions in Google Maps",
        "url": "https://www.google.com/maps/dir/?" + params,
    }]


# ---------- các lựa chọn bấm chọn ----------
def opt(label, text=None, slot=None, value=None, exclusive=False):
    message = text or label
    o = {"id": strip_accents(label).replace(" ", "_")[:40], "label": label,
         "text": message, "message": message}
    if slot:
        o["slot"], o["value"] = slot, value
    if exclusive:
        o["exclusive"] = True
    return o


def sug(options, mode="single", confirm=None):
    return {"mode": mode, "options": options, "confirm_label": confirm}


def sug_days(lang):
    vi = lang == "vi"
    options = [
        opt(f"{n} ngày" if vi else f"{n} day{'s' if n > 1 else ''}",
            f"{n} ngày" if vi else f"{n} days", "days", n)
        for n in (1, 2, 3, 4)
    ]
    day_names = {1: "one", 2: "two", 3: "three", 4: "four"}
    for option in options:
        option["id"] = f"{day_names[option['value']]}-day"
    return sug(options + [opt("Tùy bạn gợi ý" if vi else "You decide",
                              "tùy bạn", "flexible", True)])


def sug_interests(lang):
    vi = lang == "vi"
    items = [("Biển", "Beaches", "biển", "beach"), ("Thiên nhiên", "Nature", "thiên nhiên", "nature"),
             ("Văn hóa", "Culture", "văn hóa", "culture"), ("Ẩm thực", "Food", "ẩm thực", "food"),
             ("Hoàng hôn", "Sunset", "hoàng hôn", "sunset"), ("Chụp ảnh", "Photo spots", "chụp ảnh", "photo")]
    options = [opt(a if vi else b, text, "interests", val) for a, b, text, val in items]
    options.append(opt("Tùy bạn gợi ý" if vi else "You decide", "tùy bạn", "flexible", True, exclusive=True))
    return sug(options, "multi", "Gửi lựa chọn" if vi else "Send")


def sug_meal(lang):
    vi = lang == "vi"
    return sug([opt("Ăn sáng" if vi else "Breakfast", "ăn sáng" if vi else "breakfast", "meal", "breakfast"),
                opt("Ăn trưa" if vi else "Lunch", "ăn trưa" if vi else "lunch", "meal", "lunch"),
                opt("Ăn tối" if vi else "Dinner", "ăn tối" if vi else "dinner", "meal", "dinner")])


def sug_cafe(lang):
    vi = lang == "vi"
    return sug([opt("Làm việc, học bài" if vi else "Work or study", "quán cà phê yên tĩnh để làm việc"),
                opt("Hẹn hò, trò chuyện" if vi else "Date or chat", "quán cà phê không gian đẹp để trò chuyện"),
                opt("Ngắm view" if vi else "Nice view", "quán cà phê view đẹp")])


def sug_menu(lang):
    vi = lang == "vi"
    return sug([opt("Địa điểm nổi tiếng" if vi else "Famous places", "gợi ý địa điểm nổi tiếng ở Đà Nẵng"),
                opt("Ăn gì ở Đà Nẵng?" if vi else "What to eat?", "ăn gì"),
                opt("Lên lịch trình" if vi else "Plan an itinerary", "lên lịch trình"),
                opt("Quán cà phê đẹp" if vi else "Nice cafes", "cà phê")])


def sug_place(name, lang):
    vi = lang == "vi"
    return sug([opt("Giờ mở cửa & giá vé" if vi else "Hours & tickets", f"{name} mở cửa mấy giờ"),
                opt("Xếp vào lịch trình" if vi else "Add to an itinerary", f"lên lịch trình đi {name}"),
                opt("Ăn gì gần đó" if vi else "Food nearby", f"ăn gì gần {name}")])


def sug_after_search(first_name, lang):
    vi = lang == "vi"
    options = [
        opt("Địa điểm phổ biến" if vi else "Popular places",
            "gợi ý địa điểm nổi tiếng", value="popular"),
        opt("Đánh giá cao" if vi else "Highest rated",
            "địa điểm được đánh giá cao", value="highest-rated"),
        opt("Gần tôi" if vi else "Nearby",
            "__geo__", value="nearby"),
        opt("Xếp vào lịch trình" if vi else "Plan an itinerary", "lên lịch trình"),
    ]
    for option, identifier in zip(options[:3], ("popular", "highest-rated", "nearby")):
        option["id"] = identifier
    if first_name:
        options.append(opt(f"Chi tiết {short(first_name)}" if vi else f"Details: {short(first_name)}",
                           f"{short(first_name)} mở cửa mấy giờ"))
    options.append(opt("Cảm ơn, vậy là đủ" if vi else "Thanks, that's all", "cảm ơn"))
    return sug(options)


def sug_after_plan(plan, by_id, lang, assumed_days=False):
    vi = lang == "vi"
    options = []
    if assumed_days:
        options.append(opt("Chia thành 2 ngày" if vi else "Split into 2 days", "lên lịch trình 2 ngày", "days", 2))
    for day in plan:
        for s in day["stops"]:
            p = by_id.get(s["id"])
            if p is not None and s["kind"] == "visit" and pl.is_long(p):
                options.append(opt(f"Đi {short(p.name)} từ sớm" if vi else f"{short(p.name)} earlier",
                                   f"đi {short(p.name)} từ sớm"))
                break
        else:
            continue
        break
    if not any(s["kind"] == "meal" and pl.to_min(s["start"]) < 10 * 60 for d in plan for s in d["stops"]):
        options.append(opt("Thêm bữa sáng" if vi else "Add breakfast", "thêm bữa sáng ngày 1"))
    options.append(opt("Thêm quán cà phê" if vi else "Add a cafe", "thêm quán cà phê ngày 1"))
    options.append(opt("Bớt một điểm" if vi else "Remove a stop", "bớt một điểm"))
    last = next((s for d in reversed(plan) for s in reversed(d["stops"]) if s["kind"] == "visit"), None)
    if last:
        options.append(opt("Gợi ý quán ăn tối" if vi else "Dinner ideas",
                           f"ăn tối gần {short(last['name'])}"))
    options.append(opt("Cảm ơn, vậy là đủ" if vi else "Thanks, that's all", "cảm ơn"))
    return sug(options[:6])


def sug_remove(plan, lang):
    vi = lang == "vi"
    names = []
    for d in plan:
        for s in d["stops"]:
            if s["kind"] == "visit" and short(s["name"]) not in names:
                names.append(short(s["name"]))
    return sug([opt(f"Bỏ {n}" if vi else f"Remove {n}", f"bỏ {n} khỏi lịch trình") for n in names[:6]]) if names else None
