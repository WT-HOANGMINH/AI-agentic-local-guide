"""
Chạy:  python -m pytest tests/test_weather.py -q     (hoặc: python tests/test_weather.py)
Không cần mạng và không cần DB: dùng dự báo giả và monkeypatch.
"""
import sys
import types
from datetime import date

# Nếu máy chưa có httpx thì dùng bản giả (chỉ để import được).
try:
    import httpx  # noqa: F401
except ModuleNotFoundError:
    stub = types.ModuleType("httpx")
    stub.HTTPError = type("HTTPError", (Exception,), {})
    stub.get = lambda *a, **k: (_ for _ in ()).throw(stub.HTTPError("no network"))
    sys.modules["httpx"] = stub
    import httpx  # noqa: F401

from backend.services import weather_service as ws
from backend.services import weather_chat as wc
from backend.services.weather_analyzer import analyze_date, classify_hour, recommend_transport

D = "2026-11-08"          # ngày giả: Chủ nhật
TODAY = date(2026, 11, 7)


def make_forecast(hour_overrides=None, day=D):
    hour_overrides = hour_overrides or {}
    """hour_overrides: {giờ: {trường: giá trị}}. Mặc định trời quang."""
    hours = []
    for h in range(24):
        base = dict(temp_c=27, feels_like_c=30, humidity=70, rain_prob=5, rain_mm=0.0,
                    weather_code=1, wind_kmh=10, gust_kmh=18, wind_dir=90, uv=5)
        base.update(hour_overrides.get(h, {}))
        base["time"] = f"{day}T{h:02d}:00"
        hours.append(base)
    daily = [dict(date=day, weather_code=1, temp_max=31, temp_min=25,
                  rain_prob_max=max(x["rain_prob"] for x in hours),
                  rain_sum_mm=round(sum(x["rain_mm"] for x in hours), 1),
                  gust_max_kmh=18, uv_max=5)]
    return {"hours": hours, "daily": daily, "source": "Open-Meteo",
            "fetched_at": "2026-11-07T20:00+07:00", "is_stale": False}


def span(a, b, **kw):
    return {h: kw for h in range(a, b)}


def test_sunny_has_no_warning():
    a = analyze_date(make_forecast(), D)
    assert a["max_risk"] == 0
    r = wc.build_weather_reply(make_forecast(), date(2026, 11, 8), TODAY)
    assert "Nhớ mang ô" not in r["text"]
    assert "Nên tránh" not in r["text"]
    current = wc.build_weather_reply(make_forecast(day=TODAY.isoformat()), TODAY, TODAY)
    assert "Khung giờ gần hiện tại theo dự báo" in current["text"]
    assert current["weather"]["cache_status"] == "fresh"


def test_cloudy_is_still_ok():
    f = make_forecast(span(6, 22, weather_code=3, rain_prob=10))
    assert analyze_date(f, D)["max_risk"] == 0


def test_light_rain_risk1_and_transport():
    f = make_forecast(span(14, 18, rain_mm=0.6, rain_prob=55, weather_code=61))
    a = analyze_date(f, D)
    assert a["periods"]["chiều"]["label"] == "Mưa nhẹ" and a["max_risk"] == 1
    assert "áo mưa" in recommend_transport(1)


def test_heavy_rain_afternoon_morning_ok():
    f = make_forecast(span(14, 18, rain_mm=9.0, rain_prob=85, weather_code=65))
    a = analyze_date(f, D)
    assert a["periods"]["sáng"]["risk"] == 0
    assert a["periods"]["chiều"]["condition"] == "heavy_rain"
    wc._load_candidates = lambda db, want: (
        [("Cafe A", "cafe"), ("Vincom X", "shopping")] if want == "indoor"
        else [("Bãi biển Y", "tourist_attraction")])
    r = wc.build_weather_reply(f, date(2026, 11, 8), TODAY, db=object())
    t = r["text"]
    assert "85%" in t and "không phải" in t           # giải thích xác suất mưa
    assert "ô tô" in t.lower() and "Nên tránh" in t and "Nhớ mang ô" in t
    assert "Cafe A" in t or "Vincom X" in t            # chỉ địa điểm từ DB
    assert r["_skip_llm"] is True
    assert "Tốc độ gió tối đa" in t and "Nhiệt độ cảm nhận" in t


