"""Dữ liệu giả lập (không cần DB) mô phỏng bảng places của dự án, dùng cho kiểm thử."""
from dataclasses import dataclass


@dataclass
class P:
    id: int
    name: str
    category: str
    zone: str | None = None
    open_time: str | None = "00:00"
    close_time: str | None = "23:59"
    duration_min: int | None = None
    best_time: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    price_level: int | None = 2
    rating: float | None = None
    address: str = ""
    description: str = ""
    opening_hours: str | None = None
    is_active: bool = True


A = "tourist_attraction"


def make_places():
    return [
        # --- điểm tham quan ---
        P(1, "Bãi Biển Mỹ Khê", A, "son_tra", duration_min=120, best_time="morning", description="Bãi biển cát trắng sóng êm"),
        P(2, "Cầu Rồng Đà Nẵng", A, "trung_tam", duration_min=45, best_time="night", description="Biểu tượng phun lửa phun nước"),
        P(3, "Chợ Hàn", "shopping", "trung_tam", "06:00", "19:00", 60, description="Chợ du lịch đặc sản quà biếu"),
        P(4, "Bảo tàng Điêu khắc Chăm", A, "trung_tam", "07:30", "17:00", 90, description="Bảo tàng văn hóa Chăm"),
        P(5, "Chùa Linh Ứng Bán đảo Sơn Trà", A, "son_tra_ban_dao", "06:00", "21:00", 45, "morning", description="Tượng Quan Thế Âm hướng biển"),
        P(6, "Bán đảo Sơn Trà", A, "son_tra_ban_dao", duration_min=180, best_time="morning", description="Rừng nhiệt đới thiên nhiên"),
        P(7, "Bãi Bụt Sơn Trà", A, "son_tra_ban_dao", duration_min=120, best_time="morning", description="Bãi biển ngắm chùa từ dưới biển"),
        P(8, "Ngũ Hành Sơn", A, "ngu_hanh_son", "07:00", "17:30", 90, "morning", description="Danh thắng núi đá vôi tâm linh"),
        P(9, "Bãi Biển Non Nước", A, "ngu_hanh_son", duration_min=120, best_time="morning", description="Bãi biển dưới chân núi"),
        P(10, "Sun World Bà Nà Hills (Cầu Vàng, Làng Pháp, Chùa Linh Ứng)", A, "ba_na", "08:00", "17:00", 300, "morning",
          price_level=4, description="Khu du lịch trên núi Cầu Vàng Làng Pháp. Vé cáp treo Bà Nà: 900.000 VNĐ"),
        P(11, "Phố cổ Hội An", A, "hoi_an", duration_min=180, description="Di sản văn hóa thế giới UNESCO"),
        P(12, "Chùa Cầu Hội An", A, "hoi_an", "07:00", "21:00", 45, description="Biểu tượng kiến trúc Nhật Bản"),
        P(13, "Nhà cổ Tấn Ký", A, "hoi_an", "08:00", "17:30", 45, description="Nhà cổ hơn 200 năm"),
        P(14, "Chợ đêm Sơn Trà", "shopping", "son_tra", "18:00", "23:59", 90, "night", description="Chợ đêm quà lưu niệm đồ ăn vặt"),
        P(15, "Suối Hoa", A, "hoa_vang", "07:00", "17:30", 120, description="Sinh thái suối nước hoa ngập tràn thiên nhiên"),
        P(16, "Đỉnh Bàn Cờ", A, "son_tra_ban_dao", "06:00", "18:00", 45, "morning", description="Đỉnh núi ngắm toàn cảnh thành phố"),
        # --- nhà hàng ---
        P(20, "Mì Quảng Bà Mua", "restaurant", "trung_tam", "06:00", "22:00", price_level=1, description="Mì Quảng truyền thống"),
        P(21, "Bánh xèo Bà Dưỡng", "restaurant", "trung_tam", "10:00", "21:30", price_level=1, description="Bánh xèo nem lụi"),
        P(22, "Hải sản Mỹ Hạnh", "restaurant", "son_tra", "09:00", "23:00", price_level=3, description="Hải sản tươi sống ven biển Mỹ Khê"),
        P(23, "Bún chả cá Bà Lan", "restaurant", "son_tra", "06:00", "21:00", price_level=1, description="Bún chả cá ăn sáng"),
        P(24, "Quán ăn sáng Bánh mì Phượng Sơn Trà", "restaurant", "son_tra", "05:30", "20:00", price_level=1, description="Bánh mì phở xôi ăn sáng"),
        P(25, "Hải sản Thời Cũ", "restaurant", "ngu_hanh_son", "10:00", "23:00", price_level=2, description="Quán hải sản đồng giá"),
        P(26, "Bánh mì Phượng Hội An", "restaurant", "hoi_an", "06:00", "21:30", price_level=1, description="Tiệm bánh mì nổi tiếng"),
        P(27, "Cơm gà bà Buội", "restaurant", "hoi_an", "10:30", "19:00", price_level=2, description="Cơm gà Hội An"),
        P(28, "Nhà hàng Bé Mặn Hải Sản", "restaurant", "son_tra", "09:00", "23:00", price_level=2, description="Hải sản bình dân"),
        P(29, "Quán cơm Ba Na", "restaurant", "ba_na", "10:00", "16:00", price_level=3, description="Quán ăn trên khu du lịch"),
        # --- cà phê ---
        P(40, "Trình Cà Phê", "cafe", "trung_tam", "06:30", "22:00", description="Cà phê bố cục chill mộc mạc"),
        P(41, "Gió Biển Cafe", "cafe", "son_tra_ban_dao", "06:00", "22:00", description="Quán cafe gió biển ngắm vịnh"),
        P(42, "Faifo Coffee Hội An", "cafe", "hoi_an", "08:00", "21:30", description="Sân thượng ngắm mái nhà cổ"),
    ]


class FakeDB:
    """Chỉ cần là một đối tượng bất kỳ: các hàm truy cập dữ liệu được thay bằng place_repo giả."""


def install_fake_repo(places=None):
    from backend.services import place_repo, ranker
    places = places or make_places()
    by_id = {p.id: p for p in places}
    place_repo.all_active = lambda db: [p for p in places if p.is_active]
    place_repo.by_ids = lambda db, ids: [by_id[i] for i in ids if i in by_id]
    place_repo.get = lambda db, pid: by_id.get(pid)
    place_repo.restaurants = lambda db: [p for p in places if p.category == "restaurant" and p.is_active]
    ranker._cache.update(key=None, ranker=None)
    return places
