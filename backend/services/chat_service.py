import re
import unicodedata

from sqlalchemy.orm import Session

from backend.models.place import Place
from backend.services import planner_service as planner
from backend.services.intent_service import predict_intent as predict_trained_intent

MIN_CONFIDENCE = 0.35
SHOW_DISCLAIMER = False  # True = them cau "thong tin chi mang tinh tham khao"

# ------------------------------------------------------------------
# Model
# ------------------------------------------------------------------
def predict_intent(text: str):
    result = predict_trained_intent(text)
    return result["intent"], float(result["confidence"])


# ------------------------------------------------------------------
# Text helpers
# ------------------------------------------------------------------
def strip_accents(text: str) -> str:
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn").lower()


def is_vietnamese(text: str) -> bool:
    if strip_accents(text) != text.lower():
        return True
    return bool(re.search(r"\b(an gi|o dau|bao nhieu|di choi|quan|dia diem|thoi tiet|"
                          r"lich trinh|gan day|gan toi)\b", text.lower()))


# Xoa phan nguon: "Nguon: ...", "Nguồn tham khảo: ...", "Source: ..."
_SOURCE_RE = re.compile(
    r"\s*(?:Ngu\S?n(?:\s+tham\s+kh\S+)?|Source)\s*:.*$", re.IGNORECASE | re.DOTALL
)


def clean_text(text) -> str:
    return _SOURCE_RE.sub("", text or "").strip()


# ------------------------------------------------------------------
# Dinh tuyen theo tu khoa (uu tien hon model khi cau hoi ro rang)
# ------------------------------------------------------------------
ITINERARY_RE = re.compile(
    r"\b(lich trinh|ke hoach|len plan|plan|itinerary|hanh trinh|"
    r"di chuyen cua toi|tour)\b"
)
WEATHER_RE = re.compile(r"\b(thoi tiet|du bao|troi mua|weather|forecast)\b")
NEARBY_RE = re.compile(r"\b(gan day|gan toi|gan cho toi|near me|nearby)\b")
CAFE_RE = re.compile(r"\b(ca phe|cafe|coffee)\b")
FOOD_RE = re.compile(r"\b(an|quan an|nha hang|mon|do an|dac san|food|eat|restaurant)\b")


# ------------------------------------------------------------------
# Tim dia diem
# ------------------------------------------------------------------
INTENT_CATEGORY = {
    "food": "restaurant",
    "cafe": "cafe",
    "attraction": "tourist_attraction",
    "accommodation": "hotel",
}

# cum tu khoa (da bo dau) -> tu dung de loc theo ten/mo ta
KEYWORDS = {
    "bien": ["bien", "beach"],
    "beach": ["bien", "beach"],
    "thien nhien": ["thien nhien", "rung", "nui", "deo", "ban dao", "bien"],
    "nature": ["thien nhien", "rung", "nui", "deo", "ban dao"],
    "chua": ["chua", "pagoda"],
    "bao tang": ["bao tang", "museum"],
    "van hoa": ["pho co", "chua", "bao tang", "thanh dia", "nha tho", "di san"],
    "lich su": ["pho co", "chua", "bao tang", "thanh dia", "nha tho", "di san"],
    "cho": ["cho", "market"],
}

LOCATION_KEYWORDS = [
    (r"\bhoi an\b", ["hoi an"]),
    (r"\bmy son\b", ["my son"]),
]


def _requested_limit(folded: str, default: int = 5) -> int:
    m = re.search(
        r"\b(\d{1,2})\s*(?:dia diem|noi|quan|mon|cho|bai|place|spot|restaurant|cafe)", folded
    )
    if m:
        return min(max(int(m.group(1)), 1), 10)
    return default


def _search_places(db: Session, category: str, text: str, limit: int = 5):
    folded = strip_accents(text)
    places = (
        db.query(Place)
        .filter(Place.is_active == True, Place.category == category)  # noqa: E712
        .order_by(Place.id)
        .all()
    )

    def blob(p):
        return strip_accents(f"{p.name} {p.address or ''} {p.description or ''}")

    # Loc theo khu vuc (Hoi An, My Son)
    for pattern, kws in LOCATION_KEYWORDS:
        if re.search(pattern, folded):
            hit = [p for p in places if any(k in blob(p) for k in kws)]
            places = hit or places
            break

    # Loc theo chu de (bien, thien nhien, chua...)
    terms = []
    for key, vals in KEYWORDS.items():
        if re.search(rf"\b{key}\b", folded):
            terms += vals
    if terms:
        hit = [p for p in places if any(t in blob(p) for t in terms)]
        places = hit or places

    # Rating cao len truoc (neu co), giu thu tu cu khi bang nhau
    places.sort(key=lambda p: -(getattr(p, "rating", None) or 0))

    return places[:limit]


