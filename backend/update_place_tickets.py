
import sys
import unicodedata

from backend.database import SessionLocal, engine
from backend.models.place import Place


# ==========================================
# NGUON THAM KHAO
# ==========================================

CITY = (
    "https://danangfantasticity.com/en/tin-tuc/"
    "len-lich-kham-pha-da-nang-2026-cap-nhat-gia-ve-"
    "tham-quan-cac-diem-khu-du-lich"
)

HOIAN = (
    "https://danangfantasticity.com/cn/"
    "cap-nhat-ve-tham-quan-khu-pho-co-hoi-an-2026"
)


# ==========================================
# GIA VE / CHI PHI CUA 49 DIA DIEM
# Cau truc:
# "Ten dia diem": ("Thong tin gia", "URL nguon")
# ==========================================

TICKET_DATA = {

    # 1
    "Cầu Rồng": (
        "Miễn phí tham quan và xem trình diễn từ khu vực công cộng. "
        "Gửi xe và dịch vụ khác tính riêng.",
        None
    ),

    # 2
    "Bãi biển Mỹ Khê": (
        "Miễn phí vào bãi biển công cộng. "
        "Gửi xe, thuê ghế và các dịch vụ biển tính phí riêng.",
        None
    ),

    # 3
    "Ngũ Hành Sơn": (
        "Vé Thủy Sơn tham khảo 40.000đ/người lớn; "
        "Động Âm Phủ 20.000đ; thang máy 15.000đ/lượt. "
        "Cần xác nhận giá và chính sách miễn giảm.",
        CITY
    ),

    # 4
    "Bán đảo Sơn Trà": (
        "Không có vé vào cổng chung cho các khu vực công cộng "
        "được phép tham quan. Tuân thủ quy định bảo tồn và "
        "tuyến đường đang mở cửa.",
        None
    ),

    # 5
    "Bảo tàng Điêu khắc Chăm": (
        "Vé thường tham khảo 60.000đ/người. "
        "Một số đối tượng được giảm hoặc miễn phí "
        "theo chính sách áp dụng.",
        CITY
    ),

    # 6
    "Chợ Hàn": (
        "Không có vé vào chợ. "
        "Mua sắm và ăn uống thanh toán theo giá từng gian hàng.",
        None
    ),

    # 7
    "Cầu Tình Yêu": (
        "Miễn phí tham quan và chụp ảnh. "
        "Dịch vụ và vật phẩm mua thêm tính phí riêng.",
        None
    ),

    # 8
    "Đỉnh Bàn Cờ": (
        "Không có vé tham quan riêng theo thông tin tham khảo. "
        "Kiểm tra tình trạng tuyến đường và quy định tiếp cận Sơn Trà.",
        None
    ),

    # 9
    "Ghềnh Bàng": (
        "Chưa xác nhận vé vào cổng. "
        "Gửi xe máy tham khảo 5.000–10.000đ/xe. "
        "Không tự ý trekking vào các tuyến bị cấm.",
        "https://tixgo.vn/blog/da-nang/ghenh-bang-da-nang"
    ),

    # 10
    "Bãi Bụt": (
        "Miễn phí vé vào. Gửi xe máy khoảng 5.000đ, "
        "ô tô 15.000đ; thuê chòi 250.000–350.000đ. "
        "Các dịch vụ khác tính phí riêng. Giá tham khảo.",
        "https://vinpearl.com/vi/kham-pha-bai-but-da-nang-tron-ven-voi-bo-cam-nang-tu-a-z"
    ),

    # 11
    "Mũi Nghê": (
        "Chưa xác minh giá vé tham quan chính thức. "
        "Tour đường thủy được quảng bá khoảng "
        "450.000–650.000đ/người, cần kiểm tra giấy phép. "
        "Không trekking tự phát vào khu vực hạn chế.",
        "https://mia.vn/cam-nang-du-lich/mui-nghe-ban-dao-son-tra-19586"
    ),

    # 12
    "Hải đăng Tiên Sa": (
        "Một số nguồn tham khảo mức thu khoảng "
        "20.000đ/người. Chưa xác nhận giá chính thức "
        "và quyền tiếp cận hiện hành.",
        "https://daivietourist.vn/hai-dang-tien-sa-da-nang/"
    ),

    # 13
    "Nhất Lâm Thủy Trang Trà": (
        "Vé tham khảo 10.000đ/người; gửi xe máy "
        "khoảng 5.000đ. Ăn uống tính phí riêng. "
        "Cần xác nhận giá và tình trạng hoạt động.",
        "https://vinpearl.com/vi/nhat-lam-thuy-trang-tra-vung-non-xanh-nuoc-biec-khong-di-la-tiec"
    ),

    # 14
    "Cầu vòm Đồn Cả": (
        "Miễn phí tham quan. Gửi xe có thể phát sinh phí. "
        "Không đi vào đường ray hoặc hành lang đường sắt; "
        "chỉ ngắm cảnh từ vị trí an toàn.",
        "https://mia.vn/cam-nang-du-lich/cau-vom-don-ca-dep-tua-mot-thuoc-phim-ngoai-doi-that-8960"
    ),

    # 15
    "Thác Ba Đờ Phọt": (
        "Không có vé vào cổng theo nguồn tham khảo. "
        "Tự túc di chuyển, ăn uống và trang bị. "
        "Kiểm tra thời tiết và tuyến tiếp cận hợp lệ.",
        "https://tourdanangcity.vn/thac-ba-do-phot/"
    ),

    # 16
    "Hồ Hòa Trung": (
        "Miễn phí tham quan. Thuê thuyền tham khảo "
        "20.000–30.000đ/người; thuê lều khoảng "
        "200.000đ/lều. Giá tùy nhà cung cấp.",
        "https://vinpearl.com/vi/ho-hoa-trung-da-nang-diem-cam-trai-teambuilding-dinh-cua-chop"
    ),

    # 17
    "Giếng Trời": (
        "Không có vé vào cổng theo nguồn tham khảo. "
        "Tự túc đi lại và đồ bảo hộ. "
        "Kiểm tra thời tiết và quy định tiếp cận.",
        "https://daivietourist.vn/gieng-troi-da-nang/"
    ),

    # 18
    "Bãi Rạn Nam Ô": (
        "Không có vé tham quan bãi biển công cộng "
        "theo thông tin tham khảo. "
        "Gửi xe và dịch vụ khác có thể tính phí.",
        None
    ),

    # 19
    "Rừng thông Bồ Bồ": (
        "Vé tham khảo 20.000đ/người. "
        "Gửi xe máy khoảng 10.000đ, "
        "ô tô 30.000đ. Cần xác nhận mức thu thực tế.",
        "https://danangbest.com/rung-thong-bo-bo-chon-dung-chan-cua-nhung-ke-mong-mo.html"
    ),

    # 20
    "Thánh địa Mỹ Sơn": (
        "Vé tham khảo: khách Việt Nam 100.000đ/người; "
        "khách nước ngoài 150.000đ/người. "
        "Kiểm tra chính sách miễn giảm hiện hành.",
        CITY
    ),

    # 21
    "Công viên Văn hóa Ấn Tượng Hội An": (
        "Vé công viên tham khảo 100.000đ. "
        "Show Ký ức Hội An có vé riêng, "
        "giá tùy hạng ghế và chương trình.",
        CITY
    ),

    # 22
    "Sun World Bà Nà Hills và Cầu Vàng": (
        "Vé cáp treo người lớn ngoại tỉnh tham khảo "
        "1.000.000đ; trẻ em 100–140cm khoảng 800.000đ. "
        "Giá và ưu đãi thay đổi theo đối tượng, thời điểm.",
        CITY
    ),

    # 23
    "Chùa Linh Ứng Sơn Trà": (
        "Miễn phí vé vào chùa và tham quan. "
        "Gửi xe hoặc các dịch vụ khác có thể phát sinh phí.",
        None
    ),

    # 24
    "Bãi biển Non Nước": (
        "Miễn phí vào khu vực bãi biển công cộng. "
        "Các dịch vụ nghỉ dưỡng và tiện ích tính phí riêng.",
        None
    ),

    # 25
    "Nhà thờ Chính tòa Đà Nẵng": (
        "Không bán vé tham quan thông thường. "
        "Việc vào tham quan phụ thuộc giờ lễ và quy định nhà thờ.",
        None
    ),

    # 26
    "Làng đá mỹ nghệ Non Nước": (
        "Tham quan cửa hàng và làng nghề thường "
        "không có vé chung. Mua sản phẩm và "
        "trải nghiệm riêng có thể tính phí.",
        None
    ),

    # 27
    "Đèo Hải Vân": (
        "Không có vé tham quan chung khi ngắm cảnh "
        "trên các tuyến đường được phép. "
        "Chi phí di chuyển và dịch vụ tính riêng.",
        None
    ),

    # 28
    "Phố cổ Hội An": (
        "Gói vé tham quan di tích phố cổ tham khảo "
        "80.000đ hoặc 120.000đ tùy loại vé. "
        "Cần xác nhận phạm vi áp dụng và giá hiện hành.",
        HOIAN
    ),

    # 29
    "Chùa Cầu Hội An": (
        "Tham quan di tích theo quy định vé của phố cổ Hội An. "
        "Gói vé tham khảo 80.000đ hoặc 120.000đ. "
        "Chụp ảnh từ khu vực công cộng khác với vào di tích.",
        HOIAN
    ),

    # 30
    "Rừng dừa Bảy Mẫu": (
        "Vé tham quan khu vực rừng dừa tham khảo "
        "30.000đ/người. Thuyền thúng và "
        "dịch vụ trải nghiệm tính phí riêng.",
        CITY
    ),

    # 31
    "Biển An Bàng": (
        "Miễn phí vào bãi biển công cộng. "
        "Gửi xe, ăn uống và dịch vụ biển tính phí riêng.",
        None
    ),

    # 32
    "Làng gốm Thanh Hà": (
        "Vé tham quan làng gốm tham khảo "
        "35.000đ/người. Một số trải nghiệm "
        "có thể phát sinh chi phí.",
        CITY
    ),

    # 33
    "Làng rau Trà Quế": (
        "Vé tham quan làng rau tham khảo "
        "35.000đ/người. Lớp nấu ăn "
        "và trải nghiệm riêng tính phí thêm.",
        CITY
    ),

    # 34
    "Bánh xèo Bà Dưỡng": (
        "Không có vé vào cổng. "
        "Thanh toán món ăn và đồ uống theo thực đơn.",
        None
    ),

    # 35
    "Mì Quảng Bà Mua": (
        "Không có vé vào cổng. "
        "Thanh toán món ăn và đồ uống theo thực đơn.",
        None
    ),

    # 36
    "Bánh tráng cuốn thịt heo Trần": (
        "Không có vé vào cổng. "
        "Thanh toán món ăn và đồ uống theo thực đơn.",
        None
    ),

    # 37
    "Bún chả cá Nguyễn Chí Thanh": (
        "Không có vé vào cổng. "
        "Thanh toán món ăn và đồ uống theo thực đơn.",
        None
    ),

    # 38
    "Bánh mì Phượng": (
        "Không có vé vào cổng. "
        "Thanh toán bánh mì và đồ uống theo bảng giá.",
        None
    ),

    # 39
    "Cao lầu Thanh": (
        "Không có vé vào cổng. "
        "Thanh toán món ăn và đồ uống theo thực đơn.",
        None
    ),

    # 40
    "Cơm gà Bà Buội": (
        "Không có vé vào cổng. "
        "Thanh toán món ăn và đồ uống theo thực đơn.",
        None
    ),

    # 41
    "Cộng Cà Phê Bạch Đằng": (
        "Không có vé vào cổng thông thường. "
        "Thanh toán cà phê và đồ ăn theo thực đơn.",
        None
    ),

    # 42
    "Hội An Roastery": (
        "Không có vé vào cổng thông thường. "
        "Thanh toán đồ uống và bánh theo thực đơn.",
        None
    ),

    # 43
    "Faifo Coffee": (
        "Không có vé tham quan riêng được xác minh. "
        "Đồ uống và dịch vụ tính theo quy định của quán.",
        None
    ),

    # 44
    "Trình Cà Phê": (
        "Không có vé vào cổng thông thường. "
        "Thanh toán đồ uống theo thực đơn.",
        None
    ),

    # 45
    "Wonderlust Danang": (
        "Không có vé vào cổng thông thường. "
        "Thanh toán đồ uống và bánh theo thực đơn.",
        None
    ),

    # 46
    "Chợ Cồn": (
        "Không có vé vào chợ. "
        "Đồ ăn và hàng hóa thanh toán theo từng gian hàng.",
        None
    ),

    # 47
    "Chợ đêm Sơn Trà": (
        "Không có vé vào chợ đêm thông thường. "
        "Ăn uống và mua sắm tính tiền riêng.",
        None
    ),

    # 48
    "Chợ Hội An": (
        "Không có vé vào chợ để mua sắm. "
        "Ăn uống và mua hàng tính tiền riêng; "
        "di tích phố cổ có quy định vé khác.",
        None
    ),

    # 49
    "Chợ đêm Hội An": (
        "Không có vé vào chợ đêm thông thường. "
        "Đồ ăn, mua sắm và các dịch vụ khác tính phí riêng.",
        None
    ),

}


