"""Kiểm thử luồng hội thoại mới (chỉ đường, vị trí, tạm biệt, thời tiết, chọn nhiều sở thích).
Chạy:  python -m pytest tests/test_dialogue_route.py -q   (từ thư mục gốc dự án)
Không cần MySQL: địa điểm giả được nạp vào place_repo."""
import sys
import types
from types import SimpleNamespace

# Nếu môi trường thiếu thư viện nặng (sqlalchemy/httpx) thì dùng bản giả để test logic thuần.
for name in ("sqlalchemy", "sqlalchemy.orm", "httpx", "backend.models.place"):
    try:
        __import__(name)
    except Exception:
        mod = types.ModuleType(name)
        mod.Session = object
        mod.Place = type("Place", (), {})
        sys.modules[name] = mod

from backend.services import dialogue as dlg           # noqa: E402
from backend.services import place_repo, planner_service  # noqa: E402


class P:
    def __init__(self, id, name, category, lat=None, lng=None, desc="", address="Đà Nẵng", zone=None):
        self.id, self.name, self.category = id, name, category
        self.latitude, self.longitude = lat, lng
        self.description, self.address, self.zone = desc, address, zone
        self.price_level = 2
        self.opening_hours = "07:00 - 17:00"
        self.rating = 4.5
        self.is_active = True
        self.duration_min = None
        self.open_time = self.close_time = self.best_time = None


PLACES = [
    P(1, "Chùa Linh Ứng Sơn Trà", "tourist_attraction", 16.1005, 108.2778, "Chùa có tượng Phật Quan Âm cao nhất Việt Nam", zone="son_tra_ban_dao"),
    P(2, "Cầu Rồng", "tourist_attraction", 16.0612, 108.2273, "Cầu biểu tượng phun lửa", zone="trung_tam"),
    P(3, "Bãi biển Mỹ Khê", "tourist_attraction", 16.0544, 108.2480, "Bãi biển đẹp", zone="son_tra"),
    P(4, "Bán đảo Sơn Trà", "tourist_attraction", 16.1167, 108.2667, "Khu bảo tồn thiên nhiên", zone="son_tra_ban_dao"),
    P(5, "Mì Quảng Bà Mua", "restaurant", 16.0680, 108.2150, "Mì Quảng", zone="trung_tam"),
]


def setup_function(_):
    place_repo.all_active = lambda db: PLACES
    place_repo.get = lambda db, pid: next((p for p in PLACES if p.id == pid), None)
    place_repo.by_ids = lambda db, ids: [p for p in PLACES if p.id in set(ids)]
    place_repo.restaurants = lambda db: [p for p in PLACES if p.category == "restaurant"]


def run(st, msg, intent="transport", conf=0.9, **kw):
    return dlg.respond(st, msg, intent, conf, None, **kw)


def test_route_without_origin_asks_origin_and_offers_maps_link():
    st = dlg.State()
    r = run(st, "Tôi muốn đi đến Chùa Linh Ứng đường nào tối ưu nhất?")
    assert r["status"] == "needs_clarification"
    assert "Chùa Linh Ứng" in r["text"]
    assert any(o["message"] == "__geo__" for o in r["suggestions"])
    assert r["links"] and "google.com/maps/dir" in r["links"][0]["url"]
    assert r["closing"] is None


def test_route_with_gps_gives_estimate_and_honest_note():
    st = dlg.State()
    r = run(st, "Tôi muốn đi đến Chùa Linh Ứng đường nào tối ưu nhất?", lat=16.06, lng=108.22)
    assert r["status"] == "completed"
    assert "km" in r["text"] and "chưa tính tắc đường" in r["text"]
    assert "origin=16.06,108.22" in r["links"][0]["url"]
    assert r["closing"]                                     # có lời hỏi thêm + lời chúc


def test_route_two_places_from_chip():
    st = dlg.State()
    run(st, "Tôi muốn đi đến Chùa Linh Ứng đường nào tối ưu nhất?")
    r = run(st, "Từ Cầu Rồng đến Chùa Linh Ứng Sơn Trà", intent="attraction")   # classifier có thể nhầm: vẫn phải xử lý
    assert r["status"] == "completed"
    assert "Cầu Rồng" in r["text"] and "Chùa Linh Ứng" in r["text"]
    assert st.pending is None and st.route_dest is None


def test_route_unknown_origin_uses_typed_text():
    st = dlg.State()
    run(st, "Đường đến Chùa Linh Ứng thế nào?")
    r = run(st, "Từ sân bay Đà Nẵng đến Chùa Linh Ứng Sơn Trà")
    assert r["status"] == "completed"
    assert "sân bay Đà Nẵng" in r["text"]
    assert "origin=" in r["links"][0]["url"]


