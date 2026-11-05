"""Chạy trọn các kịch bản hội thoại với dữ liệu giả lập. Cần đã huấn luyện slot_tagger.joblib."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import FakeDB, P, install_fake_repo  # noqa: E402

from backend.services import dialogue as dg  # noqa: E402
from backend.services import planner as pl  # noqa: E402
from backend.services.slot_service import extract_slots, model_ready  # noqa: E402


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


def test_food_request_with_trip_length_routes_to_itinerary():
    if not model_ready():
        return
    install_fake_repo()
    st = dg.State()
    progress = []
    response = _talk(
        st,
        "mình đi 2 ngày mình muốn thử mì quảng ở khu vực xung quanh hải châu vì mình ở gần đây",
        "food",
        conf=0.7176,
    )

    assert response["status"] == "completed"
    assert len(st.plan) == 2
    assert "Ngày 1" in response["text"]
    assert "Quanh Mì Quảng Bà Mua" not in response["text"]
    assert "Mì Quảng Bà Mua" in response["text"]
    assert any(
        stop["kind"] == "meal"
        for day in st.plan
        for stop in day["stops"]
    )

    planned = dg.State()
    response = dg.respond(
        planned,
        "mình đi 2 ngày mình muốn thử mì quảng ở khu vực xung quanh hải châu vì mình ở gần đây",
        "food",
        0.7176,
        FakeDB(),
        on_step=progress.append,
    )
    assert progress == response["steps"]
    assert any("tìm kiếm địa điểm" in step.casefold() for step in progress)
    assert any("truy cập cơ sở dữ liệu" in step.casefold() for step in progress)
    assert any("đang xếp lịch" in step.casefold() for step in progress)


def test_new_itinerary_request_asks_again_instead_of_reusing_previous_trip():
    if not model_ready():
        return
    install_fake_repo()
    st = dg.State()

    first = _talk(st, "Lịch trình 2 ngày thích biển", "itinerary")
    assert first["status"] == "completed"
    previous_plan = st.plan
    assert st.slots["interests"] == ["beach"]

    followup = _talk(st, "Lên lịch trình", "itinerary")

    assert followup["status"] == "needs_clarification"
    assert "mấy ngày" in followup["text"]
    assert st.pending_for == "itinerary"
    assert st.starting_new_itinerary is True
    assert st.plan is previous_plan
    assert not st.slots

    days = _talk(st, "3 ngày", "clarify_reply")
    assert days["status"] == "needs_clarification"
    assert "sở thích" in days["text"] or "thích hướng nào" in days["text"]
    assert st.starting_new_itinerary is True

    answer = _talk(st, "mình thích văn hóa", "clarify_reply")
    assert answer["status"] == "completed"
    assert len(st.plan) == 3
    assert st.starting_new_itinerary is False
    assert st.slots["interests"] == ["culture"]


def test_morning_only_slots_include_noon_cutoff_and_stop_count():
    slots, _ = extract_slots(
        "Lịch trình buổi sáng 1 ngày, đi 4 chỗ trước 12h trưa"
    )

    assert slots["days"] == 1
    assert slots["stops_per_day"] == 4
    assert slots["day_end"] == "12:00"
    assert "start_time" not in slots
    assert "people" not in slots


def test_morning_only_request_builds_four_stops_before_noon():
    if not model_ready():
        return
    places = [
        P(
            501 + index,
            f"Điểm trung tâm {index}",
            "tourist_attraction",
            "trung_tam",
            "07:00",
            "12:00",
            30,
        )
        for index in range(4)
    ]
    install_fake_repo(places)
    st = dg.State()

    response = _talk(
        st,
        "Lịch trình buổi sáng 1 ngày, đi 4 chỗ trước 12h trưa",
        "itinerary",
    )
    visits = [
        stop
        for day in st.plan
        for stop in day["stops"]
        if stop["kind"] == "visit"
    ]

    assert response["status"] == "completed"
    assert len(visits) == 4
    assert all(pl.to_min(stop["end"]) <= 12 * 60 for stop in visits)


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


def test_clear_cafe_request_replaces_stale_clarification():
    if not model_ready():
        return
    install_fake_repo()
    st = dg.State(pending="clarify_reply", pending_for="clarify_reply")

    answer = _talk(st, "Quán cà phê đẹp", "cafe")

    assert answer["status"] == "completed"
    assert any(
        name in answer["text"]
        for name in ("Trình Cà Phê", "Gió Biển Cafe", "Faifo Coffee Hội An")
    )
    assert st.pending_for is None


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
