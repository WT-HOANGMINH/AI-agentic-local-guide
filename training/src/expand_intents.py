
from pathlib import Path
import re
import shutil

import pandas as pd

# =========================================================
# CAU HINH DUONG DAN
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = PROJECT_ROOT / "training" / "data" / "intents.csv"
BACKUP_PATH = PROJECT_ROOT / "training" / "data" / "intents_backup_before_cafe_expansion.csv"

# =========================================================
# DU LIEU BO SUNG
# Chi su dung 5 nhan da co trong dataset
# =========================================================

NEW_DATA = {
    "food": [
        "Tìm quán ăn địa phương gần biển Mỹ Khê",
        "Tôi muốn thử đặc sản Đà Nẵng với giá rẻ",
        "Gợi ý nhà hàng hải sản cho nhóm bạn",
        "Tìm quán mì Quảng gần trung tâm",
        "Có quán bún chả cá ngon không?",
        "Tôi muốn ăn tối gần cầu Rồng",
        "Tìm quán ăn sáng bình dân",
        "Gợi ý địa điểm ăn trưa cho gia đình",
        "Tôi muốn thử bánh tráng cuốn thịt heo",
        "Tìm quán ăn vặt buổi tối",
        "Có nhà hàng món Việt nào ngon?",
        "Tìm quán cơm gà gần đây",
        "Tôi muốn ăn hải sản với ngân sách thấp",
        "Gợi ý quán bánh xèo ở Đà Nẵng",
        "Tìm nơi ăn món chay",
        "Có quán bún bò nào gần trung tâm?",
        "Tôi muốn thử món ăn đường phố",
        "Tìm nhà hàng phù hợp cho buổi hẹn",
        "Gợi ý món ngon cho khách lần đầu đến Đà Nẵng",
        "Tìm quán ăn mở cửa khuya",
    ],

    "attraction": [
        "Tôi muốn tìm nơi ngắm hoàng hôn ở Đà Nẵng",
        "Gợi ý điểm ngắm bình minh gần biển",
        "Tìm địa điểm chụp ảnh phong cảnh",
        "Có nơi nào ngắm toàn cảnh thành phố không?",
        "Tôi muốn tham quan địa điểm lịch sử",
        "Gợi ý điểm check-in nổi tiếng",
        "Tìm nơi đi dạo vào buổi chiều",
        "Tôi muốn khám phá bán đảo Sơn Trà",
        "Có địa điểm văn hóa nào đáng tham quan?",
        "Tìm công viên để thư giãn cuối tuần",
        "Gợi ý địa điểm tham quan miễn phí",
        "Tôi muốn đi chùa Linh Ứng",
        "Tìm điểm du lịch thiên nhiên gần trung tâm",
        "Có nơi nào ngắm cảnh biển đẹp không?",
        "Tôi muốn tham quan bảo tàng ở Đà Nẵng",
        "Gợi ý địa điểm vui chơi cho gia đình",
        "Tìm nơi ngắm cầu Rồng về đêm",
        "Tôi muốn khám phá các công trình kiến trúc",
        "Gợi ý địa điểm đi chơi khi trời nắng",
        "Tìm điểm tham quan phù hợp cho người lớn tuổi",
    ],

    "cafe": [
        "Tìm chỗ ngồi làm việc bằng laptop",
        "Tìm nơi uống trà sữa giá rẻ",
        "Tôi cần quán cà phê có wifi mạnh",
        "Gợi ý quán nước có ổ cắm điện",
        "Tìm quán cà phê yên tĩnh để học bài",
        "Tôi muốn làm bài tập ở quán cà phê",
        "Có quán cà phê nào phù hợp để học nhóm?",
        "Tìm quán trà sữa gần trường đại học",
        "Tôi muốn uống trà sữa với giá sinh viên",
        "Gợi ý quán nước có chỗ ngồi thoải mái",
        "Tìm quán cà phê mở cửa từ sáng sớm",
        "Tôi cần nơi làm việc từ xa ở Đà Nẵng",
        "Gợi ý quán cà phê có wifi miễn phí",
        "Tìm quán nước không quá đông người",
        "Có quán trà nào phù hợp để học nhóm?",
        "Tìm quán cà phê có bàn rộng để làm việc",
        "Tôi cần chỗ ngồi học bài buổi tối",
        "Gợi ý quán trà sữa có giá hợp lý",
        "Tìm quán cà phê có máy lạnh và wifi",
        "Tôi muốn ngồi làm việc vài tiếng ở quán nước",
        "Có quán cà phê yên tĩnh gần trung tâm không?",
        "Tìm quán nước phù hợp để trò chuyện",
        "Gợi ý quán cà phê có không gian học tập",
        "Tôi muốn uống trà đào ở Đà Nẵng",
        "Tìm nơi uống nước và nghỉ chân",
        "Có quán cà phê nào có nhiều chỗ ngồi?",
        "Tôi cần quán cà phê để họp nhóm",
        "Gợi ý quán trà sữa gần biển Mỹ Khê",
        "Tìm quán cà phê có view đẹp để ngồi lâu",
        "Tôi muốn tìm quán nước giá rẻ",
        "Có quán cà phê phù hợp để đọc tài liệu không?",
        "Tìm quán cà phê có không gian làm việc chung",
        "Tôi cần nơi uống cà phê và dùng máy tính",
        "Gợi ý quán nước có không gian mát mẻ",
        "Tìm quán cà phê phù hợp cho sinh viên",
        "Tôi muốn tìm quán trà sữa để gặp bạn",
        "Tìm quán cà phê gần cầu Rồng để làm việc",
        "Tôi muốn ngồi học ở quán có điều hòa",
        "Gợi ý nơi uống cà phê vào buổi chiều",
        "Tìm quán nước có chỗ ngồi ngoài trời",
        "Tôi cần nơi thư giãn và uống đồ uống",
        "Gợi ý quán cà phê có không gian yên tĩnh",
        "Tìm quán cà phê để học online",
        "Có quán nước nào có bàn làm việc rộng?",
        "Tôi muốn tìm quán cà phê để đọc sách",
        "Tìm quán trà sữa mở cửa buổi tối",
        "Gợi ý quán cà phê có nhiều cây xanh",
        "Tôi muốn uống sinh tố gần trung tâm",
        "Tìm quán cà phê phù hợp để làm dự án nhóm",
        "Có quán nước nào có điều hòa và wifi?",
        "Tìm quán cà phê có bánh ngọt",
        "Tôi muốn ngồi cà phê ngắm sông Hàn",
        "Gợi ý quán cà phê có view biển",
        "Tìm quán nước để nghỉ ngơi sau khi tham quan",
        "Tôi muốn uống cà phê với ngân sách thấp",
        "Có quán trà sữa nào ngon gần đây?",
        "Tìm quán cà phê phù hợp để gặp đối tác",
        "Tôi cần một nơi yên tĩnh để làm việc",
        "Gợi ý quán cà phê có chỗ ngồi ngoài trời",
        "Tìm quán nước gần trường đại học",
        "Tôi muốn tìm quán cà phê để trò chuyện với bạn",
    ],

    "itinerary": [
        "Lập lịch trình du lịch Đà Nẵng một ngày",
        "Tôi có hai ngày ở Đà Nẵng nên đi đâu?",
        "Sắp xếp các điểm tham quan gần nhau",
        "Lập kế hoạch du lịch với ngân sách thấp",
        "Gợi ý lịch trình ăn uống và tham quan",
        "Tôi chỉ có nửa ngày để khám phá thành phố",
        "Lập kế hoạch đi chơi cuối tuần",
        "Sắp xếp các điểm check-in trong một ngày",
        "Tôi muốn kết hợp đi biển và ăn hải sản",
        "Lập lịch trình cho gia đình có trẻ nhỏ",
        "Gợi ý kế hoạch du lịch cho cặp đôi",
        "Sắp xếp lịch trình từ sáng đến tối",
        "Tôi muốn đi nhiều nơi nhưng tiết kiệm chi phí",
        "Lập kế hoạch khám phá Đà Nẵng trong ba ngày",
        "Sắp xếp địa điểm để giảm thời gian di chuyển",
        "Tôi muốn lịch trình không quá vội",
        "Gợi ý lịch trình cho người thích chụp ảnh",
        "Lập kế hoạch tham quan khi trời mưa",
        "Tôi muốn kết hợp cà phê và tham quan",
        "Sắp xếp điểm ăn uống gần địa điểm du lịch",
    ],

    "transport": [
        "Từ sân bay đến khách sạn nên đi bằng gì?",
        "Tìm phương tiện di chuyển giá rẻ",
        "Có xe buýt đến bán đảo Sơn Trà không?",
        "Gợi ý cách đi từ cầu Rồng đến biển Mỹ Khê",
        "Tôi muốn thuê xe máy ở Đà Nẵng",
        "Đi từ ga tàu đến trung tâm thế nào?",
        "Tìm tuyến xe buýt đến Ngũ Hành Sơn",
        "Tôi muốn biết chi phí taxi trong thành phố",
        "Gợi ý phương tiện cho gia đình có trẻ nhỏ",
        "Từ trung tâm đến sân bay mất bao lâu?",
        "Tôi muốn tìm đường đến bảo tàng Chăm",
        "Có dịch vụ đưa đón sân bay không?",
        "Tìm phương tiện cho nhóm bốn người",
        "Gợi ý cách đi lại khi trời mưa",
        "Tôi muốn so sánh chi phí xe buýt và taxi",
        "Đi từ biển Mỹ Khê đến Ngũ Hành Sơn thế nào?",
        "Tìm địa điểm thuê xe máy gần trung tâm",
        "Có tuyến xe nào đến chùa Linh Ứng?",
        "Tôi muốn tìm bãi đỗ xe gần điểm tham quan",
        "Gợi ý cách di chuyển giữa các điểm du lịch",
    ],
}