def test_nearby_search_ranks_all_categories_by_haversine_and_shares_poi_details(monkeypatch):
    places = [
        P(10, "Gần nhất", "tourist_attraction", 16.0612, 108.2273, "Mô tả địa điểm"),
        P(11, "Quán ăn", "restaurant", 16.0680, 108.2150, "Món địa phương"),
        P(12, "Không có tọa độ", "cafe", None, None),
    ]
    monkeypatch.setattr(dlg, "get_ranker", lambda _db: SimpleNamespace(places=places))
    state = dlg.State(pos=(16.06, 108.22))

    answer = dlg.handle_search(
        state, None, "attraction", "Tìm địa điểm gần chỗ tôi", {}, None, []
    )

    assert answer["text"].index("Gần nhất") < answer["text"].index("Quán ăn")
    assert "Quán ăn" in answer["text"]
    assert "Mô tả địa điểm" in answer["text"]
    assert "0.8 km" in answer["text"]
    assert "16.06,108.22" not in answer["text"]
    assert answer["links"]
    assert answer["_skip_llm"] is True


def test_nearby_food_query_filters_to_restaurants_and_expands_radius(monkeypatch):
    places = [
        P(20, "Nhà hàng gần", "restaurant", 16.0680, 108.2150, "Mì Quảng"),
        P(21, "Nhà hàng xa hơn", "restaurant", 16.12, 108.25, "Hải sản"),
        P(22, "Điểm tham quan", "tourist_attraction", 16.0612, 108.2273),
    ]
    monkeypatch.setattr(dlg, "get_ranker", lambda _db: SimpleNamespace(places=places))
    monkeypatch.setenv("NEARBY_SEARCH_RADIUS_KM", "1")
    state = dlg.State(pos=(16.06, 108.22))

    answer = dlg.handle_search(
        state, None, "food", "Tìm quán ăn gần đây", {}, None, []
    )

    assert "Nhà hàng gần" in answer["text"]
    assert "Nhà hàng xa hơn" in answer["text"]
    assert "Điểm tham quan" not in answer["text"]
    assert "mở rộng tới 10 km" in answer["text"]


def test_nearby_location_phrase_is_not_reported_as_an_unknown_place(monkeypatch):
    monkeypatch.setattr(dlg, "extract_slots", lambda _message: ({"places": ["chỗ"]}, []))
    monkeypatch.setattr(dlg, "get_ranker", lambda _db: SimpleNamespace(places=[PLACES[1]]))

    answer = dlg.respond(
        dlg.State(pos=(16.06, 108.22)),
        "Tìm địa điểm gần chỗ tôi",
        "attraction",
        0.9,
        None,
    )

    assert "chưa tìm thấy" not in answer["text"]
    assert "Cầu Rồng" in answer["text"]


def test_explicit_place_nearby_phrase_is_not_treated_as_current_location():
    assert not dlg.is_current_location_request("Tìm quán ăn gần Cầu Rồng")


def test_thanks_ends_politely_without_pending():
    st = dlg.State()
    run(st, "Tôi muốn đi đến Chùa Linh Ứng đường nào?")
    r = run(st, "cảm ơn bạn", intent="greeting")
    assert r["status"] == "completed" and "vui vẻ" in r["text"]
    assert st.pending is None


def test_weather_uses_real_tool_and_reports_step(monkeypatch=None):
    planner_service.weather_text = lambda *a, **k: "Dự báo thời tiết: ..."
    steps = []
    st = dlg.State()
    r = run(st, "Thời tiết Đà Nẵng ngày mai thế nào?", intent="weather", on_step=steps.append)
    assert "Dự báo" in r["text"]
    assert any("Open-Meteo" in s for s in steps)          # bước hiện ra khi đang chạy, không phải kể lại sau


def test_itinerary_interest_question_is_multi_select():
    st = dlg.State()
    st.slots["days"] = 2
    r = run(st, "Lập lịch trình du lịch Đà Nẵng", intent="itinerary")
    assert r["status"] == "needs_clarification"
    assert r.get("suggestion_mode") == "multi"
    assert any(o.get("exclusive") for o in r["suggestions"])


def test_short_food_question_asks_with_chips():
    st = dlg.State()
    r = run(st, "ăn gì", intent="food", conf=0.9)
    assert r["status"] == "needs_clarification"
    assert len(r["suggestions"]) >= 3