# ==========================================
# HAM XU LY
# ==========================================

def normalize_name(name):
    return unicodedata.normalize(
        "NFC",
        " ".join(name.strip().split())
    ).casefold()


def main():

    if engine.dialect.name != "mysql":
        raise RuntimeError("CHI CHO PHEP MYSQL!")

    if engine.url.database != "danang_guide":
        raise RuntimeError("SAI DATABASE!")

    if engine.url.host not in ("127.0.0.1", "localhost"):
        raise RuntimeError("CHI CHO PHEP MYSQL LOCAL!")

    if len(TICKET_DATA) != 49:
        raise RuntimeError(
            f"CAN 49 DIA DIEM, HIEN CO {len(TICKET_DATA)}"
        )

    apply_changes = "--apply" in sys.argv

    db = SessionLocal()

    try:
        places = db.query(Place).order_by(Place.id).all()

        if len(places) != 49:
            raise RuntimeError(
                f"MYSQL CO {len(places)} DIA DIEM, CAN KIEM TRA!"
            )

        database_places = {
            normalize_name(place.name): place
            for place in places
        }

        missing = [
            name
            for name in TICKET_DATA
            if normalize_name(name) not in database_places
        ]

        if missing:
            print("TEN KHONG KHOP:", missing)
            raise RuntimeError("CHUA CAP NHAT!")

        pending = []
        preserved = 0

        for name, (ticket_info, source_url) in TICKET_DATA.items():

            place = database_places[normalize_name(name)]

            # Giu nguyen gia ve da co trong MySQL
            if place.ticket_info:
                preserved += 1
                continue

            # Kiem tra chieu dai cot
            if len(ticket_info) > 255:
                raise RuntimeError(
                    "THONG TIN QUA DAI: " + name
                )

            if source_url and len(source_url) > 500:
                raise RuntimeError(
                    "LINK QUA DAI: " + name
                )

            pending.append((place, ticket_info, source_url))

            print("---------------------------------")
            print("DIA DIEM:", place.id, place.name)
            print("GIA VE:", ticket_info)

        print("---------------------------------")
        print("TONG DIA DIEM:", len(places))
        print("CAN CAP NHAT:", len(pending))
        print("DA CO GIA VE:", preserved)

        if not apply_changes:
            print("CHE DO XEM TRUOC - CHUA LUU MYSQL")
            return

        for place, ticket_info, source_url in pending:
            place.ticket_info = ticket_info
            place.ticket_source_url = source_url

        db.commit()

        print("CAP NHAT THANH CONG!")
        print("SO DIA DIEM VUA CAP NHAT:", len(pending))

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