def normalize_text(text):
    """Chuan hoa van ban de phat hien cau trung lap."""
    return re.sub(r"\s+", " ", str(text).strip().casefold())


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Khong tim thay dataset: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    if not {"text", "label"}.issubset(df.columns):
        raise ValueError("Dataset phai co hai cot text va label.")

    df = df.dropna(subset=["text", "label"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip()
    df = df[(df["text"] != "") & (df["label"] != "")]

    allowed_labels = {
        "food", "attraction", "cafe", "itinerary", "transport"
    }

    unknown_labels = set(df["label"]) - allowed_labels
    if unknown_labels:
        raise ValueError(f"Dataset co nhan khong hop le: {unknown_labels}")

    # Sao luu dataset truoc khi thay doi, khong ghi de ban sao cu
    if not BACKUP_PATH.exists():
        shutil.copy2(DATA_PATH, BACKUP_PATH)
        print(f"Da sao luu dataset: {BACKUP_PATH}")
    else:
        print("Ban sao truoc khi mo rong da ton tai.")

    existing = set(df["text"].map(normalize_text))
    rows_to_add = []

    for label, sentences in NEW_DATA.items():
        for sentence in sentences:
            normalized = normalize_text(sentence)

            if normalized in existing:
                continue

            rows_to_add.append({
                "text": sentence,
                "label": label
            })
            existing.add(normalized)

    if rows_to_add:
        additions = pd.DataFrame(rows_to_add)
        df = pd.concat([df, additions], ignore_index=True)

        # Loai bo trung lap neu co, giu lai dong dau tien
        df["_normalized"] = df["text"].map(normalize_text)
        df = df.drop_duplicates(subset="_normalized", keep="first")
        df = df.drop(columns=["_normalized"])

        df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
        print(f"Da them {len(rows_to_add)} cau moi.")
    else:
        print("Khong co cau moi nao duoc them.")

    print(f"\nTong so mau: {len(df)}")
    print("\nSo luong mau theo nhan:")
    print(df["label"].value_counts().sort_index())

    duplicates = df["text"].map(normalize_text).duplicated().sum()
    print(f"\nSo cau trung lap: {duplicates}")
    print("\nDa hoan tat mo rong dataset.")


if __name__ == "__main__":
    main()
