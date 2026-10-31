import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import slot_service as ss  # noqa: E402


def test_value_parsers():
    assert ss._time("6h30") == {"start_time": "06:30"}
    assert ss._time("7 am") == {"start_time": "07:00"}
    assert ss._time("sáng sớm") == {"early": True}
    assert ss._budget("500k") == {"budget_vnd": 500000}
    assert ss._budget("1 triệu") == {"budget_vnd": 1000000}
    assert ss._budget("rẻ") == {"budget_level": "low"}
    assert ss._num("hai ngày") == 2 and ss._num("3 ngày 2 đêm") == 3


def test_tagger_if_trained():
    if not ss.model_ready():
        return          # chưa huấn luyện: bỏ qua (chạy train_slots.py trước)
    s, _ = ss.extract_slots("lịch trình 2 ngày thích biển")
    assert s.get("days") == 2 and "beach" in s.get("interests", [])
    s, _ = ss.extract_slots("thêm bữa sáng vào ngày 1")
    assert s.get("meal") == "breakfast" and "days" not in s      # "ngày 1" là thứ tự ngày, không phải số ngày
