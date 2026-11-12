from datetime import datetime

# ---- Ngưỡng cấu hình (chỉnh tại đây, không hardcode rải rác) ----
LIGHT_RAIN_MM = 0.2      # mm/giờ
MODERATE_RAIN_MM = 2.5
HEAVY_RAIN_MM = 7.6
STRONG_WIND_KMH = 40
STRONG_GUST_KMH = 50
EXTREME_GUST_KMH = 75
HOT_FEELS_LIKE_C = 38
THUNDER_CODES = {95, 96, 99}

PERIODS = {
    "sáng": range(6, 11),
    "trưa": range(11, 14),
    "chiều": range(14, 18),
    "tối": range(18, 22),
}

# risk: 0 = ổn, 1 = lưu ý, 2 = tránh hoạt động ngoài trời, 3 = nghiêm trọng
LABELS = {
    "clear": "Nắng / quang đãng", "cloudy": "Nhiều mây",
    "light_rain": "Mưa nhẹ", "moderate_rain": "Mưa vừa",
    "heavy_rain": "Mưa to", "thunderstorm": "Dông / sấm sét",
    "strong_wind": "Gió mạnh", "extreme": "Thời tiết cực đoan",
}


def classify_hour(h: dict) -> dict:
    mm = h.get("rain_mm") or 0.0
    prob = h.get("rain_prob")
    gust = h.get("gust_kmh") or 0.0
    wind = h.get("wind_kmh") or 0.0
    feels = h.get("feels_like_c")
    code = h.get("weather_code")
    notes = []

    if gust >= EXTREME_GUST_KMH or (code in THUNDER_CODES and mm >= HEAVY_RAIN_MM):
        cond, risk = "extreme", 3
    elif code in THUNDER_CODES:
        cond, risk = "thunderstorm", 3
    elif mm >= HEAVY_RAIN_MM:
        cond, risk = "heavy_rain", 2
    elif gust >= STRONG_GUST_KMH or wind >= STRONG_WIND_KMH:
        cond, risk = "strong_wind", 2
    elif mm >= MODERATE_RAIN_MM:
        cond, risk = "moderate_rain", 2
    elif mm >= LIGHT_RAIN_MM and (prob is None or prob >= 30):
        cond, risk = "light_rain", 1
    else:
        cond = "cloudy" if code in (2, 3, 45, 48) else "clear"
        risk = 0
        # xác suất cao nhưng lượng mưa gần 0: chỉ lưu ý, không cấm hoạt động
        if prob is not None and prob >= 60:
            risk = 1
            notes.append("Xác suất mưa cao nhưng lượng mưa dự báo rất thấp")

    if feels is not None and feels >= HOT_FEELS_LIKE_C:
        risk = max(risk, 1)
        notes.append("Nóng, nhiệt độ cảm nhận cao")

    return {"time": h["time"], "condition": cond, "label": LABELS[cond],
            "risk": risk, "rain_prob": prob, "rain_mm": mm, "notes": notes}


