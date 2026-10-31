import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.place_enrichment import best_time_for, duration_for, parse_hours, zone_of  # noqa: E402


def test_parse_hours():
    assert parse_hours("06:30 - 22:00") == ("06:30", "22:00")
    assert parse_hours("18:00 - 24:00") == ("18:00", "23:59")
    assert parse_hours("Cả ngày") == ("00:00", "23:59")
    assert parse_hours(None) == (None, None)


def test_zone_of_with_real_addresses():
    cases = [
        ("Bãi Biển Mỹ Khê", "Tuyến đường Võ Nguyên Giáp, Phường Phước Mỹ, Sơn Trà, Đà Nẵng", "son_tra"),
        ("Chùa Linh Ứng Bán đảo Sơn Trà", "Bán đảo Sơn Trà, Phường Thọ Quang, Quận Sơn Trà, Đà Nẵng", "son_tra_ban_dao"),
        ("Cầu Rồng Đà Nẵng", "Nối liền đường Nguyễn Văn Linh và Võ Văn Kiệt, Quận Hải Châu / Sơn Trà", "trung_tam"),
        ("Chợ Hàn", "Số 119 Trần Phú, Phường Hải Châu 1, Quận Hải Châu, Đà Nẵng", "trung_tam"),
        ("Cầu Vàng (Golden Bridge)", "Sun World Bà Nà Hills, Thôn An Sơn, Xã Hòa Ninh, Hòa Vang, Đà Nẵng", "ba_na"),
        ("Hồ Hòa Trung", "Xã Hòa Liên & Hòa Ninh, Huyện Hòa Vang, Đà Nẵng", "hoa_vang"),
        ("Phố cổ Hội An", "Trung tâm Phường Minh An, TP. Hội An, Quảng Nam", "hoi_an"),
        ("Cù Lao Chàm", "Xã Tân Hiệp, TP. Hội An, Quảng Nam", "cu_lao_cham"),
        ("Thánh địa Mỹ Sơn", "Xã Duy Phú, Huyện Duy Xuyên, Tỉnh Quảng Nam", "my_son"),
        ("Ngọn Thủy Sơn (Ngũ Hành Sơn)", "Số 81 Huyền Trân Công Chúa, Phường Hòa Hải, Ngũ Hành Sơn, Đà Nẵng", "ngu_hanh_son"),
        ("Chợ Hòa Khánh", "Đường Âu Cơ, Phường Hoà Khánh Bắc, Quận Liên Chiểu, Đà Nẵng", "lien_chieu"),
        ("Chợ Phước Tường", "Đường Trường Chinh, Phường Hòa Phát, Quận Cẩm Lệ, Đà Nẵng", "trung_tam"),
    ]
    for name, addr, want in cases:
        assert zone_of(name, addr) == want, (name, zone_of(name, addr), want)


def test_duration_and_best_time():
    assert duration_for("Bãi Biển Mỹ Khê", "tourist_attraction") == 120
    assert duration_for("Cù Lao Chàm", "tourist_attraction") == 480
    assert duration_for("Chùa Linh Ứng Bán đảo Sơn Trà", "tourist_attraction") == 45
    assert duration_for("Bán Đảo Sơn Trà", "tourist_attraction") == 180
    assert duration_for("Mì Quảng Bà Mua", "restaurant") == 60
    assert best_time_for("Cầu Rồng Đà Nẵng", "", "00:00", "tourist_attraction") == "night"
    assert best_time_for("Mũi Nghê", "Nơi đón ánh bình minh đầu tiên", "00:00", "tourist_attraction") == "morning"
    assert best_time_for("Show Ký Ức Hội An", "", "19:00", "tourist_attraction") == "night"
    assert best_time_for("Chợ đêm Helio", "", "17:30", "shopping") == "night"
