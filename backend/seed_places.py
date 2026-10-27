"""
Nap / cap nhat danh sach dia diem day du cho Da Nang + Hoi An + My Son.
Dong bo day du 21 dia diem duoc su dung boi Frontend (js/data.js, js/common.js)
cung toan bo cac nha hang, quan ca phe, cho dem va diem tham quan noi tieng.

Chay tu THU MUC GOC cua repo (da kich hoat venv):
    python -X utf8 -m backend.seed_places
"""

from sqlalchemy import inspect, text

from backend.database import Base, SessionLocal, engine
from backend.models.user import User
from backend.models.place import Place
from backend.models.preference import UserPreference
from backend.models.itinerary import Itinerary, ItineraryItem
from backend.models.favorite import Favorite


def ensure_place_detail_columns():
    """Bo sung cot chi tiet, giu nguyen du lieu cu."""

    existing = {
        column["name"]
        for column in inspect(engine).get_columns("places")
    }

    new_columns = {
        "activities": "JSON",
        "ticket_info": "VARCHAR(255)",
        "ticket_source_url": "VARCHAR(500)",
    }

    with engine.begin() as conn:
        for name, sql_type in new_columns.items():
            if name not in existing:
                conn.execute(
                    text(
                        f"ALTER TABLE places "
                        f"ADD COLUMN {name} {sql_type}"
                    )
                )
                print(f"[Migration] Added column: {name}")

def ensure_rating_column():
    """Them cot rating neu bang places chua co (MySQL va SQLite deu chay duoc)."""
    cols = [c["name"] for c in inspect(engine).get_columns("places")]
    if "rating" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE places ADD COLUMN rating FLOAT NULL"))
        print("[Seed] Da them cot rating vao bang places.")


def normalize_place_categories():
    """Chuyen cac nhan danh muc cu ve cac ma API dang su dung."""
    aliases = {
        "nhà hàng": "restaurant",
        "ẩm thực": "restaurant",
        "thiên nhiên": "tourist_attraction",
        "văn hóa": "tourist_attraction",
        "v?n hóa": "tourist_attraction",
        "tham quan": "tourist_attraction",
        "biển": "tourist_attraction",
        "cà phê": "cafe",
        "quán cà phê": "cafe",
        "mua sắm": "shopping",
    }
    updated = 0
    with engine.begin() as conn:
        for alias, category in aliases.items():
            result = conn.execute(
                text(
                    "UPDATE places SET category = :category "
                    "WHERE LOWER(TRIM(category)) = :alias"
                ),
                {"category": category, "alias": alias},
            )
            updated += max(result.rowcount, 0)

    if updated:
        print(f"[Migration] Normalized {updated} place categories.")


def P(name, category, address, hours, description, lat, lng, price=2, rating=None):
    return {
        "name": name,
        "category": category,
        "address": address,
        "opening_hours": hours,
        "description": description,
        "latitude": lat,
        "longitude": lng,
        "price_level": price,
        "rating": rating,
        "is_active": True,
    }


ATTR = "tourist_attraction"
REST = "restaurant"
CAFE = "cafe"
SHOP = "shopping"

