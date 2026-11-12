"""
Hook trả lời câu hỏi thời tiết trong chat (không cần LLM).

- Chỉ chạy khi người dùng hỏi về thời tiết (hoặc intent == "weather").
- Số liệu lấy từ weather_service (Open-Meteo), KHÔNG bịa.
- Địa điểm gợi ý lấy từ bảng places; không có dữ liệu thì không gợi ý.
- Trả về dict cùng dạng dialogue.respond(): text, steps, suggestions, links, status.
  Có cờ _skip_llm để _apply_llm KHÔNG viết lại làm sai số liệu.
"""
from __future__ import annotations

import random
import re
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from backend.services.weather_analyzer import analyze_date, recommend_transport
from backend.services.weather_service import get_weather_forecast

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
FORECAST_DAYS = 7

WEEKDAYS = ["thứ Hai", "thứ Ba", "thứ Tư", "thứ Năm", "thứ Sáu", "thứ Bảy", "Chủ nhật"]
CAT_LABEL = {"restaurant": "ăn uống", "cafe": "cà phê",
             "shopping": "mua sắm", "tourist_attraction": "tham quan"}

# Cụm từ (không dấu) cho biết người dùng đang hỏi về thời tiết.
_WEATHER_PHRASES = re.compile(
    r"\b(thoi tiet|du bao|co mua|troi mua|mua khong|mua ko|mua to|mua lon|"
    r"neu mua|nhe mua|troi nang|nang khong|nang ko|nhiet do|bao khong|"
    r"mang o|ao mua|troi co mua)\b"
)


