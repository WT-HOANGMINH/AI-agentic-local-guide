
import sys
import unicodedata

from backend.database import SessionLocal, engine
from backend.models.place import Place


# ==================================================
# HOAT DONG PHU HOP CHO 49 DIA DIEM DANANG GUIDE
# ==================================================

ACTIVITIES = {

    # 1. CAU RONG
    "Cầu Rồng": [
        "Tham quan",
        "Chụp ảnh",
        "Ngắm cảnh đêm",
        "Xem trình diễn phun lửa và phun nước",
    ],

    # 2. BAI BIEN MY KHE
    "Bãi biển Mỹ Khê": [
        "Tắm biển tại khu vực được phép",
        "Dạo biển",
        "Ngắm bình minh",
        "Chụp ảnh",
        "Thư giãn bên bờ biển",
    ],

    # 3. NGU HANH SON
    "Ngũ Hành Sơn": [
        "Tham quan danh thắng",
        "Khám phá hang động",
        "Viếng chùa",
        "Tìm hiểu lịch sử và văn hóa",
        "Ngắm cảnh từ trên cao",
    ],

    # 4. BAN DAO SON TRA
    "Bán đảo Sơn Trà": [
        "Tham quan thiên nhiên",
        "Ngắm cảnh biển",
        "Chụp ảnh phong cảnh",
        "Quan sát động vật hoang dã từ xa",
        "Khám phá các điểm ngắm cảnh",
    ],

    # 5. BAO TANG CHAM
    "Bảo tàng Điêu khắc Chăm": [
        "Tham quan bảo tàng",
        "Tìm hiểu văn hóa Chăm Pa",
        "Chiêm ngưỡng hiện vật cổ",
        "Khám phá nghệ thuật điêu khắc",
        "Học hỏi lịch sử địa phương",
    ],

    # 6. CHO HAN
    "Chợ Hàn": [
        "Mua sắm đặc sản Đà Nẵng",
        "Mua quà lưu niệm",
        "Khám phá chợ truyền thống",
        "Thưởng thức ẩm thực địa phương",
    ],

    # 7. CAU TINH YEU
    "Cầu Tình Yêu": [
        "Dạo bộ ven sông Hàn",
        "Chụp ảnh",
        "Ngắm cảnh đêm",
        "Ngắm tượng Cá Chép Hóa Rồng",
        "Trải nghiệm không gian lãng mạn",
    ],

    # 8. DINH BAN CO
    "Đỉnh Bàn Cờ": [
        "Ngắm toàn cảnh Đà Nẵng",
        "Chụp ảnh phong cảnh",
        "Tham quan tượng Đế Thích",
        "Khám phá cảnh quan Sơn Trà",
    ],

    # 9. GHENH BANG
    "Ghềnh Bàng": [
        "Khám phá bãi đá tự nhiên",
        "Chụp ảnh phong cảnh biển",
        "Dã ngoại",
        "Trekking nhẹ",
        "Quan sát cảnh biển và rạn san hô từ bờ",
    ],

    # 10. BAI BUT
    "Bãi Bụt": [
        "Dạo biển",
        "Ngắm cảnh",
        "Chụp ảnh",
        "Thư giãn",
        "Tắm biển tại khu vực an toàn",
    ],

    # 11. MUI NGHE
    "Mũi Nghê": [
        "Ngắm bình minh",
        "Chụp ảnh thiên nhiên",
        "Trekking khám phá",
        "Ngắm cảnh biển từ ghềnh đá",
    ],

    # 12. HAI DANG TIEN SA
    "Hải đăng Tiên Sa": [
        "Tham quan hải đăng",
        "Chụp ảnh kiến trúc",
        "Ngắm toàn cảnh biển",
        "Khám phá cảnh quan bán đảo Sơn Trà",
    ],

    # 13. NHAT LAM THUY TRANG TRA
    "Nhất Lâm Thủy Trang Trà": [
        "Tham quan khu sinh thái",
        "Khám phá suối Nai",
        "Ngắm cây cổ thụ",
        "Dạo bộ giữa thiên nhiên",
        "Chụp ảnh phong cảnh",
    ],

    # 14. CAU VOM DON CA
    "Cầu vòm Đồn Cả": [
        "Ngắm kiến trúc cầu vòm",
        "Chụp ảnh phong cảnh",
        "Khám phá cảnh quan đèo Hải Vân",
        "Quan sát tàu hỏa từ vị trí an toàn",
    ],

    # 15. THAC BA DO PHOT
    "Thác Ba Đờ Phọt": [
        "Trekking",
        "Khám phá thác nước",
        "Ngắm cảnh rừng núi",
        "Chụp ảnh thiên nhiên",
        "Dã ngoại khi điều kiện cho phép",
    ],

    # 16. HO HOA TRUNG
    "Hồ Hòa Trung": [
        "Cắm trại khi được phép",
        "Dã ngoại",
        "Ngắm bình minh",
        "Ngắm hoàng hôn",
        "Chụp ảnh đồng cỏ",
        "Chèo kayak khi có điều kiện an toàn",
    ],

    # 17. GIENG TROI
    "Giếng Trời": [
        "Trekking rừng",
        "Khám phá thác nước",
        "Ngắm cảnh thiên nhiên",
        "Chụp ảnh phong cảnh",
        "Dã ngoại khi thời tiết an toàn",
    ],

    # 18. BAI RAN NAM O
    "Bãi Rạn Nam Ô": [
        "Ngắm bãi đá phủ rêu",
        "Chụp ảnh",
        "Dạo biển",
        "Ngắm bình minh",
        "Thưởng thức gỏi cá Nam Ô",
    ],

    # 19. RUNG THONG BO BO
    "Rừng thông Bồ Bồ": [
        "Dạo bộ trong rừng thông",
        "Dã ngoại",
        "Chụp ảnh",
        "Ngắm cảnh đồi núi",
        "Thư giãn giữa thiên nhiên",
    ],

    # 20. THANH DIA MY SON
    "Thánh địa Mỹ Sơn": [
        "Tham quan di tích",
        "Khám phá đền tháp Chăm",
        "Tìm hiểu lịch sử Chăm Pa",
        "Chụp ảnh kiến trúc cổ",
        "Tìm hiểu di sản văn hóa UNESCO",
    ],

    # 21. CONG VIEN AN TUONG HOI AN
    "Công viên Văn hóa Ấn Tượng Hội An": [
        "Tham quan công viên văn hóa",
        "Khám phá không gian Hội An xưa",
        "Chụp ảnh",
        "Xem chương trình biểu diễn",
        "Trải nghiệm văn hóa truyền thống",
    ],

    # 22. BA NA HILLS
    "Sun World Bà Nà Hills và Cầu Vàng": [
        "Đi cáp treo",
        "Tham quan Cầu Vàng",
        "Khám phá Làng Pháp",
        "Chụp ảnh",
        "Ngắm cảnh núi Bà Nà",
        "Trải nghiệm khu vui chơi",
    ],

    # 23. CHUA LINH UNG SON TRA
    "Chùa Linh Ứng Sơn Trà": [
        "Viếng chùa",
        "Chiêm ngưỡng tượng Phật Bà Quan Âm",
        "Tham quan kiến trúc tâm linh",
        "Ngắm toàn cảnh biển Đà Nẵng",
        "Chụp ảnh phong cảnh",
    ],

    # 24. BAI BIEN NON NUOC
    "Bãi biển Non Nước": [
        "Tắm biển tại khu vực được phép",
        "Dạo biển",
        "Nghỉ dưỡng",
        "Ngắm bình minh",
        "Chụp ảnh",
    ],

    # 25. NHA THO CHINH TOA
    "Nhà thờ Chính tòa Đà Nẵng": [
        "Tham quan kiến trúc Gothic",
        "Chụp ảnh bên ngoài nhà thờ",
        "Tìm hiểu lịch sử nhà thờ",
        "Khám phá công trình tôn giáo",
    ],

    # 26. LANG DA NON NUOC
    "Làng đá mỹ nghệ Non Nước": [
        "Tham quan làng nghề",
        "Chiêm ngưỡng tác phẩm điêu khắc đá",
        "Tìm hiểu nghề chế tác đá",
        "Mua sản phẩm thủ công mỹ nghệ",
        "Chụp ảnh",
    ],

    # 27. DEO HAI VAN
    "Đèo Hải Vân": [
        "Ngắm cảnh núi và biển",
        "Tham quan Hải Vân Quan",
        "Chụp ảnh phong cảnh",
        "Khám phá các điểm ngắm cảnh",
    ],

    # 28. PHO CO HOI AN
    "Phố cổ Hội An": [
        "Dạo bộ phố cổ",
        "Ngắm đèn lồng",
        "Tham quan nhà cổ",
        "Tìm hiểu văn hóa Hội An",
        "Thưởng thức đặc sản địa phương",
        "Chụp ảnh kiến trúc",
    ],

    # 29. CHUA CAU HOI AN
    "Chùa Cầu Hội An": [
        "Tham quan công trình di tích",
        "Chụp ảnh",
        "Tìm hiểu kiến trúc Nhật Bản",
        "Khám phá lịch sử Hội An",
    ],

    # 30. RUNG DUA BAY MAU
    "Rừng dừa Bảy Mẫu": [
        "Đi thuyền thúng",
        "Khám phá rừng dừa nước",
        "Xem biểu diễn múa thúng",
        "Quan sát hoạt động quăng chài",
        "Chụp ảnh",
    ],

    # 31. BIEN AN BANG
    "Biển An Bàng": [
        "Tắm biển tại khu vực được phép",
        "Dạo biển",
        "Ngắm bình minh",
        "Thư giãn",
        "Thưởng thức hải sản ven biển",
    ],

    # 32. LANG GOM THANH HA
    "Làng gốm Thanh Hà": [
        "Tham quan làng gốm",
        "Trải nghiệm làm gốm",
        "Tìm hiểu nghề thủ công truyền thống",
        "Mua sản phẩm gốm",
        "Chụp ảnh",
    ],

    # 33. LANG RAU TRA QUE
    "Làng rau Trà Quế": [
        "Tham quan vườn rau",
        "Trải nghiệm trồng rau",
        "Đạp xe khám phá làng quê",
        "Tìm hiểu nông nghiệp truyền thống",
        "Tham gia lớp nấu ăn khi có tổ chức",
    ],

    # 34. BANH XEO BA DUONG
    "Bánh xèo Bà Dưỡng": [
        "Thưởng thức bánh xèo",
        "Thưởng thức nem lụi",
        "Khám phá ẩm thực Đà Nẵng",
        "Trải nghiệm món ăn địa phương",
    ],

    # 35. MI QUANG BA MUA
    "Mì Quảng Bà Mua": [
        "Thưởng thức mì Quảng",
        "Khám phá ẩm thực miền Trung",
        "Trải nghiệm món ăn truyền thống",
    ],

    # 36. BANH TRANG CUON THIT HEO TRAN
    "Bánh tráng cuốn thịt heo Trần": [
        "Thưởng thức bánh tráng cuốn thịt heo",
        "Thưởng thức mắm nêm",
        "Khám phá ẩm thực Đà Nẵng",
        "Trải nghiệm món ăn truyền thống",
    ],

    # 37. BUN CHA CA NGUYEN CHI THANH
    "Bún chả cá Nguyễn Chí Thanh": [
        "Thưởng thức bún chả cá",
        "Khám phá đặc sản miền Trung",
        "Trải nghiệm ẩm thực địa phương",
    ],

    # 38. BANH MI PHUONG
    "Bánh mì Phượng": [
        "Thưởng thức bánh mì Hội An",
        "Khám phá ẩm thực đường phố",
        "Trải nghiệm đặc sản địa phương",
    ],

    # 39. CAO LAU THANH
    "Cao lầu Thanh": [
        "Thưởng thức cao lầu",
        "Khám phá ẩm thực Hội An",
        "Trải nghiệm món ăn truyền thống",
    ],

    # 40. COM GA BA BUOI
    "Cơm gà Bà Buội": [
        "Thưởng thức cơm gà Hội An",
        "Khám phá đặc sản Hội An",
        "Trải nghiệm ẩm thực truyền thống",
    ],

    # 41. CONG CA PHE
    "Cộng Cà Phê Bạch Đằng": [
        "Thưởng thức cà phê cốt dừa",
        "Ngắm cảnh sông Hàn",
        "Thư giãn",
        "Chụp ảnh không gian hoài cổ",
    ],

    # 42. HOI AN ROASTERY
    "Hội An Roastery": [
        "Thưởng thức cà phê",
        "Khám phá không gian rang xay",
        "Thư giãn",
        "Chụp ảnh kiến trúc truyền thống",
    ],

    # 43. FAIFO COFFEE
    "Faifo Coffee": [
        "Thưởng thức cà phê",
        "Ngắm toàn cảnh phố cổ Hội An",
        "Chụp ảnh từ sân thượng",
        "Ngắm hoàng hôn",
        "Thư giãn",
    ],

    # 44. TRINH CA PHE
    "Trình Cà Phê": [
        "Thưởng thức cà phê bơ",
        "Thư giãn trong không gian sân vườn",
        "Gặp gỡ bạn bè",
        "Chụp ảnh",
    ],

    # 45. WONDERLUST DANANG
    "Wonderlust Danang": [
        "Thưởng thức cà phê",
        "Thưởng thức trà và bánh",
        "Chụp ảnh không gian hiện đại",
        "Gặp gỡ bạn bè",
        "Thư giãn",
    ],

    # 46. CHO CON
    "Chợ Cồn": [
        "Khám phá ẩm thực đường phố",
        "Thưởng thức đặc sản Đà Nẵng",
        "Mua sắm",
        "Khám phá chợ truyền thống",
    ],

    # 47. CHO DEM SON TRA
    "Chợ đêm Sơn Trà": [
        "Khám phá chợ đêm",
        "Thưởng thức ẩm thực đường phố",
        "Mua quà lưu niệm",
        "Mua sắm đồ thủ công",
        "Dạo chơi buổi tối",
    ],

    # 48. CHO HOI AN
    "Chợ Hội An": [
        "Khám phá chợ truyền thống",
        "Thưởng thức ẩm thực Hội An",
        "Mua đặc sản địa phương",
        "Mua sắm",
        "Tìm hiểu văn hóa địa phương",
    ],

    # 49. CHO DEM HOI AN
    "Chợ đêm Hội An": [
        "Dạo chợ đêm",
        "Ngắm đèn lồng",
        "Mua đồ thủ công mỹ nghệ",
        "Thưởng thức món ăn đường phố",
        "Chụp ảnh",
    ],

}


