"""Thêm dữ liệu cho 4 ý định hội thoại mới vào training/data/intents.csv (tự sao lưu trước).
Chạy từ thư mục gốc dự án:  python training/src/add_dialogue_data.py
Sau đó hãy tự gõ thêm 20-30 câu THẬT cho mỗi nhãn mới (nhất là câu ngắn, có/không dấu, Việt/Anh).
"""
import random
import shutil
import unicodedata
from pathlib import Path

import pandas as pd

random.seed(7)
CSV = Path(__file__).resolve().parents[2] / "training" / "data" / "intents.csv"
P = ["Bà Nà", "Bà Nà Hills", "Cầu Rồng", "Mỹ Khê", "Sơn Trà", "Ngũ Hành Sơn", "chùa Linh Ứng",
     "chợ Hàn", "Hội An", "Bãi Bụt", "ba na", "cau rong", "my khe", "Cù Lao Chàm", "Mỹ Sơn"]

TEMPLATES = {
    "modify_itinerary": [
        "đi {p} từ sớm", "mình muốn đi {p} sớm hơn", "đổi {p} sang buổi sáng", "bỏ {p} ra khỏi lịch trình",
        "bớt {p} đi", "thêm {p} vào lịch trình", "thêm {p} vào ngày 2", "xuất phát lúc 6h",
        "dời lịch trình lên sớm hơn", "ngày 2 đi muộn hơn một chút", "sắp xếp lại cho các điểm gần nhau hơn",
        "thêm một quán cà phê vào ngày 1", "thêm bữa sáng vào ngày 1", "đổi sang đi {p} trước",
        "cho {p} đi đầu tiên", "bỏ bớt một điểm đi", "go to {p} earlier", "start the day at 6am",
        "remove {p} from the plan", "add {p} to day 2", "make day 1 shorter", "i want to leave earlier",
        "add breakfast on day 1", "swap the order of the places", "move {p} to the morning", "put {p} first"],
    "clarify_reply": [
        "{n} ngày", "{n} ngày {m} đêm", "mình đi {n} ngày", "thích biển", "mình thích thiên nhiên và ẩm thực",
        "văn hóa và chụp ảnh", "đi {n} người", "ngân sách {b}k", "ăn sáng", "ăn tối", "bữa trưa", "khu {p}",
        "gần {p}", "tùy bạn", "gợi ý giúp mình", "gì cũng được", "{n} days", "i like beaches", "for {n} people",
        "breakfast please", "near {p}", "you decide", "anything is fine", "budget {b}k", "{n} days and {m} nights",
        "mình ở gần {p}", "dinner", "lunch"],
    "greeting": [
        "xin chào", "chào bạn", "chào", "hello", "hi", "hey", "alo", "chào buổi sáng", "good morning",
        "hello bạn", "hi guide", "chào guide ơi", "hey there", "good evening", "xin chào, bạn khỏe không",
        "chào buổi tối", "chào bạn nhé", "hi bạn", "hello guide", "good afternoon", "yo", "chào ad",
        "hế lô", "xin chào guide", "chào buổi chiều", "hello there", "hi there", "chao ban", "xin chao"],
    "ask_detail": [
        "{p} mở cửa mấy giờ", "vé vào {p} bao nhiêu tiền", "{p} có gì hay", "{p} nằm ở đâu",
        "giờ mở cửa của {p}", "giá vé {p}", "kể mình nghe về {p}", "{p} có đáng đi không",
        "{p} mấy giờ đóng cửa", "cho mình biết thêm về {p}", "what time does {p} open",
        "how much is the ticket for {p}", "tell me more about {p}", "is {p} worth visiting",
        "where is {p}", "when does {p} close"],
}


def strip(s):
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def fill(t):
    return t.format(p=random.choice(P), n=random.randint(1, 5), m=random.randint(1, 4),
                    b=random.choice([200, 300, 500, 1000]))


def main():
    rows = []
    for label, temps in TEMPLATES.items():
        for t in temps:
            for _ in range(8 if "{" in t else 1):
                s = fill(t)
                for v in {s, strip(s), s.capitalize()}:
                    rows.append((v, label))
    new = pd.DataFrame(rows, columns=["text", "label"]).drop_duplicates()
    old = pd.read_csv(CSV, encoding="utf-8-sig")
    backup = CSV.with_name("intents_backup_before_dialogue.csv")
    shutil.copy2(CSV, backup)
    merged = pd.concat([old[["text", "label"]], new], ignore_index=True)
    merged = merged.drop_duplicates(subset="text", keep="first")
    merged.to_csv(CSV, index=False, encoding="utf-8")
    print(f"Đã sao lưu: {backup}")
    print(merged["label"].value_counts().to_string())


if __name__ == "__main__":
    main()