PLACES = [
    # ============================================================
    # 21 ĐỊA ĐIỂM CHÍNH ĐỒNG BỘ 100% VỚI FRONTEND (FE DATA & IMAGES)
    # ============================================================
    P("Cầu Rồng", ATTR,
      "Đường Nguyễn Văn Linh nối Võ Văn Kiệt, Phước Ninh, Hải Châu, Đà Nẵng",
      "Mở cửa cả ngày; phun lửa và phun nước lúc 21:00 tối thứ Bảy và Chủ nhật",
      "Cây cầu biểu tượng bắc qua sông Hàn với thân rồng thép dài 666 m, nổi bật về đêm khi lên đèn và trong màn trình diễn phun lửa, phun nước cuối tuần.",
      16.0611, 108.2272, 1, 4.7),

    P("Bãi biển Mỹ Khê", ATTR,
      "Đường Võ Nguyên Giáp, Phước Mỹ, Sơn Trà, Đà Nẵng",
      "Mở cửa cả ngày; thời điểm tắm biển đẹp 05:00 – 18:00",
      "Bãi biển cát trắng mịn dài, sóng êm và làn nước trong xanh, từng được tạp chí Forbes vinh danh là một trong những bãi biển quyến rũ nhất hành tinh.",
      16.0594, 108.2464, 1, 4.8),

    P("Ngũ Hành Sơn", ATTR,
      "81 Huyền Trân Công Chúa, Hòa Hải, Ngũ Hành Sơn, Đà Nẵng",
      "07:00 – 17:30 hằng ngày",
      "Quần thể năm ngọn núi đá vôi mang tên ngũ hành (Kim, Mộc, Thủy, Hỏa, Thổ) với nhiều hang động huyền bí như động Huyền Không và các ngôi chùa cổ.",
      16.0040, 108.2630, 1, 4.7),

    P("Bán đảo Sơn Trà", ATTR,
      "Bán đảo Sơn Trà, Thọ Quang, Sơn Trà, Đà Nẵng",
      "Mở cửa cả ngày; thời điểm tham quan đẹp nhất 05:00 – 17:30",
      "Khu rừng tự nhiên ven biển với cung đường đèo ngắm biển tuyệt mỹ, đỉnh Bàn Cờ, cây đa nghìn năm và là nơi cư trú của loài voọc chà vá chân nâu quý hiếm.",
      16.1167, 108.2833, 1, 4.7),

    P("Bảo tàng Điêu khắc Chăm", ATTR,
      "02 Đường 2 Tháng 9, Bình Hiên, Hải Châu, Đà Nẵng",
      "07:00 – 17:00 hằng ngày",
      "Bảo tàng lưu giữ bộ sưu tập nghệ thuật điêu khắc sa thạch và đất nung Chăm Pa quy mô nhất thế giới, có niên đại từ thế kỷ 7 đến thế kỷ 15.",
      16.0603, 108.2233, 1, 4.6),

    P("Chợ Hàn", SHOP,
      "119 Trần Phú, Hải Châu 1, Hải Châu, Đà Nẵng",
      "06:00 – 19:00 hằng ngày",
      "Khu chợ truyền thống sầm uất ngay trung tâm thành phố với hàng trăm gian hàng đặc sản, hải sản khô, bánh mứt, vải may áo dài và quà lưu niệm Đà Nẵng.",
      16.0682, 108.2248, 2, 4.3),

    P("Cầu Tình Yêu", ATTR,
      "Đường Trần Hưng Đạo, An Hải Trung, Sơn Trà, Đà Nẵng",
      "Mở cửa cả ngày; đẹp và lãng mạn nhất vào buổi tối khi lên đèn",
      "Cây cầu đi dạo ven bờ đông sông Hàn nổi bật với các trụ đèn lồng hình trái tim đỏ rực, nơi các cặp đôi móc ổ khóa tình yêu và ngắm tượng Cá Chép Hóa Rồng.",
      16.0630, 108.2296, 1, 4.4),

    P("Đỉnh Bàn Cờ", ATTR,
      "Đỉnh núi Sơn Trà, Thọ Quang, Sơn Trà, Đà Nẵng",
      "06:00 – 18:00 hằng ngày",
      "Điểm cao nhất trên bán đảo Sơn Trà (gần 700 m so với mực nước biển), gắn với truyền thuyết bàn cờ tiên và tượng Đế Thích ngắm trọn cảnh sắc thành phố.",
      16.1180, 108.2760, 1, 4.6),

    P("Ghềnh Bàng", ATTR,
      "Bãi Bụt, Bán đảo Sơn Trà, Sơn Trà, Đà Nẵng",
      "Nên đi vào ban ngày khi thời tiết đẹp và biển êm (07:00 – 16:30)",
      "Bờ biển hoang sơ với những khối đá sẫm màu xếp lớp tự nhiên và rạn san hô gần bờ; phù hợp tham quan, cắm trại dã ngoại và trekking nhẹ.",
      16.1189, 108.3242, 1, 4.5),

    P("Bãi Bụt", ATTR,
      "Bán đảo Sơn Trà, Thọ Quang, Sơn Trà, Đà Nẵng",
      "Mở cửa cả ngày (06:00 – 18:00)",
      "Bãi biển êm đềm ở phía nam bán đảo Sơn Trà nằm dưới chân chùa Linh Ứng, phong cảnh thanh bình, nước trong vắt, thích hợp thư giãn và nghỉ mát.",
      16.1015, 108.2780, 1, 4.6),

    P("Mũi Nghê", ATTR,
      "Mũi phía đông bán đảo Sơn Trà, Thọ Quang, Sơn Trà, Đà Nẵng",
      "Khởi hành sớm để đón ánh bình minh đầu tiên của Đà Nẵng (05:00 – 10:00)",
      "Mũi đất hoang sơ ở cực đông Sơn Trà với hồ bơi tự nhiên giữa ghềnh đá và khung cảnh đón bình minh hùng vĩ; đường tiếp cận dốc và cần chuẩn bị kỹ.",
      16.11788, 108.33864, 1, 4.6),

    P("Hải đăng Tiên Sa", ATTR,
      "Bán đảo Sơn Trà, Thọ Quang, Sơn Trà, Đà Nẵng",
      "07:30 – 17:30 hằng ngày",
      "Ngọn hải đăng kiến trúc Pháp cổ kính xây dựng từ năm 1902 trên độ cao 223 m so với mực nước biển, điểm check-in và ngắm toàn cảnh biển trời bao la.",
      16.1362, 108.3185, 1, 4.4),

    P("Nhất Lâm Thủy Trang Trà", ATTR,
      "Bán đảo Sơn Trà, Thọ Quang, Sơn Trà, Đà Nẵng",
      "07:00 – 17:30 hằng ngày",
      "Khu du lịch sinh thái trong lành ẩn mình giữa rừng nguyên sinh Sơn Trà với suối Nai mát rượi và cây đa ngơ ngác nghìn năm tuổi rợp bóng mát.",
      16.1120, 108.2980, 1, 4.3),

    P("Cầu vòm Đồn Cả", ATTR,
      "Chân đèo Hải Vân, Thị trấn Lăng Cô giáp Liên Chiểu, Đà Nẵng",
      "07:00 – 17:30 hằng ngày; không đi vào lòng đường ray",
      "Cây cầu đường sắt vòm đá mang nét đẹp cổ tích phủ đầy rêu phong nằm lọt thỏm giữa hẻm núi đèo Hải Vân, điểm chụp ảnh và săn khoảnh khắc tàu hỏa đi qua.",
      16.2085, 108.1368, 1, 4.6),

    P("Thác Ba Đờ Phọt", ATTR,
      "Dãy núi Chúa, Xã Hòa Phú, Huyện Hòa Vang, Đà Nẵng",
      "06:30 – 16:00 (Nên đi mùa khô từ tháng 3 đến tháng 8)",
      "Quần thể thác nước nhiều tầng hoang sơ và hang đá tự nhiên trên núi Chúa, điểm đến lý tưởng cho những người đam mê phượt, trekking băng rừng.",
      15.9870, 107.9420, 1, 4.5),

    P("Hồ Hòa Trung", ATTR,
      "Xã Hòa Liên và Hòa Sơn, Huyện Hòa Vang, Đà Nẵng",
      "Mở cửa cả ngày (Đẹp nhất lúc bình minh 05:30 và hoàng hôn 16:30 – 18:00)",
      "Hồ nước nhân tạo được bao bọc bởi những hòn đảo nổi và đồng cỏ xanh ngắt như thảo nguyên Mông Cổ thu nhỏ, thích hợp cắm trại qua đêm và chèo thuyền kayak.",
      16.0825, 108.0850, 1, 4.5),

    P("Giếng Trời", ATTR,
      "Khu bảo tồn Bà Nà - Núi Chúa, Xã Hòa Ninh, Huyện Hòa Vang, Đà Nẵng",
      "06:00 – 16:00 (Nên trekking mùa khô, không đi vào mùa mưa lũ)",
      "Hồ nước tự nhiên trong vắt sâu thẳm giữa cánh rừng già với dòng thác trắng xóa đổ từ trên cao, tạo cảm giác như một chiếc giếng khổng lồ của tạo hóa.",
      15.9845, 107.9715, 1, 4.6),

    P("Bãi Rạn Nam Ô", ATTR,
      "Làng chài Nam Ô, Phường Hòa Hiệp Nam, Liên Chiểu, Đà Nẵng",
      "Mở cửa cả ngày (Mùa rêu xanh tuyệt đẹp từ tháng 1 đến tháng 3)",
      "Bãi đá ven biển trải dài với vô số tảng đá phủ rêu xanh ngọc bích khi thủy triều rút, nơi du khách có thể chụp ảnh check-in và thưởng thức gỏi cá Nam Ô nổi tiếng.",
      16.1265, 108.1350, 1, 4.5),

    P("Rừng thông Bồ Bồ", ATTR,
      "Xã Điện Tiến, Thị xã Điện Bàn, Quảng Nam (cách Đà Nẵng khoảng 22 km)",
      "07:30 – 17:30 hằng ngày",
      "Đồi thông xanh ngát trải dài trên triền đồi với không gian thanh bình mát mẻ, được ví như Đà Lạt thu nhỏ giữa lòng Quảng Nam - Đà Nẵng.",
      15.9220, 108.1580, 1, 4.4),

    P("Thánh địa Mỹ Sơn", ATTR,
      "Thôn Mỹ Sơn, Xã Duy Phú, Huyện Duy Xuyên, Quảng Nam (cách Đà Nẵng ~45 km)",
      "06:30 – 17:30 hằng ngày",
      "Quần thể di tích đền tháp Chăm Pa cổ xưa nằm giữa thung lũng khép kín, được UNESCO công nhận là Di sản Văn hóa Thế giới với kỹ thuật xây gạch không lộ mạch độc đáo.",
      15.7981, 108.1251, 2, 4.7),

    P("Công viên Văn hóa Ấn Tượng Hội An", ATTR,
      "Cồn Hến, Phường Cẩm Nam, Thành phố Hội An, Quảng Nam",
      "16:00 – 22:00 hằng ngày (Show diễn Ký Ức Hội An từ 20:00 – 21:00 các ngày trừ thứ Ba)",
      "Công viên chủ đề văn hóa sống động tái hiện ký ức thương cảng Hội An thế kỷ 16-17, với điểm nhấn là show diễn thực cảnh Ký Ức Hội An lớn nhất Việt Nam.",
      15.8775, 108.3375, 3, 4.8),

    # ============================================================
    # CÁC ĐỊA ĐIỂM THAM QUAN NỔI BẬT KHÁC (ĐÀ NẴNG & HỘI AN)
    # ============================================================
    P("Sun World Bà Nà Hills và Cầu Vàng", ATTR,
      "Thôn An Sơn, Xã Hòa Ninh, Hòa Vang, Đà Nẵng",
      "08:00 – 22:00 hằng ngày",
      "Khu du lịch trên đỉnh núi cao 1.487 m với biểu tượng Cầu Vàng nổi tiếng thế giới, Làng Pháp cổ kính và hệ thống cáp treo đạt nhiều kỷ lục Guinness.",
      15.9988, 107.9877, 4, 4.8),

    P("Chùa Linh Ứng Sơn Trà", ATTR,
      "Bãi Bụt, Bán đảo Sơn Trà, Sơn Trà, Đà Nẵng",
      "06:00 – 18:00 hằng ngày",
      "Ngôi chùa uy nghiêm tọa lạc trên bán đảo Sơn Trà với tượng Phật Bà Quan Âm cao 67 m hướng ra biển Đông, nơi ngắm trọn vịnh Đà Nẵng xinh đẹp.",
      16.1002, 108.2758, 1, 4.8),

    P("Bãi biển Non Nước", ATTR,
      "Đường Huyền Trân Công Chúa, Hòa Hải, Ngũ Hành Sơn, Đà Nẵng",
      "Mở cửa cả ngày",
      "Bãi cát trắng mịn thoai thoải và làn nước trong xanh ngay dưới chân Ngũ Hành Sơn, không gian êm đềm thích hợp tắm biển và nghỉ dưỡng.",
      16.0004, 108.2696, 1, 4.6),

    P("Nhà thờ Chính tòa Đà Nẵng", ATTR,
      "156 Trần Phú, Hải Châu 1, Hải Châu, Đà Nẵng",
      "Tham quan bên ngoài cả ngày; giờ lễ sáng và chiều",
      "Nhà thờ kiến trúc Gothic Pháp với gam màu hồng phấn độc đáo và cột thu lôi hình con gà trên đỉnh tháp chuông (thường gọi là nhà thờ Con Gà).",
      16.0670, 108.2237, 1, 4.5),

    P("Làng đá mỹ nghệ Non Nước", ATTR,
      "Huyền Trân Công Chúa, Hòa Hải, Ngũ Hành Sơn, Đà Nẵng",
      "07:00 – 17:30 hằng ngày",
      "Làng nghề truyền thống hơn 400 năm tuổi nổi tiếng với các tác phẩm tượng Phật, linh vật và đồ trang sức bằng đá cẩm thạch tinh xảo.",
      16.0030, 108.2650, 1, 4.5),

    P("Đèo Hải Vân", ATTR,
      "Đèo Hải Vân, Hòa Hiệp Bắc, Liên Chiểu, Đà Nẵng",
      "Mở cửa cả ngày; nên đi ban ngày khi trời nắng đẹp",
      "Thiên hạ đệ nhất hùng quan với những cung đường đèo uốn lượn ven biển ngoạn mục, đỉnh đèo có Hải Vân Quan nhìn bao quát vịnh Lăng Cô và Đà Nẵng.",
      16.2005, 108.1280, 1, 4.8),

    P("Phố cổ Hội An", ATTR,
      "Phường Minh An, Thành phố Hội An, Quảng Nam",
      "Đi dạo cả ngày; các điểm di tích mở cửa 07:00 – 21:00",
      "Di sản Văn hóa Thế giới UNESCO với những dãy nhà cổ tường vàng mái ngói rêu phong, hội quán người Hoa và hàng ngàn lồng đèn rực rỡ bên dòng sông Hoài.",
      15.8794, 108.3279, 2, 4.9),

    P("Chùa Cầu Hội An", ATTR,
      "Giao đường Trần Phú và Nguyễn Thị Minh Khai, Hội An, Quảng Nam",
      "07:00 – 21:00 hằng ngày",
      "Cây cầu gỗ cổ kính mái ngói mang đậm phong cách kiến trúc Nhật Bản, biểu tượng linh hồn của phố cổ Hội An và được in trên tờ tiền 20.000 đồng.",
      15.8774, 108.3262, 1, 4.7),

    P("Rừng dừa Bảy Mẫu", ATTR,
      "Thôn Vạn Lăng, Xã Cẩm Thanh, Hội An, Quảng Nam",
      "07:00 – 17:30 hằng ngày",
      "Vùng rừng dừa nước bạt ngàn miền Tây giữa lòng xứ Quảng, nổi tiếng với trải nghiệm chèo thuyền thúng, xem quăng chài và múa thúng điêu luyện.",
      15.8700, 108.3700, 2, 4.7),

    P("Biển An Bàng", ATTR,
      "Đường Hai Bà Trưng, Cẩm An, Hội An, Quảng Nam",
      "Mở cửa cả ngày",
      "Bãi biển tĩnh lặng nằm cách phố cổ Hội An khoảng 4 km với bãi cát trắng mịn, nhiều nhà hàng hải sản tươi sống và quán bar ven biển thoáng đãng.",
      15.9100, 108.3500, 1, 4.6),

    P("Làng gốm Thanh Hà", ATTR,
      "Đường Phạm Phán, Thanh Hà, Hội An, Quảng Nam",
      "08:00 – 17:30 hằng ngày",
      "Làng nghề gốm đất nung cổ truyền hơn 500 năm tuổi ven sông Thu Bồn, nơi du khách có thể tự tay tạo hình sản phẩm gốm cho riêng mình.",
      15.8730, 108.3000, 2, 4.5),

    P("Làng rau Trà Quế", ATTR,
      "Thôn Trà Quế, Cẩm Hà, Hội An, Quảng Nam",
      "07:00 – 17:30 hằng ngày",
      "Làng nông nghiệp hữu cơ truyền thống chuyên canh các loại rau thơm đặc sắc, thích hợp cho chuyến đạp xe khám phá đồng quê và học nấu ăn.",
      15.9000, 108.3400, 2, 4.6),

    # ============================================================
    # ẨM THỰC ĐẶC SẢN (ĐÀ NẴNG & HỘI AN)
    # ============================================================
    P("Bánh xèo Bà Dưỡng", REST,
      "K280/23 Hoàng Diệu, Bình Hiên, Hải Châu, Đà Nẵng",
      "09:30 – 21:30 hằng ngày",
      "Thương hiệu bánh xèo và nem lụi trứ danh Đà Nẵng, bánh xèo vỏ giòn rụm nhân tôm thịt tươi ngon, ăn kèm rau sống và nước chấm tương gan béo bùi độc quyền.",
      16.0592, 108.2173, 2, 4.4),

    P("Mì Quảng Bà Mua", REST,
      "19 Trần Bình Trọng, Phước Ninh, Hải Châu, Đà Nẵng",
      "06:00 – 21:30 hằng ngày",
      "Địa chỉ thưởng thức mì Quảng gia truyền nổi tiếng với sợi mì vàng dẻo dai, tôm thịt ếch gà đậm vị, nước dùng sánh ngọt và bánh tráng mè nướng giòn.",
      16.0645, 108.2198, 1, 4.3),

    P("Bánh tráng cuốn thịt heo Trần", REST,
      "4 Lê Duẩn, Hải Châu 1, Hải Châu, Đà Nẵng",
      "09:00 – 21:30 hằng ngày",
      "Thương hiệu ẩm thực nức tiếng với món thịt heo hai đầu da luộc mềm béo, cuộn bánh tráng Đại Lộc, đĩa rau rừng tươi mát và chấm mắm nêm thơm nồng.",
      16.0712, 108.2205, 2, 4.3),

    P("Bún chả cá Nguyễn Chí Thanh", REST,
      "109 Nguyễn Chí Thanh, Hải Châu 1, Hải Châu, Đà Nẵng",
      "06:00 – 21:00 hằng ngày",
      "Quán bún chả cá lâu năm đượm vị biển miền Trung với chả cá thu chiên và hấp dai ngọt, nước dùng nấu từ bí đỏ, thơm, cà chua ngọt dịu tự nhiên.",
      16.0653, 108.2120, 1, 4.3),

    P("Bánh mì Phượng", REST,
      "2B Phan Châu Trinh, Cẩm Châu, Hội An, Quảng Nam",
      "06:30 – 21:30 hằng ngày",
      "Tiệm bánh mì Hội An lừng danh khắp thế giới từng được cố đầu bếp Anthony Bourdain ngợi ca, nhân thập cẩm đầy đặn hòa quyện cùng nước sốt bí truyền.",
      15.8770, 108.3290, 1, 4.5),

    P("Cao lầu Thanh", REST,
      "26 Thái Phiên, Minh An, Hội An, Quảng Nam",
      "07:00 – 19:00 hằng ngày",
      "Quán cao lầu đậm chất truyền thống phố cổ Hội An với sợi mì vàng dai đặc trưng, thịt xíu thơm phức, tép mỡ giòn tan và rau thơm Trà Quế nồng nàn.",
      15.8785, 108.3300, 1, 4.5),

    P("Cơm gà Bà Buội", REST,
      "22 Phan Chu Trinh, Minh An, Hội An, Quảng Nam",
      "10:30 – 20:30 hằng ngày",
      "Thương hiệu cơm gà lâu đời bậc nhất Hội An, hạt cơm vàng ươm nấu từ nước luộc gà, thịt gà ta xé phay bóp gỏi rau răm giòn ngọt thơm lừng.",
      15.8790, 108.3270, 2, 4.4),

    # ============================================================
    # QUÁN CÀ PHÊ VIEW ĐẸP & CONCEPT ĐẶC SẮC
    # ============================================================
    P("Cộng Cà Phê Bạch Đằng", CAFE,
      "96 Bạch Đằng, Hải Châu 1, Hải Châu, Đà Nẵng",
      "07:00 – 23:00 hằng ngày",
      "Không gian hoài niệm thời bao cấp nhìn thẳng ra bờ sông Hàn thơ mộng, nổi tiếng nhất với món cà phê cốt dừa thơm béo và cốt dừa cacao mát lạnh.",
      16.0698, 108.2243, 2, 4.5),

    P("Hội An Roastery", CAFE,
      "135 Trần Phú, Minh An, Hội An, Quảng Nam",
      "07:00 – 22:00 hằng ngày",
      "Không gian rang xay cà phê mộc mạc giữa trung tâm phố cổ Hội An với hương thơm cà phê thơm nồng và kiến trúc gỗ truyền thống ấm cúng.",
      15.8786, 108.3265, 2, 4.5),

    P("Faifo Coffee", CAFE,
      "130 Trần Phú, Minh An, Hội An, Quảng Nam",
      "07:30 – 22:00 hằng ngày",
      "Quán cà phê sở hữu tầng thượng ngắm hoàng hôn và toàn cảnh mái ngói âm dương rêu phong tuyệt đẹp, điểm check-in không thể bỏ lỡ tại Hội An.",
      15.8788, 108.3268, 2, 4.4),

    P("Trình Cà Phê", CAFE,
      "22/4 Lê Đình Dương, Phước Ninh, Hải Châu, Đà Nẵng",
      "06:30 – 22:30 hằng ngày",
      "Quán cà phê mang phong cách sân vườn nhiệt đới xanh mát, mộc mạc và yên bình, nổi tiếng với món cà phê bơ béo ngậy độc đáo.",
      16.0625, 108.2190, 2, 4.6),

    P("Wonderlust Danang", CAFE,
      "96 Trần Phú, Hải Châu 1, Hải Châu, Đà Nẵng",
      "07:30 – 22:30 hằng ngày",
      "Tổ hợp cà phê concept phong cách tối giản hiện đại với mái vòm kính ngập tràn ánh sáng tự nhiên, trà bánh thơm ngon và góc sống ảo cực chất.",
      16.0691, 108.2235, 2, 4.5),

    # ============================================================
    # CHỢ TRUYỀN THỐNG & CHỢ ĐÊM
    # ============================================================
    P("Chợ Cồn", SHOP,
      "290 Hùng Vương, Vĩnh Trung, Hải Châu, Đà Nẵng",
      "05:30 – 19:30 hằng ngày",
      "Thiên đường ẩm thực đường phố và chợ đầu mối lớn nhất Đà Nẵng với hàng trăm quầy ốc hút, bánh bèo, bánh tráng kẹp và đặc sản miền Trung giá bình dân.",
      16.0680, 108.2140, 1, 4.4),

    P("Chợ đêm Sơn Trà", SHOP,
      "Đường Mai Hắc Đế, An Hải Tây, Sơn Trà, Đà Nẵng",
      "18:00 – 23:30 hằng ngày",
      "Chợ đêm náo nhiệt nằm sát chân cầu Rồng với hơn 150 gian hàng ẩm thực nướng, hải sản đường phố, đồ lưu niệm thủ công mỹ nghệ và áo thun du lịch.",
      16.0617, 108.2325, 2, 4.4),

    P("Chợ Hội An", SHOP,
      "Trần Quý Cáp – Bạch Đằng, Minh An, Hội An, Quảng Nam",
      "06:00 – 19:00 hằng ngày",
      "Khu chợ trung tâm sầm uất ven sông Hoài ngập tràn rau củ tươi ngon, gia vị miền Trung, hoa quả nhiệt đới và khu ẩm thực cao lầu, mì Quảng nức tiếng.",
      15.8767, 108.3295, 1, 4.4),

    P("Chợ đêm Hội An", SHOP,
      "Đường Nguyễn Hoàng, An Hội, Hội An, Quảng Nam",
      "17:00 – 23:00 hằng ngày",
      "Khu chợ đêm rực rỡ sắc màu bên kia sông Hoài với hàng chục quầy lồng đèn lấp lánh, đồ thủ công mỹ nghệ, đồ gốm và các món ăn vặt đường phố Hội An.",
      15.8790, 108.3310, 2, 4.5),
]


