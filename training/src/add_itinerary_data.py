
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_ROOT / "training" / "data" / "intents.csv"

NEW_ITINERARY = [
    "Hãy lập tuyến tham quan nhiều địa điểm trong cùng một ngày",
    "Tạo lịch trình sao cho các điểm đến nối tiếp nhau thuận tiện",
    "Sắp xếp thứ tự ghé thăm các địa điểm du lịch",
    "Tối ưu kế hoạch tham quan để hạn chế thời gian đi đường",
    "Lập lịch trình gồm địa điểm ăn uống và điểm tham quan gần nhau",
    "Tôi muốn ghé nhiều nơi nhưng không phải quay lại đường cũ",
    "Hãy chia các điểm du lịch thành từng cụm theo khu vực",
    "Lập kế hoạch đi chơi dựa trên giờ mở cửa của các địa điểm",
    "Sắp xếp điểm tham quan phù hợp với giờ đến và giờ rời Đà Nẵng",
    "Tạo lịch trình có thời gian dự phòng giữa các hoạt động",
    "Tôi muốn đi tham quan trước rồi ăn tối ở nơi gần đó",
    "Lập kế hoạch tham quan và chọn điểm ăn trưa thuận tiện",
    "Hãy đề xuất thứ tự đi các điểm để tiết kiệm công sức",
    "Tôi muốn lịch trình có thể đổi điểm nếu trời mưa",
    "Điều chỉnh lịch trình khi một địa điểm quá đông khách",
    "Tạo phương án tham quan thay thế nếu không kịp giờ",
    "Lập kế hoạch cho một ngày với thời gian xuất phát cụ thể",
    "Sắp xếp các điểm đến theo khoảng thời gian tôi có",
    "Tạo lịch trình có cả điểm tham quan và thời gian nghỉ chân",
    "Tôi muốn ưu tiên các điểm gần nhau trong chuyến đi",
    "Lập kế hoạch tham quan theo sở thích và ngân sách của tôi",
    "Tạo lịch trình kết hợp bảo tàng, ăn uống và đi dạo",
    "Sắp xếp kế hoạch đi chơi cho nhóm có nhiều sở thích khác nhau",
    "Lập lịch trình linh hoạt nếu tôi muốn bỏ qua một điểm đến",
    "Tôi muốn lên kế hoạch cho chuyến đi từ sáng đến tối theo thứ tự hợp lý",
]

def normalize(text):
    return " ".join(str(text).strip().casefold().split()).rstrip(".,!?;:")

def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Khong tim thay dataset: {DATA_FILE}")

    df = pd.read_csv(DATA_FILE)

    required_columns = {"text", "label"}
    if not required_columns.issubset(df.columns):
        raise ValueError("Dataset phai co hai cot: text va label")

    existing = set(df["text"].dropna().map(normalize))
    rows_to_add = []

    for text in NEW_ITINERARY:
        key = normalize(text)
        if key and key not in existing:
            rows_to_add.append({"text": text, "label": "itinerary"})
            existing.add(key)

    if not rows_to_add:
        print("Khong co cau moi nao can them.")
        return

    updated = pd.concat(
        [df, pd.DataFrame(rows_to_add)],
        ignore_index=True
    )
    updated.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

    print(f"Da them {len(rows_to_add)} cau itinerary.")
    print(f"Tong so mau moi: {len(updated)}")
    print("\nSo luong mau theo nhan:")
    print(updated["label"].value_counts().sort_index())
    print(f"\nDa cap nhat: {DATA_FILE}")

if __name__ == "__main__":
    main()