def test_three_day_weather_outlook_has_range_and_real_source_metadata(monkeypatch):
    from datetime import datetime, timedelta

    start = datetime.now(wc.TZ).date()
    first = make_forecast(day=start.isoformat())
    second = make_forecast(day=(start + timedelta(days=1)).isoformat())
    first["hours"].extend(second["hours"])
    first["daily"].extend(second["daily"])
    first.update(fetched_at="2026-11-06T20:00+07:00", from_cache=True)
    class S: pass
    monkeypatch.setattr(wc, "get_weather_forecast", lambda **kwargs: first)
    result = wc.maybe_weather_reply("dự báo 2 ngày tới", "weather", S())
    assert "2 ngày" in result["text"]
    assert result["weather"]["cache_status"] == "cached"
    assert result["weather"]["reference_url"] == "https://open-meteo.com/en/docs"
    assert result["weather"]["requested_end_date"] == (start + timedelta(days=1)).isoformat()


def test_high_prob_but_tiny_rain_is_not_banned():
    f = make_forecast(span(14, 18, rain_prob=80, rain_mm=0.0, weather_code=3))
    a = analyze_date(f, D)
    assert a["max_risk"] == 1                            # chỉ lưu ý, không cấm


def test_low_prob_but_thunderstorm_is_severe():
    f = make_forecast(span(15, 17, rain_prob=30, rain_mm=1.0, weather_code=95))
    a = analyze_date(f, D)
    assert a["max_risk"] == 3
    t = wc.build_weather_reply(f, date(2026, 11, 8), TODAY)["text"]
    assert "an toàn" in t and "Trung tâm Dự báo" in t


def test_strong_gust_is_extreme():
    assert classify_hour(dict(time="x", gust_kmh=80, rain_mm=0))["risk"] == 3


def test_missing_rain_prob_is_disclosed_not_invented():
    f = make_forecast()
    f["daily"][0]["rain_prob_max"] = None
    t = wc.build_weather_reply(f, date(2026, 11, 8), TODAY)["text"]
    assert "không cung cấp xác suất mưa" in t


def test_date_beyond_forecast_is_declined():
    r = wc.build_weather_reply(make_forecast(), date(2026, 11, 20), TODAY)
    assert "chỉ có dự báo" in r["text"]


def test_stale_data_is_labelled_and_no_place_advice():
    f = make_forecast(span(14, 18, rain_mm=9.0, rain_prob=85, weather_code=65))
    f.update(is_stale=True, stale_minutes=95)
    t = wc.build_weather_reply(f, date(2026, 11, 8), TODAY, db=object())["text"]
    assert "dữ liệu cũ" in t and "95 phút" in t and "Nên đi" not in t


def test_api_unavailable_without_cache(monkeypatch=None):
    ws._cache.clear()
    ws._call_api = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
    try:
        ws.get_weather_forecast(forecast_days=3)
        assert False, "phải raise"
    except RuntimeError:
        pass
    class S: pass
    r = wc.maybe_weather_reply("mai có mưa không", "weather", S())
    assert "chưa dám nói chắc" in r["text"]            # trung thực, không bịa số


