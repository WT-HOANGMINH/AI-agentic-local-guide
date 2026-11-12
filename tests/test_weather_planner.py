"""
Test xếp lịch theo thời tiết (không cần mạng/DB).
Chạy: PYTHONPATH=. python tests/test_weather_planner.py
"""
import sys
import types
from datetime import datetime, timedelta
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

try:
    import httpx  # noqa: F401
except ModuleNotFoundError:
    stub = types.ModuleType("httpx")
    stub.HTTPError = type("HTTPError", (Exception,), {})
    sys.modules["httpx"] = stub

sys.path.insert(0, "tests")
from test_weather import make_forecast, span  # noqa: E402
from backend.services import weather_planner as wp  # noqa: E402

D = "2026-11-08"


def place(pid, name, cat="tourist_attraction"):
    return NS(id=pid, name=name, category=cat, description="", address="", weather_profile=None)


BEACH = place(1, "Bai bien My Khe")
MUSEUM_ON_PLAN = place(2, "Bao tang Cham")
MUSEUM_ALT = place(5, "Bao tang Da Nang")
CAFE = place(7, "Trinh Ca Phe", "cafe")
TRAVEL = lambda a, b: abs(a.id - b.id)


def make_day():
    return {"attr_ids": [2, 1], "stops": [
        {"id": 2, "kind": "visit", "start": "09:00", "end": "10:30", "name": MUSEUM_ON_PLAN.name},
        {"id": 1, "kind": "visit", "start": "14:00", "end": "15:30", "name": BEACH.name},
    ]}


def run(forecast, day=None, pool=(MUSEUM_ALT,), protected=frozenset(), backups=(CAFE, MUSEUM_ALT)):
    day = day or make_day()
    places = {p.id: p for p in (BEACH, MUSEUM_ON_PLAN, MUSEUM_ALT, CAFE)}

    def replan(old_id, new_id):
        day["attr_ids"] = [new_id if i == old_id else i for i in day["attr_ids"]]
        for s in day["stops"]:
            if s["id"] == old_id:
                s["id"], s["name"] = new_id, places[new_id].name
        return {"dropped": []}

    rep = wp.adjust_day(
        idx=0, iso=D, forecast=forecast, get_day=lambda: day,
        by_id_fn=lambda: {i: places[i] for i in day["attr_ids"]},
        used_ids_fn=lambda: set(day["attr_ids"]), replan=replan, pool=list(pool),
        travel_min=TRAVEL, protected=protected, backups_pool=list(backups))
    return rep, day


RAIN = make_forecast(span(14, 18, rain_mm=9.0, rain_prob=85, weather_code=65))


def test_rainy_afternoon_swaps_beach_for_indoor_but_keeps_morning():
    rep, day = run(RAIN)
    assert [c["old"] for c in rep["changes"]] == ["Bai bien My Khe"]
    assert rep["changes"][0]["new"] == "Bao tang Da Nang"
    assert {s["id"] for s in day["stops"]} == {2, 5} and rep["unresolved"] == []
    text = wp.day_block("ngày mai", rep, RAIN)
    assert "Đã đổi" in text and "14:00–15:30" in text and "85%" in text and "ô tô" in text.lower()


def test_outdoor_in_good_morning_is_untouched():
    day = {"attr_ids": [1], "stops": [{"id": 1, "kind": "visit", "start": "08:00",
                                       "end": "09:30", "name": BEACH.name}]}
    rep, day = run(RAIN, day=day)
    assert rep["changes"] == [] and rep["unresolved"] == [] and day["stops"][0]["id"] == 1


def test_sunny_keeps_plan():
    f = make_forecast()
    rep, day = run(f)
    assert rep["changes"] == [] and "giữ nguyên" in wp.day_block("ngày mai", rep, f)


def test_user_requested_place_is_kept_with_warning_and_backups():
    rep, day = run(RAIN, protected=frozenset({1}))
    assert rep["changes"] == [] and any(s["id"] == 1 for s in day["stops"])
    u = rep["unresolved"][0]
    assert u["reason"] == "protected" and "Trinh Ca Phe" in u["backups"]
    assert "bạn yêu cầu" in wp.day_block("ngày mai", rep, RAIN)


def test_no_indoor_alternative_is_disclosed_not_invented():
    rep, day = run(RAIN, pool=())
    assert rep["unresolved"][0]["reason"] == "no_indoor"
    assert "chưa có điểm tham quan trong nhà" in wp.day_block("ngày mai", rep, RAIN)


def test_thunderstorm_prioritises_safety():
    f = make_forecast(span(14, 17, rain_prob=30, rain_mm=1.0, weather_code=95))
    rep, _ = run(f)
    assert rep["risk"] == 3
    assert "an toàn" in wp.day_block("ngày mai", rep, f)


