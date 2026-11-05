"""Bộ trích thông tin từ câu hỏi (số ngày, giờ, bữa ăn, sở thích, địa điểm, ngân sách, số người).

Phần nhận diện nhãn từng từ (BIO) do model tự huấn luyện: training/models/slot_tagger.joblib
(huấn luyện bằng training/src/train_slots.py). Các hàm _num/_time/_budget chỉ chuẩn hóa giá trị.
"""
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "training" / "models" / "slot_tagger.joblib"
TOKEN_RE = re.compile(r"[\w$:'-]+", re.UNICODE)


def strip_accents(s) -> str:
    s = unicodedata.normalize("NFD", str(s).replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def tokenize(text):
    return TOKEN_RE.findall(text)


def token_features(tokens, i):
    """Đặc trưng của một từ: bản thân từ, hậu tố, từ lân cận. Dùng chung cho huấn luyện và chạy thật."""
    w = strip_accents(tokens[i])
    f = {"bias": 1.0, "w": w, "p2": w[:2], "s2": w[-2:], "s3": w[-3:],
         "digit": float(w.isdigit()), "hasdigit": float(any(c.isdigit() for c in w)),
         "len": float(min(len(w), 8))}
    for off in (-2, -1, 1, 2):
        j = i + off
        f[f"w{off}"] = strip_accents(tokens[j]) if 0 <= j < len(tokens) else "<pad>"
    return f


@lru_cache(maxsize=1)
def _model():
    return joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None


def model_ready() -> bool:
    return _model() is not None


def tag(text):
    """Trả về danh sách (loại, cụm từ), ví dụ [("DAYS", "2 ngày"), ("INTEREST", "biển")]."""
    tokens, model = tokenize(text), _model()
    if not tokens or model is None:
        return []
    tags = model.predict([token_features(tokens, i) for i in range(len(tokens))])
    spans, cur = [], None
    for tok, t in zip(tokens, tags):
        if t == "O":
            if cur:
                spans.append(cur)
                cur = None
        elif t.startswith("B-") or cur is None or cur[0] != t[2:]:
            if cur:
                spans.append(cur)
            cur = [t[2:], [tok]]
        else:
            cur[1].append(tok)
    if cur:
        spans.append(cur)
    return [(k, " ".join(v)) for k, v in spans]


NUM = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5, "sau": 6, "bay": 7,
       "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}
INTEREST_MAP = {
    "beach": ["bien", "beach", "tam bien"],
    "nature": ["thien nhien", "nature", "nui", "rung", "hiking"],
    "culture": ["van hoa", "culture", "chua", "bao tang", "temple", "museum"],
    "food": ["am thuc", "food", "an uong", "dac san"],
    "sunset": ["hoang hon", "sunset", "binh minh", "sunrise"],
    "photo": ["chup anh", "check in", "check-in", "song ao", "photo"],
}
DISH_LABEL = {
    "mi quang": "mì Quảng",
    "bun cha ca": "bún chả cá",
    "banh mi": "bánh mì",
    "hai san": "hải sản",
    "banh xeo": "bánh xèo",
}
AREA_ALIASES = {
    "trung_tam": ("trung tam", "hai chau", "thanh khe", "cam le"),
    "son_tra": ("son tra", "my khe", "bien my khe"),
    "ngu_hanh_son": ("ngu hanh son", "non nuoc"),
    "ba_na": ("ba na", "ba na hills"),
    "hoi_an": ("hoi an", "pho co hoi an"),
    "hoa_vang": ("hoa vang", "hoa phu"),
}


def area_of(value):
    normalized = strip_accents(value)
    for area, aliases in AREA_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases):
            return area
    return None


def _num(text):
    for t in strip_accents(text).split():
        m = re.match(r"\d+", t)
        if m:
            return int(m.group())
        if t in NUM:
            return NUM[t]
    return None


def _time(text):
    t = strip_accents(text)
    if re.search(r"\b(som|early|earlier)\b", t):
        return {"early": True}
    m = re.search(r"(\d{1,2})(?:\s*(?:h|gio|:)\s*(\d{2})?)?\s*(am|pm)?", t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        if m.group(3) == "pm" and h < 12:
            h += 12
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return {"start_time": f"{h:02d}:{mi:02d}"}
    return {}


def _budget(text):
    t = strip_accents(text)
    if re.search(r"\b(re|cheap|tiet kiem|low)\b", t):
        return {"budget_level": "low"}
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu|tr|usd)?", t.replace("$", ""))
    if not m:
        return {}
    v = float(m.group(1).replace(",", "."))
    unit = m.group(2) or ("usd" if "$" in t else "")
    mult = {"k": 1e3, "nghin": 1e3, "ngan": 1e3, "trieu": 1e6, "tr": 1e6, "usd": 25000}.get(unit, 1e3 if v < 1000 else 1)
    return {"budget_vnd": int(v * mult)}


