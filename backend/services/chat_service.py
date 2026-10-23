import glob
import os
import re
import unicodedata

import joblib
from sqlalchemy.orm import Session

from backend.models.place import Place

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(ROOT, "training", "models")  # sua neu thu muc khac
MIN_CONFIDENCE = 0.35
SHOW_DISCLAIMER = False  # True = them cau "thong tin chi mang tinh tham khao"

_model = None


# ------------------------------------------------------------------
# Model
# ------------------------------------------------------------------
def _load_model():
    global _model
    if _model is None:
        path = os.getenv("INTENT_MODEL_PATH")
        if not path:
            files = glob.glob(os.path.join(MODEL_DIR, "*.joblib"))
            if not files:
                raise RuntimeError(f"Không tìm thấy file .joblib trong {MODEL_DIR}")
            path = files[0]
        _model = joblib.load(path)
    return _model


def predict_intent(text: str):
    model = _load_model()
    encoder = None
    if isinstance(model, dict):
        encoder = model.get("label_encoder")
        model = model.get("model") or model.get("pipeline")
    label = model.predict([text])[0]
    if encoder is not None:
        label = encoder.inverse_transform([label])[0]
    conf = 1.0
    if hasattr(model, "predict_proba"):
        conf = float(max(model.predict_proba([text])[0]))
    return str(label), conf


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
    return bool(re.search(r"\b(an gi|o dau|bao nhieu|di choi|quan|dia diem|thoi tiet)\b",
                          text.lower()))


# Xoa phan "Nguon: ..." (ke ca ban bi loi font "Ngu?n: ...") khoi noi dung
_SOURCE_RE = re.compile(r"\s*(?:Ngu\S?n|Source)\s*:.*$", re.IGNORECASE | re.DOTALL)


def clean_text(text) -> str:
    return _SOURCE_RE.sub("", text or "").strip()


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

    return places[:limit]


def _format_places(places, vi: bool) -> str:
    lab_addr, lab_hours = ("Địa chỉ", "Giờ mở cửa") if vi else ("Address", "Opening hours")
    blocks = []
    for i, p in enumerate(places, 1):
        lines = [f"{i}. {p.name}"]
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


def _itinerary(db: Session, message: str, vi: bool) -> str:
    folded = strip_accents(message)
    in_hoi_an = bool(re.search(r"\bhoi an\b", folded))

    def pick(category, n):
        rows = (
            db.query(Place)
            .filter(Place.is_active == True, Place.category == category)  # noqa: E712
            .order_by(Place.id)
            .all()
        )
        is_ha = lambda p: "hoi an" in strip_accents(f"{p.name} {p.address or ''}")  # noqa: E731
        rows = [p for p in rows if is_ha(p) == in_hoi_an] or rows
        return rows[:n]

    attractions = pick("tourist_attraction", 4)
    food = pick("restaurant", 2)
    cafes = pick("cafe", 2)

    day1 = attractions[:2] + food[:1]
    day2 = attractions[2:4] + food[1:2] + cafes[:1]

    head = "Lịch trình gợi ý 2 ngày 1 đêm:" if vi else "Suggested 2-day itinerary:"
    d1 = "Ngày 1" if vi else "Day 1"
    d2 = "Ngày 2" if vi else "Day 2"
    return (f"{head}\n\n{d1}\n{_format_places(day1, vi)}"
            f"\n\n{d2}\n{_format_places(day2, vi)}")


# ------------------------------------------------------------------
# Tra loi
# ------------------------------------------------------------------
def answer(message: str, db: Session) -> dict:
    vi = is_vietnamese(message)
    intent, conf = predict_intent(message)

    if conf < MIN_CONFIDENCE:
        reply = ("Mình chưa hiểu rõ câu hỏi. Bạn có thể hỏi về địa điểm, quán ăn, cà phê, "
                 "lịch trình hoặc thời tiết ở Đà Nẵng và Hội An nhé?" if vi else
                 "I'm not sure I understood. Ask me about places, food, cafes, itineraries "
                 "or weather in Da Nang and Hoi An.")
        return {"reply": reply, "intent": "unknown", "confidence": conf}

    if intent == "out_of_scope":
        reply = ("Mình chỉ hỗ trợ thông tin du lịch Đà Nẵng và Hội An. "
                 "Bạn muốn tìm địa điểm, món ăn hay lịch trình?"
                 if vi else "I can only help with Da Nang and Hoi An travel. "
                            "Want places, food or an itinerary?")

    elif intent in INTENT_CATEGORY:
        limit = _requested_limit(strip_accents(message))
        places = _search_places(db, INTENT_CATEGORY[intent], message, limit)
        if places:
            head = "Mình gợi ý cho bạn:\n\n" if vi else "Here are my suggestions:\n\n"
            reply = head + _format_places(places, vi)
        else:
            reply = ("Hiện chưa có dữ liệu cho mục này." if vi
                     else "No data for this category yet.")

    elif intent == "itinerary":
        reply = _itinerary(db, message, vi)

    elif intent == "transport":
        reply = ("Ở Đà Nẵng bạn có thể dùng Grab/Be, taxi, xe máy thuê hoặc xe buýt. "
                 "Từ Đà Nẵng đến Hội An khoảng 30 km, đi taxi hoặc Grab mất khoảng 45 phút."
                 if vi else
                 "In Da Nang you can use Grab/Be, taxis, rented scooters or buses. "
                 "Hoi An is about 30 km from Da Nang, roughly 45 minutes by taxi or Grab.")

    elif intent == "weather":
        try:
            from backend.services.weather_service import get_weather_forecast
            if hasattr(get_weather_forecast, "invoke"):
                result = get_weather_forecast.invoke({"city": "Da Nang"})
            else:
                result = get_weather_forecast("Da Nang")
            reply = str(result)
        except Exception:
            reply = ("Mình chưa lấy được dự báo thời tiết lúc này." if vi
                     else "Couldn't fetch the weather right now.")
    else:
        reply = "Mình chưa hỗ trợ nội dung này." if vi else "I can't help with that yet."

    return {"reply": reply, "intent": intent, "confidence": round(conf, 3)}
