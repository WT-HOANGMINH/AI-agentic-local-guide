"""Sinh dữ liệu gán nhãn từng từ (BIO) cho bộ trích thông tin.  Chạy: python training/src/generate_slots.py
Mẹo: sau khi thử thực tế, hãy thêm khuôn mẫu cho các cách nói bị bắt sai vào TEMPLATES rồi sinh lại + huấn luyện lại.
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.services.slot_service import strip_accents, tokenize   # noqa: E402

random.seed(42)
f = ROOT / "training" / "data" / "place_names.txt"
PLACES = ([l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else
          ["Bà Nà Hills", "Cầu Rồng", "Mỹ Khê", "Sơn Trà", "Ngũ Hành Sơn", "Hội An", "chợ Hàn", "Bãi Bụt",
           "chùa Linh Ứng", "Cù Lao Chàm", "Mỹ Sơn", "Hải Vân"])

VALUES = {
    "DAYS": [["1", "ngày"], ["2", "ngày"], ["hai", "ngày"], ["3", "ngày", "2", "đêm"], ["ba", "ngày"], ["một", "ngày"],
             ["2", "days"], ["two", "days"], ["3", "days", "2", "nights"], ["1", "day"], ["4", "ngày"], ["5", "ngày"]],
    "TIME": [["6h"], ["7h"], ["6", "giờ"], ["06:30"], ["7", "am"], ["6h30"], ["sớm"], ["sáng", "sớm"], ["early"],
             ["8", "giờ", "sáng"], ["5", "am"]],
    "MEAL": [["ăn", "sáng"], ["ăn", "trưa"], ["ăn", "tối"], ["bữa", "sáng"], ["bữa", "tối"], ["breakfast"], ["lunch"], ["dinner"]],
    "INTEREST": [["biển"], ["thiên", "nhiên"], ["văn", "hóa"], ["ẩm", "thực"], ["hoàng", "hôn"], ["chụp", "ảnh"],
                 ["check-in"], ["beach"], ["nature"], ["culture"], ["sunset"], ["street", "food"]],
    "BUDGET": [["500", "nghìn"], ["500k"], ["1", "triệu"], ["2", "triệu"], ["300k"], ["rẻ"], ["tiết", "kiệm"],
               ["cheap"], ["$20"], ["200", "k"]],
    "PEOPLE": [["2", "người"], ["4", "người"], ["6", "người"], ["2", "people"], ["4", "people"], ["cả", "nhà"],
               ["gia", "đình"], ["family"], ["một", "mình"]],
}
TEMPLATES = [
    "tôi muốn đi {PLACE} từ {TIME}", "mình muốn đi {PLACE} {TIME}", "đi {PLACE} {TIME} nhé",
    "đi {PLACE} từ sớm", "mình muốn đi {PLACE} sớm hơn", "cho {PLACE} đi đầu tiên",
    "lên lịch trình {DAYS} thích {INTEREST}", "cho mình lịch trình {DAYS} cho {PEOPLE}",
    "lịch trình {DAYS} đi {PLACE} và {INTEREST}", "mình muốn {MEAL} ở {PLACE}", "{MEAL} gần {PLACE}",
    "tìm quán {MEAL} giá {BUDGET}", "đi {PEOPLE} ngân sách {BUDGET}", "ngân sách {BUDGET}",
    "{DAYS}", "{INTEREST}", "{INTEREST} và {INTEREST}", "{PLACE}", "{PLACE} {TIME}", "{MEAL}", "{PEOPLE}",
    "đổi {PLACE} sang {TIME}", "bỏ {PLACE} khỏi lịch trình", "thêm {PLACE} vào lịch trình",
    "xuất phát lúc {TIME}", "mình thích {INTEREST} và muốn đi {DAYS}",
    # nhắc tới "ngày N" (số thứ tự ngày) KHÔNG phải số ngày của chuyến đi
    "thêm {MEAL} vào ngày 2", "thêm {PLACE} vào ngày 2", "bỏ {PLACE} khỏi ngày 1", "đi {PLACE} vào ngày 3",
    "ngày 2 xuất phát lúc {TIME}", "ngày 1 đi {PLACE} từ {TIME}", "đổi ngày 2 sang {TIME}",
    "add {MEAL} on day 2", "add {PLACE} to day 2", "remove {PLACE} from day 1", "on day 3 start at {TIME}",
    "i want to go to {PLACE} {TIME}", "plan {DAYS} for {PEOPLE} with {INTEREST}", "plan {DAYS} trip",
    "where can i have {MEAL} near {PLACE}", "budget {BUDGET}", "i like {INTEREST}", "start at {TIME}",
    "remove {PLACE} from the plan", "add {PLACE} to the plan", "{DAYS} in {PLACE}", "show me {INTEREST} spots",
    "ăn gì ở {PLACE}", "tôi muốn đi chơi", "gợi ý quán cà phê gần {PLACE}", "{PLACE} mở cửa mấy giờ",
    "vé vào {PLACE} bao nhiêu", "từ {PLACE} đến {PLACE} bao xa", "what time does {PLACE} open",
    "lịch trình", "ăn gì", "cà phê", "địa điểm nổi tiếng",
    "tôi du lịch ở đà nẵng tôi muốn đi {PLACE} và {PLACE} ăn {MEAL} uống cà phê nghỉ trưa đi cùng bạn gái",
    "mình muốn đi {PLACE} cùng bạn gái trong {DAYS}",
    "ăn mì quảng sáng rồi đi {PLACE}",
    "uống cà phê và nghỉ trưa trong lịch trình {DAYS}",
]


def make():
    toks, tags = [], []
    for w in random.choice(TEMPLATES).split():
        m = re.fullmatch(r"\{(\w+)\}", w)
        if m:
            kind = m.group(1)
            vals = tokenize(random.choice(PLACES)) if kind == "PLACE" else random.choice(VALUES[kind])
            toks += vals
            tags += [("B-" if i == 0 else "I-") + kind for i in range(len(vals))]
        else:
            toks.append(w)
            tags.append("O")
    if random.random() < 0.4:                      # giả lập gõ không dấu
        toks = [strip_accents(t) for t in toks]
    return toks, tags


def main():
    seen, out = set(), []
    for _ in range(40000):
        toks, tags = make()
        key = (tuple(toks), tuple(tags))
        if key not in seen:
            seen.add(key)
            out.append({"tokens": toks, "tags": tags})
        if len(out) >= 8000:
            break
    path = ROOT / "training" / "data" / "slots_train.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out), encoding="utf-8")
    print(f"Đã sinh {len(out)} câu -> {path}  (từ {len(PLACES)} tên địa điểm)")


if __name__ == "__main__":
    main()