def _format_places(places, vi: bool) -> str:
    lab_addr, lab_hours = ("Địa chỉ", "Giờ mở cửa") if vi else ("Address", "Opening hours")
    blocks = []
    for i, p in enumerate(places, 1):
        rating = getattr(p, "rating", None)
        title = clean_text(p.name) + (f" ({rating}/5)" if rating else "")
        lines = [f"{i}. {title}"]
        if p.address:
            lines.append(f"   {lab_addr}: {clean_text(p.address)}")
        if p.opening_hours:
            lines.append(f"   {lab_hours}: {clean_text(p.opening_hours)}")
        if p.description:
            lines.append(f"   {clean_text(p.description)}")
        blocks.append("\n".join(lines))

    text = "\n\n".join(blocks)
    if SHOW_DISCLAIMER:
        text += ("\n\nThông tin chỉ mang tính tham khảo, bạn nên kiểm tra giờ mở cửa và giá vé."
                 if vi else "\n\nFor reference only; please check opening hours and prices.")
    return text


# ------------------------------------------------------------------
# Tra loi
# ------------------------------------------------------------------
def answer(message: str, db: Session, lat=None, lng=None) -> dict:
    vi = is_vietnamese(message)
    folded = strip_accents(message)
    has_gps = lat is not None and lng is not None

    # 1) Model nhan dien y dinh (neu model loi van tra loi duoc bang tu khoa)
    try:
        intent, conf = predict_intent(message)
    except Exception as exc:
        print(f"[Chat] Intent model unavailable: {type(exc).__name__}: {exc}")
        intent, conf = "unknown", 0.0

    # 2) Tu khoa ro rang thi uu tien hon model
    routed = False
    if ITINERARY_RE.search(folded):
        intent, routed = "itinerary", True
    elif WEATHER_RE.search(folded):
        intent, routed = "weather", True
    elif NEARBY_RE.search(folded):
        if CAFE_RE.search(folded):
            intent = "cafe"
        elif FOOD_RE.search(folded) or intent == "food":
            intent = "food"
        elif intent not in INTENT_CATEGORY:
            intent = "attraction"
        routed = True

    if not routed and conf < MIN_CONFIDENCE:
        reply = ("Mình chưa hiểu rõ câu hỏi. Bạn có thể hỏi về địa điểm, quán ăn, cà phê, "
                 "lịch trình hoặc thời tiết ở Đà Nẵng và Hội An nhé?" if vi else
                 "I'm not sure I understood. Ask me about places, food, cafes, itineraries "
                 "or weather in Da Nang and Hoi An.")
        return {"reply": reply, "intent": "unknown", "confidence": round(conf, 3)}

    # 3) Tra loi theo y dinh
    if intent == "out_of_scope":
        reply = ("Mình chỉ hỗ trợ thông tin du lịch Đà Nẵng và Hội An. "
                 "Bạn muốn tìm địa điểm, món ăn hay lịch trình?"
                 if vi else "I can only help with Da Nang and Hoi An travel. "
                            "Want places, food or an itinerary?")

    elif intent == "itinerary":
        reply = planner.build_itinerary(db, message, vi, lat, lng)

    elif intent == "weather":
        reply = planner.weather_text(lat, lng)

    elif intent in INTENT_CATEGORY:
        category = INTENT_CATEGORY[intent]

        if NEARBY_RE.search(folded):
            if has_gps:
                reply = planner.nearby(db, category, lat, lng, vi)
            else:
                reply = ("Mình chưa biết vị trí của bạn. Hãy cho phép trình duyệt truy cập "
                         "vị trí rồi hỏi lại nhé."
                         if vi else "I don't know your location yet. Please allow location "
                                    "access and ask again.")
        else:
            limit = _requested_limit(folded)
            places = _search_places(db, category, message, limit)
            if places:
                head = "Mình gợi ý cho bạn:\n\n" if vi else "Here are my suggestions:\n\n"
                reply = head + _format_places(places, vi)
            else:
                reply = ("Hiện chưa có dữ liệu cho mục này." if vi
                         else "No data for this category yet.")

    elif intent == "transport":
        reply = ("Ở Đà Nẵng bạn có thể dùng Grab/Be, taxi, xe máy thuê hoặc xe buýt. "
                 "Từ Đà Nẵng đến Hội An khoảng 30 km, đi taxi hoặc Grab mất khoảng 45 phút."
                 if vi else
                 "In Da Nang you can use Grab/Be, taxis, rented scooters or buses. "
                 "Hoi An is about 30 km from Da Nang, roughly 45 minutes by taxi or Grab.")

    else:
        reply = "Mình chưa hỗ trợ nội dung này." if vi else "I can't help with that yet."

    return {"reply": reply, "intent": intent, "confidence": round(conf, 3)}
