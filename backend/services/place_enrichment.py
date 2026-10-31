"""Quy tắc suy ra dữ liệu cho planner từ dữ liệu địa điểm có sẵn (không phụ thuộc DB).
Các con số thời lượng là ước lượng mặc định: hãy xem lại cho các địa điểm quan trọng."""
import re

from backend.services.slot_service import strip_accents

ATTRACTION_DURATION = [  # (regex trên tên không dấu, số phút) - lấy quy tắc khớp đầu tiên
    (r"ba na hills|sun world", 300),
    (r"cu lao cham|hon lao", 480),
    (r"my son|thanh dia", 180),
    (r"vuon thu", 90),
    (r"nuoc khoang nong|cong vien nuoc", 240),
    (r"pho co hoi an", 180),
    (r"asia park|chau a", 120),
    (r"chua |hoi quan|nha co|^dinh |dinh lang|thanh dien hai|nha tho", 45),
    (r"ban dao son tra|khu bao ton", 180),
    (r"suoi|thac|sinh thai|khe ram|ngam doi|toom sara|retreat", 120),
    (r"bai bien|^bai |bai tam", 120),
    (r"ngu hanh son|ngan thuy son|deo hai van", 90),
    (r"bao tang|show|nha hat", 90),
    (r"^dong |dinh ban co|cay da|^cau |song ", 45),
    (r"cong vien", 60),
]


def parse_hours(s):
    """'06:30 - 22:00' -> ('06:30','22:00'); 'Cả ngày' -> ('00:00','23:59'); không rõ -> (None, None)."""
    t = strip_accents(s or "")
    t = re.sub(r"[–—−]", "-", t)
    m = re.search(r"(\d{1,2})[:h](\d{2})\s*-\s*(\d{1,2})[:h](\d{2})", t)
    if m:
        h1, m1, h2, m2 = map(int, m.groups())
        close = f"{h2:02d}:{m2:02d}" if h2 < 24 else "23:59"
        return f"{h1:02d}:{m1:02d}", close
    if "ngay" in t:
        return "00:00", "23:59"
    return None, None


def zone_of(name, address):
    """Suy ra khu vực từ địa chỉ/tên (dùng cho ước lượng di chuyển khi thiếu tọa độ)."""
    s = strip_accents(f"{address} {name}")
    if re.search(r"cu lao cham|hon lao|tan hiep", s): return "cu_lao_cham"
    if re.search(r"my son|duy xuyen|duy phu", s): return "my_son"
    if re.search(r"hoi an|dien ban|dien duong", s): return "hoi_an"
    if "ba na" in s: return "ba_na"
    if re.search(r"hoa vang|hoa phu|hoa bac|hoa chau", s): return "hoa_vang"
    if re.search(r"lien chieu|hai van", s): return "lien_chieu"
    if re.search(r"ngu hanh son|non nuoc", s): return "ngu_hanh_son"
    if "son tra" in s and "hai chau" in s: return "trung_tam"  # cầu nối hai quận
    if "son tra" in s:
        return "son_tra_ban_dao" if re.search(r"tho quang|ban dao|chan cau moi|tien sa", s) else "son_tra"
    if re.search(r"hai chau|thanh khe|cam le|hoa cuong|hoa thuan|trung tam thanh pho", s): return "trung_tam"
    return None


def duration_for(name, category):
    if category != "tourist_attraction":
        return 60
    n = strip_accents(name)
    for pat, mins in ATTRACTION_DURATION:
        if re.search(pat, n):
            return mins
    return 60


def best_time_for(name, description, open_time, category):
    n, d = strip_accents(name), strip_accents(description or "")
    if category == "shopping":
        return "night" if open_time and open_time >= "17:00" else None
    if category != "tourist_attraction":
        return None
    if open_time and open_time >= "18:00": return "night"
    if open_time and open_time >= "15:00": return "sunset"
    if re.search(r"cau rong|cau song han|cau tinh yeu", n): return "night"
    if re.search(r"hoang hon|thuan phuoc", n + " " + d): return "sunset"
    if re.search(r"binh minh|bai bien|^bai |ban dao|dinh ban co|deo hai van|ba na|ngu hanh son", n + " " + d):
        return "morning"
    return None