def test_stale_forecast_does_not_change_plan():
    f = make_forecast(span(14, 18, rain_mm=9.0, rain_prob=85, weather_code=65))
    f.update(is_stale=True, stale_minutes=120)
    rep, day = run(f)
    assert rep["changes"] == [] and any(s["id"] == 1 for s in day["stops"])
    t = wp.day_block("ngày mai", rep, f)
    assert "dữ liệu cũ" in t and "KHÔNG dùng" in t


def test_date_outside_forecast_is_declined():
    f = make_forecast()
    f["hours"] = [h for h in f["hours"] if not h["time"].startswith(D)]
    f["daily"] = [{**f["daily"][0], "date": "2026-11-20"}]
    rep, _ = run(f)
    assert rep["available"] is False and "chỉ có đến" in wp.day_block("x", rep, f)


def test_forecast_change_after_itinerary_triggers_swap():
    sunny = run(make_forecast())[0]["changes"]
    stormy = run(RAIN)[0]["changes"]
    assert sunny == [] and len(stormy) == 1


# ---------- smoke test đoạn nối trong dialogue.py (dùng module giả cho phần chưa có file) ----------
def _load_dialogue():
    from backend.services import weather_chat as wc
    import backend.services as services
    for name in ("compose", "nlg", "place_repo", "planner_service", "planner", "ranker", "slot_service"):
        module = MagicMock()
        sys.modules[f"backend.services.{name}"] = module
        setattr(services, name, module)
    sys.modules["backend.services.slot_service"].strip_accents = wc._strip
    sys.modules["backend.services.slot_service"].AREA_ALIASES = {}
    sys.modules["backend.services.compose"].render_plan = lambda *a, **k: "[KẾ HOẠCH ĐÃ CẬP NHẬT]"
    sys.modules["backend.services.compose"].maps_links = lambda *a, **k: []
    import importlib
    sys.modules.pop("backend.services.dialogue", None)
    return importlib.import_module("backend.services.dialogue")


def test_dialogue_glue_replans_when_user_asks_if_it_rains():
    dlg = _load_dialogue()
    tomorrow = (datetime.now(dlg.wx.TZ).date() + timedelta(days=1)).isoformat()
    f = make_forecast(span(14, 18, rain_mm=9.0, rain_prob=85, weather_code=65), day=tomorrow)
    dlg.get_weather_forecast = lambda **k: f

    day = make_day()
    places = {p.id: p for p in (BEACH, MUSEUM_ON_PLAN, MUSEUM_ALT, CAFE)}
    st = dlg.State(plan=[day], travel_date=tomorrow, requested_place_ids=set())
    dlg.by_id_of = lambda db, plan: {i: places[i] for i in plan[0]["attr_ids"]}
    dlg.itinerary_data = lambda *a, **k: {"ok": True}
    dlg.pl.travel_min = TRAVEL

    def fake_replan(db, st_, idx, remove_id=None, add_ids=(), **k):
        d = st_.plan[idx]
        d["attr_ids"] = [add_ids[0] if i == remove_id else i for i in d["attr_ids"]]
        for s in d["stops"]:
            if s["id"] == remove_id:
                s["id"] = add_ids[0]
        return {"dropped": []}
    dlg.replan_day = fake_replan
    dlg.get_ranker = lambda db: NS(places=[BEACH, MUSEUM_ON_PLAN, MUSEUM_ALT, CAFE])
    dlg.wx.build_weather_reply = lambda forecast, target, today, db=None: {
        "text": "DỰ BÁO", "steps": [], "suggestions": [], "links": [], "weather": {}}

    res = dlg.handle_weather(st, object(), "Nếu mưa thì sao?", [])
    assert "Mình đã kiểm tra lại lịch trình" in res["text"] and "Đã đổi" in res["text"]
    assert "[KẾ HOẠCH ĐÃ CẬP NHẬT]" in res["text"] and res["itinerary"] == {"ok": True}
    assert {s["id"] for s in st.plan[0]["stops"]} == {2, 5}


def test_dialogue_followup_without_date_asks_back():
    dlg = _load_dialogue()
    res = dlg.handle_weather(dlg.State(), object(), "Nếu mưa thì sao?", [])
    assert "ngày nào" in res["text"]


def test_dialogue_remembers_tomorrow_from_itinerary_request():
    dlg = _load_dialogue()
    st = dlg.State()
    dlg.capture_travel_date(st, "Tôi muốn đi Đà Nẵng ngày mai", "itinerary")
    tomorrow = (datetime.now(dlg.wx.TZ).date() + timedelta(days=1)).isoformat()
    assert st.travel_date == tomorrow and st.slots["travel_date"] == tomorrow
    dlg.capture_travel_date(st, "lịch trình 2-3 ngày", "itinerary")           # không nuốt nhầm '2-3'
    assert st.travel_date == tomorrow


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("PASS", name)
            except Exception as e:
                import traceback; traceback.print_exc()
                fails += 1; print("FAIL", name, "->", repr(e))
    sys.exit(1 if fails else 0)
