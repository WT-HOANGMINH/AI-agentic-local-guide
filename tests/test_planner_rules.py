"""Kiểm tra các 'luật' của planner bằng dữ liệu giả lập (không cần DB). Chạy: pytest tests/"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import make_places  # noqa: E402

from backend.services import planner as pl  # noqa: E402


def _trip(n_days=3, start=None):
    places = make_places()
    by_id = {p.id: p for p in places}
    attrs = [p for p in places if p.category == "tourist_attraction"]
    foods = [p for p in places if p.category == "restaurant"]
    scores = {p.id: 1.0 - 0.05 * i for i, p in enumerate(attrs)}
    return pl.plan_trip(attrs, foods, [], scores, n_days, start), by_id


def test_stops_inside_opening_hours():
    plan, by_id = _trip()
    for day in plan:
        for s in day["stops"]:
            p = by_id[s["id"]]
            assert pl.to_min(s["start"]) >= pl.opens(p), (p.name, s)
            assert pl.to_min(s["end"]) <= pl.closes(p), (p.name, s)


def test_no_overlap_inside_a_day():
    plan, _ = _trip()
    for day in plan:
        for a, b in zip(day["stops"], day["stops"][1:]):
            assert pl.to_min(b["start"]) >= pl.to_min(a["end"]), (a, b)


def test_night_place_not_before_evening():
    plan, by_id = _trip(4)
    for day in plan:
        for s in day["stops"]:
            if by_id[s["id"]].best_time == "night":
                assert pl.to_min(s["start"]) >= 19 * 60, s


def test_long_place_gets_its_own_day_and_opens_on_time():
    plan, by_id = _trip(5)
    bana = [d for d in plan if any(s["id"] == 10 for s in d["stops"])]
    assert bana, "Bà Nà phải có trong lịch"
    visits = [s for s in bana[0]["stops"] if s["kind"] == "visit"]
    assert [s["id"] for s in visits] == [10], "ngày Bà Nà không xếp thêm điểm khác"
    assert visits[0]["start"] == "08:00", "bắt đầu đúng giờ mở cửa, không chờ vô nghĩa"


def test_meals_are_chosen_near_previous_stop():
    plan, by_id = _trip()
    for day in plan:
        for prev, cur in zip(day["stops"], day["stops"][1:]):
            if cur["kind"] == "meal" and by_id[prev["id"]].zone:
                same_zone_exists = any(p.category == "restaurant" and p.zone == by_id[prev["id"]].zone
                                       and p.id not in {s["id"] for s in day["stops"]} for p in make_places())
                if same_zone_exists:
                    assert by_id[cur["id"]].zone == by_id[prev["id"]].zone, (prev["name"], cur["name"])


def test_grouping_never_worse_than_given_order():
    plan, _ = _trip()
    for day in plan:
        assert day["saved"] >= 0


def test_zone_minutes_symmetric_and_hub_fallback():
    assert pl.zone_minutes("trung_tam", "hoi_an") == pl.zone_minutes("hoi_an", "trung_tam") == 45
    assert pl.zone_minutes("hoa_vang", "my_son") == 140
    assert pl.zone_minutes(None, "hoi_an") == 25
    assert pl.zone_minutes("hoi_an", "hoi_an") == 8


def test_dinner_comes_before_night_place_and_no_evening_lunch():
    places = make_places()
    by_id = {p.id: p for p in places}
    foods = [p for p in places if p.category == "restaurant"]
    night = [by_id[14]]                                   # chợ đêm, mở từ 18:00, best_time night
    res = pl.build_day(night, foods, None, "08:00")
    kinds = [(s["kind"], s["start"]) for s in res["stops"]]
    assert kinds[0][0] == "meal" and kinds[-1][0] == "visit", kinds
    assert not any(k == "meal" and pl.to_min(t) < 17 * 60 for k, t in kinds), "không có bữa trưa lúc chiều tối"