def analyze_date(forecast: dict, date: str) -> dict:
    """Phân tích 1 ngày (YYYY-MM-DD) theo từng buổi."""
    hours = [h for h in forecast["hours"] if h["time"].startswith(date)]
    if not hours:
        return {"date": date, "available": False}

    periods = {}
    for name, rng in PERIODS.items():
        sel = [h for h in hours if int(h["time"][11:13]) in rng]
        if not sel:
            continue
        cls = [classify_hour(h) for h in sel]
        worst = max(cls, key=lambda c: c["risk"])
        probs = [c["rain_prob"] for c in cls if c["rain_prob"] is not None]
        periods[name] = {
            "condition": worst["condition"], "label": worst["label"],
            "risk": worst["risk"],
            "rain_prob_max": max(probs) if probs else None,
            "rain_mm_total": round(sum(c["rain_mm"] for c in cls), 1),
            "notes": sorted({n for c in cls for n in c["notes"]}),
        }

    day = next((d for d in forecast["daily"] if d["date"] == date), {})
    day_hours = hours
    wind_values = [h["wind_kmh"] for h in day_hours if h.get("wind_kmh") is not None]
    gust_values = [h["gust_kmh"] for h in day_hours if h.get("gust_kmh") is not None]
    feels_values = [
        h["feels_like_c"] for h in day_hours
        if h.get("feels_like_c") is not None
    ]
    uv_values = [h["uv"] for h in day_hours if h.get("uv") is not None]
    return {
        "date": date, "available": True, "periods": periods,
        "temp_min": day.get("temp_min"), "temp_max": day.get("temp_max"),
        "rain_prob_max": day.get("rain_prob_max"),
        "rain_sum_mm": day.get("rain_sum_mm"),
        "wind_max_kmh": max(wind_values) if wind_values else None,
        "gust_max_kmh": max(gust_values) if gust_values else day.get("gust_max_kmh"),
        "feels_like_min": min(feels_values) if feels_values else None,
        "feels_like_max": max(feels_values) if feels_values else None,
        "uv_max": max(uv_values) if uv_values else day.get("uv_max"),
        "max_risk": max((p["risk"] for p in periods.values()), default=0),
        "fetched_at": forecast.get("fetched_at"),
        "is_stale": forecast.get("is_stale", False),
    }


def recommend_transport(risk: int, user_pref: str | None = None) -> str:
    if risk >= 3:
        return "Hoãn hoạt động ngoài trời, ở nơi an toàn và theo dõi cảnh báo chính thức."
    if risk == 2:
        return "Ưu tiên ô tô / taxi / xe công nghệ; hạn chế đi xe máy và đi bộ."
    if risk == 1:
        return "Nên đi ô tô hoặc taxi; nếu đi xe máy thì mang áo mưa."
    return user_pref or "Xe máy, xe đạp, đi bộ hoặc ô tô tùy khoảng cách."


def poi_allowed(poi_profile: str, period_risk: int) -> bool:
    """poi_profile: 'indoor' | 'outdoor' | 'weather_dependent'."""
    if poi_profile == "indoor":
        return period_risk < 3
    if poi_profile == "weather_dependent":
        return period_risk <= 1
    return period_risk == 0 or period_risk == 1  # outdoor: tránh khi risk >= 2


def build_advice(a: dict) -> str:
    """Tạo thông báo tiếng Việt từ số liệu thật. Không có số liệu thì không nói."""
    if not a.get("available"):
        return "Mình chưa có dự báo cho ngày này nên chưa thể đưa ra khuyến nghị thời tiết."

    lines = [f"Dự báo ngày {a['date']} ở Đà Nẵng (cập nhật lúc {a['fetched_at']}):"]
    if a["is_stale"]:
        lines.append("Lưu ý: không kết nối được nguồn dự báo, đây là dữ liệu cũ, hãy kiểm tra lại.")
    if a["rain_prob_max"] is not None:
        lines.append(f"- Xác suất có mưa cao nhất trong ngày: {a['rain_prob_max']}% "
                     "(đây là khả năng xảy ra mưa, không phải % thời gian mưa).")
    if a["rain_sum_mm"] is not None:
        lines.append(f"- Tổng lượng mưa dự báo: {a['rain_sum_mm']} mm.")
    if a["temp_min"] is not None:
        lines.append(f"- Nhiệt độ: {a['temp_min']}–{a['temp_max']}°C.")
    for name, p in a["periods"].items():
        lines.append(f"- Buổi {name}: {p['label']}")

    risk = a["max_risk"]
    lines.append("- Phương tiện: " + recommend_transport(risk))
    if risk >= 1:
        lines.append("- Nên đi: bảo tàng, trung tâm thương mại, quán cà phê, nhà hàng, "
                     "khu vui chơi trong nhà.")
        lines.append("- Nên tránh: bãi biển, sông, thác, leo núi, điểm ngắm cảnh ngoài trời khi mưa to/dông/gió mạnh.")
        lines.append("- Nhớ mang ô hoặc áo mưa, giày dép chống trơn, bảo vệ điện thoại khỏi nước.")
    lines.append("Dự báo luôn có sai số, hãy kiểm tra lại trước khi đi.")
    return "\n".join(lines)