def test_cache_fresh_then_stale_when_api_fails():
    ws._cache.clear()
    calls = {"n": 0}
    raw = {"hourly": {"time": [f"{D}T00:00"], "precipitation_probability": [40]},
           "daily": {"time": [D], "precipitation_probability_max": [40]}}
    def ok(*a, **k):
        calls["n"] += 1
        return raw
    ws._call_api = ok
    first = ws.get_weather_forecast(forecast_days=2)
    again = ws.get_weather_forecast(forecast_days=2)
    assert calls["n"] == 1 and again["from_cache"] and not again["is_stale"]
    assert "rain_mm" in first["unavailable_fields"]     # trường thiếu được ghi rõ
    # API chết + cache hết hạn 'mới' nhưng còn trong 6 giờ -> trả về và đánh dấu cũ
    ws._cache[next(iter(ws._cache))]["ts"] -= 3600
    ws._call_api = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
    old = ws.get_weather_forecast(forecast_days=2)
    assert old["is_stale"] is True and old["stale_minutes"] >= 60
    # quá 6 giờ -> không dùng nữa
    ws._cache[next(iter(ws._cache))]["ts"] -= 7 * 3600
    try:
        ws.get_weather_forecast(forecast_days=2)
        assert False
    except RuntimeError:
        pass


def test_forecast_changes_after_itinerary():
    """Dự báo đổi từ nắng sang mưa to: kết quả phải đổi theo."""
    before = analyze_date(make_forecast(), D)["max_risk"]
    after = analyze_date(make_forecast(span(14, 18, rain_mm=10, rain_prob=90, weather_code=65)), D)
    assert before == 0 and after["max_risk"] == 2 and after["periods"]["chiều"]["risk"] == 2


def test_date_parsing():
    p = wc.parse_target_date
    assert p("mai có mưa không", TODAY) == (date(2026, 11, 8), True)
    assert p("hôm nay trời sao", TODAY) == (TODAY, True)
    assert p("ngày mốt có nắng không", TODAY) == (date(2026, 11, 9), True)
    assert p("cuối tuần này thời tiết", TODAY) == (date(2026, 11, 7), True)   # hôm nay là thứ Bảy
    assert p("thời tiết 12/11", TODAY) == (date(2026, 11, 12), True)
    assert p("nếu mưa thì sao", TODAY, date(2026, 11, 8)) == (date(2026, 11, 8), False)


def test_date_parsing_false_positives():
    p = wc.parse_target_date
    assert p("Lịch trình 2-3 ngày ở Đà Nẵng", TODAY) == (TODAY, False)      # '2-3' không phải ngày 2/3
    assert p("đi 1/2 ngày thôi", TODAY) == (TODAY, False)                     # nửa ngày
    assert p("chợ đêm Mai Hắc Đế", TODAY) == (TODAY, False)                  # tên đường, không phải 'mai'
    assert p("đi ngày 12 tháng 11", TODAY) == (date(2026, 11, 12), True)


def test_trigger_detection():
    assert wc.looks_like_weather("Ê mai Đà Nẵng có mưa không?")
    assert wc.looks_like_weather("Nếu mưa thì sao?")
    assert not wc.looks_like_weather("Lên lịch trình 2 ngày 1 đêm")
    assert not wc.looks_like_weather("mua quà ở đâu")   # 'mua' = buy, không phải mưa


def test_followup_without_date_asks_back():
    class S: pass
    r = wc.maybe_weather_reply("Nếu mưa thì sao?", "unclear", S())
    assert r and "ngày nào" in r["text"]


def test_classify_places():
    from backend.enrich_weather_profile import classify as c
    assert c("Bảo tàng Chăm", "tourist_attraction") == "indoor"
    assert c("Bãi biển Mỹ Khê", "tourist_attraction") == "outdoor"
    assert c("Cau Rong Da Nang", "tourist_attraction") == "outdoor"
    assert c("Chùa Linh Ứng", "tourist_attraction") == "weather_dependent"
    assert c("Trinh Ca Phe", "cafe") == "indoor"
    assert c("Cafe view biển ABC", "cafe") == "weather_dependent"
    assert c("Chợ Hàn", "shopping") == "weather_dependent"
    assert c("Vincom Plaza", "shopping") == "indoor"


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("PASS", name)
            except Exception as e:
                fails += 1; print("FAIL", name, "->", repr(e))
    sys.exit(1 if fails else 0)
