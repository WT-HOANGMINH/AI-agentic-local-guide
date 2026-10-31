"""Chạy trọn các kịch bản hội thoại với dữ liệu giả lập. Cần đã huấn luyện slot_tagger.joblib."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import FakeDB, install_fake_repo  # noqa: E402

from backend.services import dialogue as dg  # noqa: E402
from backend.services import planner as pl  # noqa: E402
from backend.services.slot_service import model_ready  # noqa: E402


def _talk(st, msg, intent, conf=0.95):
    return dg.respond(st, msg, intent, conf, FakeDB())


def test_asks_back_when_message_is_too_short():
    if not model_ready():
        return
    install_fake_repo()
    st = dg.State()
    r = _talk(st, "lịch trình", "itinerary")
    assert "mấy ngày" in r["text"] and st.pending_for == "itinerary" and not st.plan
    r = _talk(st, "ăn gì", "food")
    assert "bữa nào" in r["text"]


def test_itinerary_choice_suggestions_continue_same_conversation():
    if not model_ready():
        return
    install_fake_repo()
    st = dg.State()
    first = _talk(st, "lịch trình", "itinerary")
    assert first["status"] == "needs_clarification"
    choice = next(
        option for option in first["suggestions"]
        if option["id"] == "two-day"
    )

    preference = _talk(st, choice["message"], "itinerary")
    assert preference["status"] == "needs_clarification"
    answer = _talk(st, "mình thích biển và thiên nhiên", "clarify_reply")

    assert answer["status"] == "completed"
    assert len(st.plan) == 2
    assert answer["suggestions"]


def test_famous_attractions_returns_five_and_refinement_choices():
    if not model_ready():
        return
    install_fake_repo()
    answer = _talk(
        dg.State(),
        "Gợi ý 5 địa điểm nổi tiếng ở Đà Nẵng",
        "attraction",
    )
    place_lines = [
        line for line in answer["text"].splitlines()
        if line[:2] in {"1.", "2.", "3.", "4.", "5."}
    ]
    assert len(place_lines) == 5
    assert answer["status"] == "completed"
    assert {item["id"] for item in answer["suggestions"]} >= {
        "popular", "highest-rated", "nearby"
    }


def test_nearby_query_asks_for_location_without_claiming_gps():
    if not model_ready():
        return
    install_fake_repo()
    answer = _talk(
        dg.State(),
        "Tìm địa điểm nổi tiếng gần tôi",
        "attraction",
    )
    assert answer["status"] == "needs_clarification"
    assert "chưa được cấp vị trí" in answer["text"]
    assert answer["suggestions"]


def test_short_itinerary_request_clarifies_and_keeps_user_details():
    if not model_ready():
        return
    places = install_fake_repo()
    by_id = {place.id: place for place in places}
    by_id[10].duration_min = None
    by_id[10].open_time = None
    by_id[10].close_time = None
    by_id[10].opening_hours = "08:00 – 17:00 hằng ngày"
    st = dg.State()

    first = _talk(st, "lên lịch trình du lịch cho tôi", "itinerary")
    assert first["status"] == "needs_clarification"
    assert "mấy ngày" in first["text"]
    assert first["suggestions"]

    details = (
        "Tôi du lịch ở Đà Nẵng, muốn đi Bà Nà và Sơn Trà, "
        "ăn mì Quảng sáng, uống cà phê, nghỉ trưa, đi cùng bạn gái"
    )
    followup = _talk(st, details, "weather", conf=0.35)
    assert followup["status"] == "needs_clarification"
    assert "mấy ngày" in followup["text"]
    assert st.slots["food_query"] == "mi quang"
    assert st.slots["cafe_requested"] is True
    assert st.slots["midday_rest"] is True
    assert st.slots["companion"] == "couple"
    assert 10 in st.requested_place_ids
    assert "son_tra" not in st.slots.get("zone", "")

    answer = _talk(st, "Lịch trình 2 ngày", "itinerary")
    planned_ids = {
        stop["id"]
        for day in st.plan
        for stop in day["stops"]
        if stop["kind"] == "visit"
    }
    assert answer["status"] == "completed"
    assert 10 in planned_ids
    bana_day = next(day for day in st.plan if 10 in day["attr_ids"])
    assert bana_day["attr_ids"] == [10]
    assert pl.duration(by_id[10]) == 300
    bana_stop = next(stop for stop in bana_day["stops"] if stop["id"] == 10)
    assert (bana_stop["start"], bana_stop["end"]) == ("08:00", "13:00")
    assert "hai bạn" in answer["text"]
    assert "Mì Quảng Bà Mua" in answer["text"]
    assert "cà phê" in answer["text"]
    assert "Nghỉ ngơi" in answer["text"]
    assert all(
        stop["id"] in by_id
        for day in st.plan
        for stop in day["stops"]
    )


def test_full_planning_and_early_bana_flow():
    if not model_ready():
        return
    places = install_fake_repo()
    by_id = {p.id: p for p in places}
    st = dg.State()
    _talk(st, "lên lịch trình", "itinerary")
    r = _talk(st, "2 ngày thích biển", "clarify_reply")
    assert len(st.plan) == 2 and "Ngày 1" in r["text"] and "phút" in r["text"]
    assert "latitude" not in r["text"].lower()

    r = _talk(st, "mình muốn đi Bà Nà từ sớm", "modify_itinerary")
    day = next(d for d in st.plan if any(s["id"] == 10 for s in d["stops"]))
    assert day["stops"][0]["id"] == 10 and day["stops"][0]["start"] == "08:00"
    assert "mở cửa lúc 08:00" in r["text"]
    for d in st.plan:                                    # mọi điểm vẫn nằm trong giờ mở cửa
        for s in d["stops"]:
            p = by_id[s["id"]]
            assert pl.to_min(s["start"]) >= pl.opens(p) and pl.to_min(s["end"]) <= pl.closes(p)


def test_add_breakfast_uses_early_open_place():
    if not model_ready():
        return
    places = install_fake_repo()
    by_id = {p.id: p for p in places}
    st = dg.State()
    _talk(st, "lên lịch trình", "itinerary")
    _talk(st, "2 ngày thích biển", "clarify_reply")
    _talk(st, "thêm bữa sáng ngày 1", "modify_itinerary")
    first = st.plan[0]["stops"][0]
    assert first["kind"] == "meal" and by_id[first["id"]].open_time <= "08:00"


def test_breakfast_search_filters_by_opening_hours():
    if not model_ready():
        return
    places = install_fake_repo()
    st = dg.State()
    r = _talk(st, "ăn sáng gần Mỹ Khê", "food")
    lines = [l for l in r["text"].splitlines() if l[:2] in {"1.", "2.", "3.", "4."}]
    assert lines, r["text"]
    names = {l.split(". ", 1)[1].split(" – ")[0] for l in lines}
    for p in places:
        if p.name in names:
            assert p.open_time <= "08:00", p.name


def test_remove_place_replans_day():
    if not model_ready():
        return
    install_fake_repo()
    st = dg.State()
    _talk(st, "lên lịch trình", "itinerary")
    _talk(st, "2 ngày thích biển", "clarify_reply")
    target = next(s for d in st.plan for s in d["stops"] if s["kind"] == "visit")
    _talk(st, f"bỏ {target['name']} khỏi lịch trình", "modify_itinerary")
    assert all(target["id"] != s["id"] for d in st.plan for s in d["stops"])


def test_greeting_and_unclear():
    if not model_ready():
        return
    install_fake_repo()
    st = dg.State()
    greeting = _talk(st, "xin chào", "greeting")
    assert "chào" in greeting["text"].casefold()
    unclear = _talk(dg.State(), "blah", "food", conf=0.2)
    assert "chưa chắc hiểu" in unclear["text"]
    assert unclear["status"] == "needs_clarification"
    assert unclear["suggestions"]


def test_long_place_takes_whole_day_and_others_are_moved():
    if not model_ready():
        return
    places = install_fake_repo()
    by_id = {p.id: p for p in places}
    st = dg.State()
    _talk(st, "lên lịch trình", "itinerary")
    _talk(st, "3 ngày thích biển", "clarify_reply")
    _talk(st, "mình muốn đi Bà Nà từ sớm", "modify_itinerary")
    day = next(d for d in st.plan if 10 in d["attr_ids"])
    assert day["attr_ids"] == [10], "ngày Bà Nà không còn điểm tham quan khác"
    visits = [s for s in day["stops"] if s["kind"] == "visit"]
    assert [s["id"] for s in visits] == [10]
    for d in st.plan:
        for s in d["stops"]:
            p = by_id[s["id"]]
            assert pl.to_min(s["start"]) >= pl.opens(p) and pl.to_min(s["end"]) <= pl.closes(p)
    # sau khi thêm bữa sáng vào ngày Bà Nà, Bà Nà vẫn còn trong lịch (không bị đẩy ra ngoài)
    _talk(st, f"thêm bữa sáng ngày {st.plan.index(day) + 1}", "modify_itinerary")
    assert any(s["id"] == 10 for s in st.plan[st.plan.index(day) if day in st.plan else 0]["stops"]) or \
        any(s["id"] == 10 for d in st.plan for s in d["stops"])