def extract_slots(text):
    """Trả về (slots, spans), gồm thời lượng, khung giờ, sở thích và các ràng buộc lịch."""
    slots, places, spans = {}, [], tag(text)
    normalized = strip_accents(text)
    day_count = re.search(
        r"\b(\d+|mot|hai|ba|bon|nam|sau|bay|one|two|three|four|five|six|seven)\s*(?:ngay|day)\b",
        normalized,
    )
    if day_count:
        count = _num(day_count.group(1))
        if count:
            slots["days"] = min(max(count, 1), 7)

    stop_count = re.search(
        r"\b(\d+|mot|hai|ba|bon|nam|sau|bay)\s*(?:cho|dia diem|places|stops)\b",
        normalized,
    )
    if stop_count:
        count = _num(stop_count.group(1))
        if count:
            slots["stops_per_day"] = min(max(count, 1), 12)

    if re.search(r"\b(?:buoi sang|morning only|before noon)\b", normalized) or re.search(
        r"\btruoc\s*(?:12|muoi hai)\s*(?:h|gio)?\s*(?:trua)?\b",
        normalized,
    ):
        slots["day_end"] = "12:00"

    matched_zones = [area for area, aliases in AREA_ALIASES.items()
                     if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases)]
    if len(matched_zones) == 1:
        slots["zone"] = matched_zones[0]

    for kind, val in spans:
        t = strip_accents(val)
        if kind == "DAYS":
            n = _num(val)
            if n:
                slots["days"] = min(n, 7)
        elif kind == "TIME":
            slots.update(_time(val))
        elif kind == "MEAL":
            slots["meal"] = ("breakfast" if re.search(r"sang|breakfast", t) else
                             "lunch" if re.search(r"trua|lunch", t) else "dinner")
        elif kind == "INTEREST":
            for k, ws in INTEREST_MAP.items():
                if any(w in t for w in ws) and k not in slots.setdefault("interests", []):
                    slots["interests"].append(k)
        elif kind == "BUDGET":
            slots.update(_budget(val))
        elif kind == "PEOPLE":
            has_person_unit = bool(
                re.search(r"\b(?:\d+\s*)?(?:nguoi|people|persons)\b", normalized)
            )
            if stop_count and not has_person_unit and _num(val) == _num(stop_count.group(1)):
                continue
            if re.search(r"mot minh|alone|solo", t):
                slots["people"] = 1
            else:
                n = _num(val)
                slots["people"] = n if n else 4
        elif kind == "PLACE":
            places.append(val)
    if places:
        slots["places"] = places

    if slots.get("day_end") and slots.get("start_time", "00:00") >= slots["day_end"]:
        slots.pop("start_time", None)

    meal_phrase = re.search(
        r"\b(an|bua|dung bua|breakfast|lunch|dinner)\b.{0,40}?"
        r"\b(sang|trua|toi|breakfast|lunch|dinner)\b",
        normalized,
    )
    slots.pop("meal", None)
    if meal_phrase:
        period = meal_phrase.group(2)
        slots["meal"] = {
            "sang": "breakfast",
            "breakfast": "breakfast",
            "trua": "lunch",
            "lunch": "lunch",
            "toi": "dinner",
            "dinner": "dinner",
        }[period]

    food_preferences = (
        ("mi quang", r"\bmi quang\b"),
        ("bun cha ca", r"\bbun cha ca\b"),
        ("banh mi", r"\bbanh mi\b"),
        ("hai san", r"\bhai san\b"),
        ("banh xeo", r"\bbahn? xeo\b"),
    )
    for query, pattern in food_preferences:
        if re.search(pattern, normalized):
            slots["food_query"] = query
            slots["dish"] = [query]
            break

    if re.search(r"\b(ca phe|cafe|coffee|cf)\b", normalized):
        slots["cafe_requested"] = True
        slots.setdefault("wants", []).append("coffee")
    if re.search(r"\b(nghi trua|nghi ngoi|ngu trua|nghi mot chut)\b", normalized):
        slots["midday_rest"] = True
        slots.setdefault("wants", []).append("rest")

    companions = (
        ("couple", r"\b(ban gai|ban trai|nguoi yeu|vo chong|hai dua)\b"),
        ("family", r"\b(gia dinh|ca nha|vo chong va con)\b"),
        ("friends", r"\b(nhom ban|hoi ban|ban be)\b"),
        ("solo", r"\b(mot minh|di mot minh|solo)\b"),
    )
    for companion, pattern in companions:
        if re.search(pattern, normalized):
            slots["companion"] = companion
            break
    return slots, spans