# Bản đồ đổi tên từ các bản ghi cũ lỗi font / tên dài sang tên chuẩn
RENAME_MAP = {
    "Cầu Rồng Đà Nẵng": "Cầu Rồng",
    "Bảo tàng Điêu khắc Chăm Đà Nẵng": "Bảo tàng Điêu khắc Chăm",
    "Chợ Hàn Đà Nẵng": "Chợ Hàn",
    "Sun World Bà Nà Hills & Cầu Vàng": "Sun World Bà Nà Hills và Cầu Vàng",
    "Chùa Linh Ứng - Bán Đảo Sơn Trà": "Chùa Linh Ứng Sơn Trà",
    "Bánh Xèo Tôm Nhảy Bà Dưỡng": "Bánh xèo Bà Dưỡng",
    "Trình Cà Phê - Không Gian Xanh & Vintage": "Trình Cà Phê",
    "Wonderlust Danang - Cà phê Concept": "Wonderlust Danang",
    "Chợ Đêm Sơn Trà": "Chợ đêm Sơn Trà",
}


def main():
    Base.metadata.create_all(bind=engine)
    ensure_rating_column()
    ensure_place_detail_columns()
    normalize_place_categories()

    db = SessionLocal()
    added = updated = hidden = 0
    try:
        # 1. Đổi tên các bản ghi cũ sang tên chuẩn để giữ nguyên ID và tránh trùng lặp
        for old_name, new_name in RENAME_MAP.items():
            existing = db.query(Place).filter(Place.name == old_name).first()
            if existing:
                conflict = db.query(Place).filter(Place.name == new_name).first()
                if not conflict or conflict.id == existing.id:
                    existing.name = new_name
                    db.commit()

        names = {p["name"] for p in PLACES}

        # 2. Cập nhật hoặc thêm mới địa điểm
        for data in PLACES:
            row = db.query(Place).filter(Place.name == data["name"]).first()
            if row:
                for key, value in data.items():
                    setattr(row, key, value)
                updated += 1
            else:
                db.add(Place(**data))
                added += 1

        # 3. Ẩn các địa điểm cũ không còn nằm trong danh sách chuẩn hóa
        for row in db.query(Place).filter(Place.is_active == True).all():
            if row.name not in names:
                row.is_active = False
                hidden += 1

        db.commit()
        print(f"[Seed] Done: added={added}, updated={updated}, hidden_old={hidden}")
        print(f"[Seed] Total active places: {db.query(Place).filter(Place.is_active == True).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