def _strip(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def looks_like_weather(message: str) -> bool:
    return bool(_WEATHER_PHRASES.search(_strip(message or "")))


# ---------------------------------------------------------------- ngày
def parse_target_date(message: str, today: date, remembered: date | None = None):
    """Trả về (ngày, có_nêu_rõ_trong_câu)."""
    low = (message or "").lower()
    s = _strip(message or "")

    m = re.search(r"\b(\d{1,2})/(\d{1,2})\b(?!\s*ngay)", s)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        try:
            cand = date(today.year, mo, d)
            if cand < today:
                cand = date(today.year + 1, mo, d)
            return cand, True
        except ValueError:
            pass

    m = re.search(r"\bngay\s+(\d{1,2})\s+thang\s+(\d{1,2})\b", s)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        try:
            cand = date(today.year, mo, d)
            if cand < today:
                cand = date(today.year + 1, mo, d)
            return cand, True
        except ValueError:
            pass

    if re.search(r"\b(mốt|ngày kia)\b", low) or re.search(r"\bngay kia\b", s):
        return today + timedelta(days=2), True
    if re.search(r"\b(hom nay|bay gio|hien tai|toi nay|chieu nay|sang nay|trua nay)\b", s):
        return today, True
    if re.search(r"\bngay mai\b", s) or (
        re.search(r"\bmai\b", s) and not re.search(r"\bmai hac de\b", s)
    ):
        return today + timedelta(days=1), True
    if re.search(r"\b(cuoi tuan|weekend|thu bay|t7)\b", s):
        return today + timedelta(days=(5 - today.weekday()) % 7), True
    if re.search(r"\b(chu nhat|cn)\b", s):
        return today + timedelta(days=(6 - today.weekday()) % 7), True

    if remembered:
        return remembered, False
    return today, False


def _label(d: date, today: date) -> str:
    diff = (d - today).days
    base = {0: "hôm nay", 1: "ngày mai", 2: "ngày mốt"}.get(diff)
    tail = f"{WEEKDAYS[d.weekday()]}, {d.strftime('%d/%m')}"
    return f"{base} ({tail})" if base else tail


# ------------------------------------------------------ địa điểm (từ DB)
def _load_candidates(db, want: str) -> list[tuple[str, str]]:
    """
    want: 'indoor' | 'outdoor'. Trả về [(tên, category)] từ bảng places.
    Dùng cột weather_profile nếu đã có dữ liệu, không thì suy ra từ category.
    """
    from backend.models.place import Place

    base = db.query(Place.name, Place.category).filter(Place.is_active.is_(True))
    col = getattr(Place, "weather_profile", None)
    rows = []
    if col is not None:
        try:
            rows = base.filter(col == want).limit(80).all()
        except Exception:
            db.rollback()  # cột chưa tồn tại trong DB: dùng fallback
    if not rows:
        cats = ("cafe", "restaurant", "shopping") if want == "indoor" else ("tourist_attraction",)
        rows = base.filter(Place.category.in_(cats)).limit(80).all()
    return [(r[0], r[1]) for r in rows]


def _pick_places(db, want: str, per_cat: int = 1, max_total: int = 4) -> list[str]:
    try:
        cands = _load_candidates(db, want)
    except Exception:
        return []
    by_cat: dict[str, list[str]] = {}
    for name, cat in cands:
        by_cat.setdefault(cat, []).append(name)
    out = []
    for cat, names in by_cat.items():
        for name in random.sample(names, min(per_cat, len(names))):
            out.append(f"{name} ({CAT_LABEL.get(cat, cat)})")
    random.shuffle(out)
    return out[:max_total]


# ------------------------------------------------------------- soạn câu
_INTRO = {
    0: ["Tin vui nè!", "Trời có vẻ hợp đi chơi đó!", "Dự báo nhìn khá ổn!"],
    1: ["Có chút lắt nhắt, nhưng chưa đến mức phải ở nhà.", "Trời hơi khó đoán một chút nhé."],
    2: ["Ngày này trời không đẹp lắm đâu.", "Hơi ướt át đây, mình chuẩn bị trước cho chắc nhé."],
    3: ["Khoan đã, dự báo có dông hoặc gió rất mạnh."],
}


def summary_lines(analysis: dict) -> list[str]:
    """Render the observed forecast fields used by itinerary weather notes."""
    lines = []
    if analysis.get("rain_prob_max") is not None:
        lines.append(
            f"- Xác suất mưa cao nhất: {analysis['rain_prob_max']:.0f}%."
        )
    else:
        lines.append("- Nguồn dự báo không cung cấp xác suất mưa.")
    if analysis.get("rain_sum_mm") is not None:
        lines.append(f"- Tổng lượng mưa: {analysis['rain_sum_mm']:.1f} mm.")
    if analysis.get("temp_min") is not None and analysis.get("temp_max") is not None:
        lines.append(
            f"- Nhiệt độ: {analysis['temp_min']:.0f}–{analysis['temp_max']:.0f}°C."
        )
    if analysis.get("feels_like_min") is not None and analysis.get("feels_like_max") is not None:
        lines.append(
            f"- Nhiệt độ cảm nhận: {analysis['feels_like_min']:.0f}–"
            f"{analysis['feels_like_max']:.0f}°C."
        )
    if analysis.get("wind_max_kmh") is not None:
        gust = analysis.get("gust_max_kmh")
        gust_text = f", gió giật tối đa {gust:.0f} km/h" if gust is not None else ""
        lines.append(f"- Tốc độ gió tối đa: {analysis['wind_max_kmh']:.0f} km/h{gust_text}.")
    for period, values in analysis.get("periods", {}).items():
        lines.append(f"- Buổi {period}: {values['label']}.")
    return lines


def weather_metadata(forecast: dict, target: date, analysis: dict | None = None) -> dict:
    dates = [row["date"] for row in forecast.get("daily", []) if row.get("date")]
    return {
        "date": target.isoformat(),
        "source": forecast.get("source", "Open-Meteo"),
        "reference_url": "https://open-meteo.com/en/docs",
        "fetched_at": (analysis or {}).get("fetched_at") or forecast.get("fetched_at"),
        "cache_status": (
            "stale" if forecast.get("is_stale")
            else "cached" if forecast.get("from_cache")
            else "fresh"
        ),
        "location": forecast.get("location", "Da Nang, Vietnam"),
        "valid_from": min(dates) if dates else None,
        "valid_until": max(dates) if dates else None,
        "is_stale": bool(forecast.get("is_stale")),
    }


def _fail_text(reason: str, weather: dict | None = None) -> dict:
    response = {
        "text": reason, "steps": [], "suggestions": [], "links": [],
        "status": "ok", "_skip_llm": True, "places": [],
    }
    if weather is not None:
        response["weather"] = weather
    return response


def build_weather_reply(forecast: dict, target: date, today: date, db=None) -> dict:
    iso = target.isoformat()
    a = analyze_date(forecast, iso)
    if not a.get("available"):
        last = forecast["daily"][-1]["date"] if forecast.get("daily") else "?"
        return _fail_text(
            f"Mình chỉ có dự báo từ hôm nay đến {last}, nên chưa tra được {_label(target, today)}. "
            "Bạn thử hỏi ngày gần hơn nhé, mình không muốn đoán bừa.",
            weather_metadata(forecast, target, a),
        )

    risk = a["max_risk"]
    lines = [f"{random.choice(_INTRO[risk])} Dự báo {_label(target, today)} ở Đà Nẵng:"]

    if a["is_stale"]:
        lines.append(
            f"⚠ Mình không kết nối được nguồn dự báo, đây là dữ liệu cũ (lưu cách đây "
            f"{forecast.get('stale_minutes', '?')} phút), không phải dự báo mới nhất."
        )

    # --- số liệu thật
    if a["rain_prob_max"] is not None:
        lines.append(
            f"- Xác suất có mưa cao nhất trong ngày: {a['rain_prob_max']:.0f}%. "
            "Đây là khả năng có mưa xảy ra trong khung giờ đó, không phải mưa suốt "
            f"{a['rain_prob_max']:.0f}% thời gian."
        )
    else:
        lines.append("- Nguồn dự báo không cung cấp xác suất mưa cho ngày này.")
    if a["rain_sum_mm"] is not None:
        lines.append(f"- Tổng lượng mưa dự báo: {a['rain_sum_mm']:.1f} mm.")
    if a["temp_min"] is not None and a["temp_max"] is not None:
        lines.append(f"- Nhiệt độ: {a['temp_min']:.0f}–{a['temp_max']:.0f}°C.")
    if a.get("feels_like_min") is not None and a.get("feels_like_max") is not None:
        lines.append(
            f"- Nhiệt độ cảm nhận trong ngày: {a['feels_like_min']:.0f}–"
            f"{a['feels_like_max']:.0f}°C."
        )
    if a.get("wind_max_kmh") is not None:
        gust = a.get("gust_max_kmh")
        gust_text = f", gió giật tối đa {gust:.0f} km/h" if gust is not None else ""
        lines.append(f"- Tốc độ gió tối đa: {a['wind_max_kmh']:.0f} km/h{gust_text}.")
    if target == today:
        target_hours = [
            hour for hour in forecast.get("hours", [])
            if hour.get("time", "").startswith(iso)
        ]
        parsed_hours = []
        for hour in target_hours:
            try:
                parsed_hours.append((
                    abs(datetime.fromisoformat(hour["time"]).replace(tzinfo=TZ) - datetime.now(TZ)),
                    hour,
                ))
            except (KeyError, TypeError, ValueError):
                continue
        if parsed_hours:
            nearest = min(parsed_hours, key=lambda pair: pair[0])[1]
            current_bits = []
            if nearest.get("temp_c") is not None:
                current_bits.append(f"nhiệt độ {nearest['temp_c']:.0f}°C")
            if nearest.get("feels_like_c") is not None:
                current_bits.append(
                    f"cảm nhận {nearest['feels_like_c']:.0f}°C"
                )
            if nearest.get("rain_prob") is not None:
                current_bits.append(
                    f"xác suất mưa {nearest['rain_prob']:.0f}%"
                )
            if nearest.get("wind_kmh") is not None:
                current_bits.append(f"gió {nearest['wind_kmh']:.0f} km/h")
            if nearest.get("humidity") is not None:
                current_bits.append(f"độ ẩm {nearest['humidity']:.0f}%")
            if current_bits:
                lines.append(
                    "- Khung giờ gần hiện tại theo dự báo: "
                    + ", ".join(current_bits)
                    + "."
                )

    period_txt = "; ".join(f"{n}: {p['label'].lower()}" for n, p in a["periods"].items())
    if period_txt:
        lines.append(f"- Theo buổi: {period_txt}.")
    best = [n for n, p in a["periods"].items() if p["risk"] == min(q["risk"] for q in a["periods"].values())]
    if risk >= 1 and best and risk < 3:
        lines.append(f"- Khung ít rủi ro nhất cho hoạt động ngoài trời: {', '.join(best)}.")
    if a.get("uv_max") is not None and a["uv_max"] >= 8:
        lines.append(f"- Chỉ số UV tối đa khoảng {a['uv_max']:.0f} (cao): nhớ kem chống nắng, mũ, kính.")

    risky = [n for n, p in a["periods"].items() if p["risk"] >= 1]
    when = ", ".join(f"buổi {n}" for n in risky)
    if risky and len(risky) < len(a["periods"]):
        lines.append(f"- Phương tiện ({when}): {recommend_transport(risk)} "
                     "Các buổi còn lại có thể đi như bình thường.")
    else:
        lines.append("- Phương tiện: " + recommend_transport(risk))

    # --- gợi ý địa điểm (chỉ khi dữ liệu mới, chỉ lấy từ DB)
    if not a["is_stale"]:
        if risk >= 3:
            lines.append(
                "Ưu tiên an toàn: hoãn biển, sông, thác, leo núi và các điểm ngắm cảnh ngoài trời. "
                "Open-Meteo không có cảnh báo chính thức, bạn nên xem thêm bản tin của "
                "Trung tâm Dự báo Khí tượng Thủy văn Quốc gia."
            )
        elif risk >= 2 and db is not None:
            ins = _pick_places(db, "indoor", max_total=4)
            outs = _pick_places(db, "outdoor", max_total=3)
            if ins:
                lines.append(f"Nên đi ({when}, ưu tiên trong nhà): " + ", ".join(ins) + ".")
            lines.append(f"Nên tránh ({when}): bãi biển, sông, thác, leo núi, "
                         "ngắm cảnh ngoài trời" + (f" (ví dụ {', '.join(outs)})" if outs else "") + ".")
        elif risk == 1:
            lines.append("Ngoài trời vẫn đi được, nhưng nên linh hoạt: xếp việc ngoài trời vào khung "
                         "ít mưa và có sẵn phương án trong nhà.")
        else:
            lines.append("Hợp cho cả biển, ngắm cảnh lẫn ăn uống, bạn cứ thoải mái lên kế hoạch.")

    if risk >= 1:
        lines.append("Nhớ mang ô hoặc áo mưa, giày dép chống trơn, và bọc điện thoại cho khỏi ướt nhé!")

    lines.append(
        f"(Nguồn: {forecast.get('source', 'Open-Meteo')} "
        f"https://open-meteo.com/en/docs; cập nhật lúc {a['fetched_at']}. "
        "Dự báo luôn có sai số, bạn kiểm tra lại trước khi đi.)"
    )

    return {
        "text": "\n".join(lines),
        "steps": [
            f"Lấy dự báo Open-Meteo (cập nhật {a['fetched_at']})",
            "Phân tích theo giờ: xác suất mưa, lượng mưa, gió, nhiệt độ",
        ],
        "suggestions": ["Lên lịch trình cho ngày này", "Gợi ý quán cà phê trong nhà"],
        "links": [], "status": "ok", "_skip_llm": True, "places": [],
        "weather": {
            **weather_metadata(forecast, target, a),
            "max_risk": risk,
        },
    }


def build_weather_range_reply(
    forecast: dict,
    start: date,
    duration_days: int,
    today: date,
) -> dict:
    lines = [
        f"Dự báo thời tiết {duration_days} ngày ở Đà Nẵng "
        f"(Open-Meteo, https://open-meteo.com/en/docs):"
    ]
    if forecast.get("is_stale"):
        lines.append(
            f"⚠ Dữ liệu cũ (lưu cách đây {forecast.get('stale_minutes', '?')} phút), "
            "không phải dự báo mới nhất."
        )

    risks = []
    for offset in range(duration_days):
        target = start + timedelta(days=offset)
        analysis = analyze_date(forecast, target.isoformat())
        lines.append(f"\n{_label(target, today)}:")
        if not analysis.get("available"):
            last = forecast["daily"][-1]["date"] if forecast.get("daily") else "?"
            lines.append(
                f"- Chưa có dữ liệu cho ngày này; nguồn dự báo hiện có đến {last}."
            )
            continue
        risks.append(analysis["max_risk"])
        lines.extend(summary_lines(analysis))
        lines.append("- Phương tiện: " + recommend_transport(analysis["max_risk"]))
        if analysis["max_risk"] >= 2:
            lines.append(
                "- Hạn chế hoạt động ngoài trời trong khung giờ có mưa to, dông hoặc gió mạnh."
            )

    lines.append(
        "\nDự báo luôn có sai số; hãy kiểm tra lại trước khi đi. "
        "Open-Meteo không cung cấp cảnh báo thiên tai chính thức."
    )
    metadata = weather_metadata(forecast, start)
    metadata.update({
        "requested_days": duration_days,
        "requested_end_date": (start + timedelta(days=duration_days - 1)).isoformat(),
        "max_risk": max(risks) if risks else None,
    })
    return {
        "text": "\n".join(lines),
        "steps": [
            "Lấy dự báo Open-Meteo",
            f"Phân tích dữ liệu theo ngày cho {duration_days} ngày",
        ],
        "suggestions": [],
        "links": [],
        "status": "ok",
        "_skip_llm": True,
        "places": [],
        "weather": metadata,
    }


def maybe_weather_reply(message: str, intent: str, state, db=None) -> dict | None:
    """Trả về reply nếu là câu hỏi thời tiết, ngược lại None (để luồng cũ xử lý)."""
    if not (intent == "weather" or looks_like_weather(message)):
        return None

    today = datetime.now(TZ).date()
    remembered = None
    raw = getattr(state, "wx_date", None)
    if isinstance(raw, str):
        try:
            remembered = date.fromisoformat(raw)
        except ValueError:
            remembered = None
    if remembered and remembered < today:
        remembered = None

    target, explicit = parse_target_date(message, today, remembered)
    day_match = re.search(r"\b([2-7])\s*[- ]?\s*(ngay|days?)\b", _strip(message))
    duration_days = int(day_match.group(1)) if day_match else None
    if duration_days is None and re.search(r"\b(cuoi tuan|weekend)\b", _strip(message)):
        duration_days = 2

    # "Nếu mưa thì sao?" mà chưa biết đi ngày nào: hỏi lại, không đoán.
    if not explicit and remembered is None and "neu" in _strip(message):
        return _fail_text("Bạn định đi vào ngày nào nhỉ? Cho mình ngày cụ thể "
                          "(ví dụ ngày mai, cuối tuần, 12/11) để mình tra dự báo đúng nhé.")

    try:
        forecast = get_weather_forecast(forecast_days=FORECAST_DAYS)
    except RuntimeError:
        return _fail_text(
            "Mình đang không kết nối được nguồn dự báo và cũng chưa có dữ liệu "
            "lưu đủ mới, nên chưa dám nói chắc ngày đó mưa hay nắng. "
            "Bạn thử lại sau ít phút, hoặc xem bản tin chính thức nhé.",
            {
                "date": target.isoformat(),
                "source": "Open-Meteo",
                "reference_url": "https://open-meteo.com/en/docs",
                "fetched_at": None,
                "cache_status": "unavailable",
                "location": "Da Nang, Vietnam",
                "valid_from": None,
                "valid_until": None,
                "is_stale": False,
            },
        )

    try:
        state.wx_date = target.isoformat()
    except Exception:
        pass

    if duration_days:
        return build_weather_range_reply(forecast, target, duration_days, today)
    return build_weather_reply(forecast, target, today, db)