# ==================================================
# KIEM TRA VA CAP NHAT MYSQL
# ==================================================

def normalize_name(value):
    return unicodedata.normalize("NFC", value.strip())


def main():

    # Khong cho phep sua SQLite hay Neon
    if engine.dialect.name != "mysql":
        raise RuntimeError("CHI CHO PHEP MYSQL LOCAL!")

    if engine.url.database != "danang_guide":
        raise RuntimeError("SAI DATABASE!")

    if engine.url.host not in ("127.0.0.1", "localhost"):
        raise RuntimeError("CHI CHO PHEP MYSQL TREN MAY!")

    if len(ACTIVITIES) != 49:
        raise RuntimeError("DANH SACH KHONG DU 49 DIA DIEM!")

    apply_changes = "--apply" in sys.argv

    db = SessionLocal()

    try:
        places = db.query(Place).order_by(Place.id).all()

        print("TONG DIA DIEM MYSQL:", len(places))

        if len(places) != 49:
            raise RuntimeError(
                "MYSQL KHONG CO DUNG 49 DIA DIEM!"
            )

        database_places = {
            normalize_name(p.name): p
            for p in places
        }

        activity_names = {
            normalize_name(name)
            for name in ACTIVITIES
        }

        missing = activity_names - set(database_places)
        extra = set(database_places) - activity_names

        if missing or extra:
            print("TEN KHONG TIM THAY TRONG MYSQL:", missing)
            print("TEN CHUA CO TRONG DANH SACH:", extra)
            raise RuntimeError(
                "TEN DIA DIEM KHONG KHOP. CHUA CAP NHAT!"
            )

        updated = 0
        preserved = 0

        for name, activities in ACTIVITIES.items():

            place = database_places[normalize_name(name)]

            # Giu nguyen hoat dong da co
            if place.activities:
                preserved += 1
                continue

            print("SE CAP NHAT:", place.id, place.name)
            print("  ", ", ".join(activities))

            if apply_changes:
                place.activities = activities

            updated += 1

        if apply_changes:
            db.commit()
            print("--------------------------------")
            print("CAP NHAT MYSQL THANH CONG!")
            print("SO DIA DIEM VUA CAP NHAT:", updated)
            print("SO DIA DIEM GIU NGUYEN:", preserved)

        else:
            print("--------------------------------")
            print("DAY LA CHE DO XEM TRUOC.")
            print("SO DIA DIEM CAN CAP NHAT:", updated)
            print("CHUA THAY DOI DU LIEU MYSQL.")
            print("CHAY LAI VOI --apply DE LUU.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
