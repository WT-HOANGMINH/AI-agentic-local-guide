"""
Nap / cap nhat danh sach dia diem (Da Nang + Hoi An + My Son).

Chay tu THU MUC GOC cua repo:
    python -X utf8 -m backend.seed_places

- Cap nhat theo TEN dia diem: chay lai bao nhieu lan cung duoc, khong bi trung.
- Dia diem cu khong co trong danh sach nay se bi AN (is_active = False),
  khong bi xoa, nen lich trinh / yeu thich cu van khong bi loi khoa ngoai.
- Dia chi, gio mo cua va toa do duoi day la thong tin pho bien, CHUA kiem chung
  tung noi. Hay doi chieu Google Maps roi sua truc tiep trong file nay.
"""

from backend.database import Base, SessionLocal, engine
from backend.models.place import Place


def P(name, category, address, hours, description, lat, lng, price=2):
    return {
        "name": name,
        "category": category,
        "address": address,
        "opening_hours": hours,
        "description": description,
        "latitude": lat,
        "longitude": lng,
        "price_level": price,
        "is_active": True,
    }


ATTR = "tourist_attraction"

PLACES = [
    # ------------------------------------------------------------
    # DA NANG - THAM QUAN
    # ------------------------------------------------------------
    P("Cầu Rồng", ATTR,
      "Đường Nguyễn Văn Linh nối Võ Văn Kiệt, bắc qua sông Hàn, Đà Nẵng",
      "Mở cửa cả ngày; phun lửa và phun nước lúc 21:00 tối thứ Bảy và Chủ nhật",
      "Biểu tượng của Đà Nẵng với thân cầu hình rồng thép dài hơn 600 m, "
      "đẹp nhất về đêm khi lên đèn và trong màn phun lửa, phun nước cuối tuần.",
      16.0611, 108.2272, 1),
    P("Sun World Bà Nà Hills và Cầu Vàng", ATTR,
      "Khu du lịch Sun World Bà Nà Hills, Hòa Vang, Đà Nẵng (cách trung tâm khoảng 25 km)",
      "Khoảng 08:00 – 22:00 hằng ngày; giờ cáp treo thay đổi theo mùa",
      "Khu du lịch trên núi cao hơn 1.400 m với Cầu Vàng, Làng Pháp, vườn hoa "
      "và hệ thống cáp treo; khí hậu mát mẻ quanh năm.",
      15.9988, 107.9877, 4),
    P("Ngũ Hành Sơn", ATTR,
      "81 Huyền Trân Công Chúa, Hòa Hải, Ngũ Hành Sơn, Đà Nẵng",
      "07:00 – 17:30 hằng ngày",
      "Cụm năm ngọn núi đá vôi và cẩm thạch với nhiều hang động, chùa chiền "
      "như động Huyền Không, chùa Tam Thai; có thang máy và đường bộ lên núi.",
      16.0040, 108.2630, 1),
    P("Bán đảo Sơn Trà", ATTR,
      "Bán đảo Sơn Trà, Sơn Trà, Đà Nẵng (cách trung tâm khoảng 10 km)",
      "Mở cửa cả ngày; nên đi trong khoảng 05:00 – 17:30",
      "Khu rừng thiên nhiên ven biển với đường đèo uốn lượn ngắm biển, cây đa "
      "nghìn năm, đỉnh Bàn Cờ và là nơi sinh sống của loài voọc chà vá chân nâu.",
      16.1167, 108.2833, 1),
    P("Chùa Linh Ứng Sơn Trà", ATTR,
      "Bãi Bụt, bán đảo Sơn Trà, Sơn Trà, Đà Nẵng",
      "06:00 – 17:30 hằng ngày",
      "Ngôi chùa hướng ra biển với tượng Phật Bà Quan Âm cao 67 m, "
      "có tầm nhìn bao quát vịnh Đà Nẵng.",
      16.1002, 108.2758, 1),
    P("Bảo tàng Điêu khắc Chăm", ATTR,
      "02 Đường 2 Tháng 9, Hải Châu, Đà Nẵng",
      "07:00 – 17:00 hằng ngày",
      "Bảo tàng lưu giữ bộ sưu tập điêu khắc đá và đất nung Chăm Pa phong phú, "
      "niên đại từ khoảng thế kỷ 7 đến thế kỷ 15.",
      16.0603, 108.2233, 1),
    P("Bãi biển Mỹ Khê", ATTR,
      "Đường Võ Nguyên Giáp, Sơn Trà, Đà Nẵng",
      "Mở cửa cả ngày; thời điểm tắm biển đẹp 05:00 – 18:00",
      "Bãi biển cát trắng dài, nước trong, phù hợp tắm biển, thư giãn "
      "và ngắm bình minh.",
      16.0594, 108.2464, 1),
    P("Bãi biển Non Nước", ATTR,
      "Đường Huyền Trân Công Chúa, Ngũ Hành Sơn, Đà Nẵng",
      "Mở cửa cả ngày; thời điểm tắm biển đẹp 05:00 – 18:00",
      "Bãi cát dài yên tĩnh dưới chân Ngũ Hành Sơn, thường ít đông đúc hơn "
      "Mỹ Khê, hợp để thư giãn.",
      16.0004, 108.2696, 1),
    P("Nhà thờ Chính tòa Đà Nẵng", ATTR,
      "156 Trần Phú, Hải Châu, Đà Nẵng",
      "Tham quan bên ngoài cả ngày; vào bên trong theo giờ lễ",
      "Nhà thờ màu hồng kiến trúc Pháp với tháp chuông có con gà trên đỉnh, "
      "thường được gọi là nhà thờ Con Gà.",
      16.0670, 108.2237, 1),
    P("Làng đá mỹ nghệ Non Nước", ATTR,
      "Huyền Trân Công Chúa, Hòa Hải, Ngũ Hành Sơn, Đà Nẵng",
      "07:00 – 17:00 hằng ngày",
      "Làng nghề điêu khắc đá cẩm thạch lâu đời dưới chân Ngũ Hành Sơn, "
      "có thể xem nghệ nhân chế tác và mua quà lưu niệm.",
      16.0030, 108.2650, 1),
    P("Đèo Hải Vân", ATTR,
      "Đèo Hải Vân, Liên Chiểu, Đà Nẵng (tuyến nối Đà Nẵng – Huế)",
      "Mở cửa cả ngày; nên đi ban ngày khi trời quang",
      "Đèo nổi tiếng với cung đường ven biển ngoạn mục, mây phủ quanh năm "
      "và tầm nhìn bao quát vịnh Lăng Cô.",
      16.2005, 108.1280, 1),

    # ------------------------------------------------------------
    # HOI AN & MY SON
    # ------------------------------------------------------------
    P("Phố cổ Hội An", ATTR,
      "Khu phố cổ (Trần Phú – Nguyễn Thái Học – Bạch Đằng), Hội An, Đà Nẵng",
      "Đi dạo cả ngày; các điểm di tích mở khoảng 07:00 – 21:00 (cần vé tham quan)",
      "Di sản văn hóa thế giới UNESCO với nhà cổ, hội quán và đèn lồng; "
      "đẹp nhất vào buổi tối khi phố lên đèn.",
      15.8794, 108.3279, 2),
    P("Chùa Cầu Hội An", ATTR,
      "Giao đường Trần Phú và Nguyễn Thị Minh Khai, Hội An, Đà Nẵng",
      "07:00 – 21:00 hằng ngày (tính trong vé tham quan phố cổ)",
      "Cây cầu có mái che gắn với phố cổ Hội An, biểu tượng của thành phố "
      "và có mặt trên tờ tiền 20.000 đồng.",
      15.8774, 108.3262, 1),
    P("Rừng dừa Bảy Mẫu", ATTR,
      "Cẩm Thanh, Hội An, Đà Nẵng",
      "07:00 – 17:00 hằng ngày",
      "Rừng dừa nước ven sông Thu Bồn, nổi tiếng với trải nghiệm ngồi thúng "
      "chai và xem biểu diễn quay thúng.",
      15.8700, 108.3700, 2),
    P("Biển An Bàng", ATTR,
      "Cửa Đại, Hội An, Đà Nẵng",
      "Mở cửa cả ngày; thời điểm tắm biển đẹp 05:00 – 18:00",
      "Bãi biển yên tĩnh cách phố cổ khoảng 5 km, có nhiều quán ăn "
      "và ghế nghỉ ven biển.",
      15.9100, 108.3500, 1),
    P("Làng gốm Thanh Hà", ATTR,
      "Thanh Hà, Hội An, Đà Nẵng",
      "07:00 – 17:00 hằng ngày",
      "Làng nghề gốm hơn 500 năm tuổi, du khách có thể xem và tự tay "
      "nặn gốm.",
      15.8730, 108.3000, 2),
    P("Làng rau Trà Quế", ATTR,
      "Trà Quế, Hội An, Đà Nẵng",
      "07:00 – 17:00 hằng ngày",
      "Làng trồng rau hữu cơ, phù hợp đạp xe thư giãn và trải nghiệm "
      "làm nông dân, học nấu món Hội An.",
      15.9000, 108.3400, 2),
    P("Thánh địa Mỹ Sơn", ATTR,
      "Thánh địa Mỹ Sơn, Duy Phú, Đà Nẵng (cách Hội An khoảng 40 km)",
      "06:30 – 16:00 hằng ngày",
      "Quần thể đền tháp Chăm Pa trong thung lũng, được UNESCO công nhận "
      "là di sản văn hóa thế giới.",
      15.7640, 108.1230, 2),

    # ------------------------------------------------------------
    # AM THUC DA NANG
    # ------------------------------------------------------------
    P("Bánh xèo Bà Dưỡng", "restaurant",
      "K280/23 Hoàng Diệu, Hải Châu, Đà Nẵng",
      "10:00 – 21:00 hằng ngày",
      "Quán bánh xèo và nem lụi đặc trưng của ẩm thực Đà Nẵng, "
      "ăn kèm rau sống và nước chấm đậm đà.",
      16.0592, 108.2173, 2),
    P("Mì Quảng Bà Mua", "restaurant",
      "19 Trần Bình Trọng, Hải Châu, Đà Nẵng",
      "06:00 – 21:00 hằng ngày",
      "Quán mì Quảng lâu năm, món đặc sản miền Trung với sợi mì vàng, "
      "nước dùng ít và đậm vị.",
      16.0645, 108.2198, 1),
    P("Bánh tráng cuốn thịt heo Trần", "restaurant",
      "4 Lê Duẩn, Hải Châu, Đà Nẵng",
      "09:00 – 21:00 hằng ngày",
      "Quán bánh tráng cuốn thịt heo hai đầu da nổi tiếng, "
      "ăn kèm rau rừng và mắm nêm.",
      16.0712, 108.2205, 2),
    P("Bún chả cá Nguyễn Chí Thanh", "restaurant",
      "109 Nguyễn Chí Thanh, Hải Châu, Đà Nẵng",
      "06:30 – 20:00 hằng ngày",
      "Quán bún chả cá với nước dùng ngọt thanh từ xương và cá, "
      "món sáng quen thuộc của người Đà Nẵng.",
      16.0653, 108.2120, 1),

    # ------------------------------------------------------------
    # AM THUC HOI AN
    # ------------------------------------------------------------
    P("Bánh mì Phượng", "restaurant",
      "2B Phan Châu Trinh, Hội An, Đà Nẵng",
      "06:30 – 21:30 hằng ngày",
      "Tiệm bánh mì nổi tiếng của Hội An, nhân đầy đặn và nước sốt đặc trưng.",
      15.8770, 108.3290, 1),
    P("Cao lầu Thanh", "restaurant",
      "26 Thái Phiên, Hội An, Đà Nẵng",
      "07:00 – 21:00 hằng ngày",
      "Quán cao lầu – món đặc sản Hội An với sợi mì dai, thịt xíu, "
      "rau sống và tóp mỡ giòn.",
      15.8785, 108.3300, 2),
    P("Cơm gà Bà Buội", "restaurant",
      "22 Phan Chu Trinh, Hội An, Đà Nẵng",
      "10:00 – 21:00 hằng ngày",
      "Quán cơm gà Hội An với cơm nấu nước luộc gà, gà xé phay "
      "trộn rau răm và hành tây.",
      15.8790, 108.3270, 2),

    # ------------------------------------------------------------
    # CA PHE
    # ------------------------------------------------------------
    P("Cộng Cà Phê Bạch Đằng", "cafe",
      "96 Bạch Đằng, Hải Châu, Đà Nẵng",
      "07:00 – 23:00 hằng ngày",
      "Quán cà phê phong cách thời bao cấp, nổi tiếng với cà phê cốt dừa "
      "và không gian gần sông Hàn.",
      16.0698, 108.2243, 2),
    P("Hội An Roastery", "cafe",
      "135 Trần Phú, Hội An, Đà Nẵng",
      "07:00 – 22:00 hằng ngày",
      "Quán cà phê rang xay tại phố cổ Hội An, có nhiều lựa chọn cà phê "
      "Việt Nam và không gian mát mẻ.",
      15.8786, 108.3265, 2),
    P("Faifo Coffee", "cafe",
      "130 Trần Phú, Hội An, Đà Nẵng",
      "08:00 – 22:00 hằng ngày",
      "Quán cà phê có sân thượng nhìn ra các mái ngói phố cổ, "
      "phù hợp ngắm hoàng hôn.",
      15.8788, 108.3268, 2),

    # ------------------------------------------------------------
    # CHO / MUA SAM
    # ------------------------------------------------------------
    P("Chợ Hàn", "shopping",
      "119 Trần Phú, Hải Châu, Đà Nẵng",
      "06:00 – 19:00 hằng ngày",
      "Chợ truyền thống ở trung tâm, bán đặc sản, thực phẩm khô, "
      "vải vóc và quà lưu niệm.",
      16.0682, 108.2248, 2),
    P("Chợ Cồn", "shopping",
      "290 Hùng Vương, Hải Châu, Đà Nẵng",
      "05:30 – 19:00 hằng ngày",
      "Chợ lớn nhất Đà Nẵng với khu ẩm thực, hải sản tươi và đồ khô, "
      "giá thường mềm hơn chợ Hàn.",
      16.0680, 108.2140, 2),
    P("Chợ đêm Sơn Trà", "shopping",
      "Đường Mai Hắc Đế, Sơn Trà, Đà Nẵng",
      "18:00 – 23:00 hằng ngày",
      "Khu chợ đêm với gian hàng ẩm thực đường phố và quà lưu niệm.",
      16.0617, 108.2325, 2),
    P("Chợ Hội An", "shopping",
      "Trần Quý Cáp – Bạch Đằng, Hội An, Đà Nẵng",
      "05:00 – 18:00 hằng ngày",
      "Chợ trung tâm Hội An với trái cây, đặc sản, gia vị và các quán "
      "ăn bình dân.",
      15.8767, 108.3295, 2),
    P("Chợ đêm Hội An", "shopping",
      "Đường Nguyễn Hoàng, Hội An, Đà Nẵng (bên kia cầu An Hội)",
      "17:00 – 22:30 hằng ngày",
      "Chợ đêm với đèn lồng, đồ thủ công, quà lưu niệm và ẩm thực "
      "đường phố.",
      15.8790, 108.3310, 2),
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    added = updated = hidden = 0
    try:
        names = {p["name"] for p in PLACES}

        for data in PLACES:
            row = db.query(Place).filter(Place.name == data["name"]).first()
            if row:
                for key, value in data.items():
                    setattr(row, key, value)
                updated += 1
            else:
                db.add(Place(**data))
                added += 1

        # An cac dia diem cu (du lieu loi font / khong co trong danh sach)
        for row in db.query(Place).filter(Place.is_active == True).all():  # noqa: E712
            if row.name not in names:
                row.is_active = False
                hidden += 1

        db.commit()
        print(f"[Seed] added={added} updated={updated} hidden_old={hidden}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
