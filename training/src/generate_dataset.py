"""
Sinh bo du lieu y dinh (intent) song ngu Viet - Anh quy mo lon (mac dinh 60.000 mau).

Cach lam:
  * Moi nhan co nhieu "mau cau" (template) tieng Viet va tieng Anh, trong do cac cho
    trong {area}, {dish}, {budget}... duoc dien tu danh sach gia tri thuc te cua
    Da Nang / Hoi An. Moi gia tri co ban dich Viet - Anh di kem nen hai ngon ngu nhat quan.
  * Them bien the tu nhien: loi mo dau, loi ket, bo dau tieng Viet, viet thuong,
    thieu dau cau, loi go tieng Anh nhe.
  * CHONG RO RI DU LIEU: mot phan mau cau (20%) duoc giu rieng de tao tap kiem thu
    "synthetic_eval" -> model khong the "hoc thuoc" cau truc cau khi duoc danh gia.
  * Loai bo cau trung voi bo du lieu viet tay (intents.csv) de bo viet tay van la
    thuoc do danh gia trung thuc nhat.

Chay:
    python training/src/generate_dataset.py                 # 60.000 mau, 5 nhan
    python training/src/generate_dataset.py --total 80000
    python training/src/generate_dataset.py --extra-labels  # them accommodation, weather, out_of_scope
"""
import argparse
import random
import re
import string
import unicodedata
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "training" / "data"
HUMAN_PATH = DATA_DIR / "intents.csv"

CORE_LABELS = ["food", "cafe", "attraction", "itinerary", "transport"]
EXTRA_LABELS = ["accommodation", "weather", "out_of_scope"]

# ---------------------------------------------------------------------------
# CAC GIA TRI DIEN VAO CHO TRONG: moi phan tu la cap (tieng Viet, tieng Anh)
# ---------------------------------------------------------------------------
SLOTS = {
    "area": [("", "")] * 3 + [
        ("gần cầu Rồng", "near Dragon Bridge"),
        ("gần biển Mỹ Khê", "near My Khe Beach"),
        ("ở trung tâm Đà Nẵng", "in central Da Nang"),
        ("gần sông Hàn", "near the Han River"),
        ("gần bán đảo Sơn Trà", "near Son Tra Peninsula"),
        ("gần Ngũ Hành Sơn", "near the Marble Mountains"),
        ("gần chợ Hàn", "near Han Market"),
        ("gần sân bay", "near the airport"),
        ("gần ga Đà Nẵng", "near Da Nang Train Station"),
        ("ở phố cổ Hội An", "in Hoi An Ancient Town"),
        ("gần chùa Cầu", "near the Japanese Covered Bridge"),
        ("gần biển An Bàng", "near An Bang Beach"),
        ("ở quận Hải Châu", "in Hai Chau District"),
        ("ở quận Sơn Trà", "in Son Tra District"),
        ("ở quận Ngũ Hành Sơn", "in Ngu Hanh Son District"),
        ("ở quận Thanh Khê", "in Thanh Khe District"),
        ("ở quận Liên Chiểu", "in Lien Chieu District"),
        ("gần khách sạn của tôi", "near my hotel"),
        ("gần đây", "nearby"),
        ("quanh đây", "around here"),
        ("ở Hội An", "in Hoi An"),
        ("ở Đà Nẵng", "in Da Nang"),
        ("gần Bà Nà Hills", "near Ba Na Hills"),
        ("gần cầu Sông Hàn", "near Han River Bridge"),
        ("gần cầu Tình Yêu", "near Love Bridge"),
    ],
    "dish": [
        ("mì Quảng", "Mi Quang"), ("bún chả cá", "bun cha ca"), ("bánh xèo", "banh xeo"),
        ("bánh tráng cuốn thịt heo", "pork rice paper rolls"), ("bún mắm nêm", "bun mam nem"),
        ("bánh mì", "banh mi"), ("cao lầu", "cao lau"), ("cơm gà", "chicken rice"),
        ("hải sản", "seafood"), ("bún bò", "beef noodle soup"), ("nem lụi", "nem lui"),
        ("bánh bèo", "banh beo"), ("chè", "Vietnamese sweet soup"), ("lẩu", "hotpot"),
        ("ốc", "snails"), ("bánh canh", "banh canh"), ("bún thịt nướng", "grilled pork vermicelli"),
        ("cơm hến", "clam rice"),
    ],
    "meal": [("sáng", "breakfast"), ("trưa", "lunch"), ("tối", "dinner"), ("khuya", "a late-night meal")],
    "foodtype": [
        ("hải sản", "seafood"), ("món chay", "vegetarian"), ("món Việt", "Vietnamese"),
        ("đặc sản miền Trung", "Central Vietnamese"), ("bình dân", "budget-friendly local"),
        ("món nướng", "grilled food"), ("lẩu", "hotpot"),
    ],
    "foodfeat": [
        ("giá rẻ", "that is cheap"), ("đông người địa phương", "that locals love"),
        ("hợp khẩu vị khách nước ngoài", "that foreign visitors like"),
        ("mở cửa khuya", "that is open late"), ("có chỗ đậu xe", "that has parking"),
        ("không quá cay", "that is not too spicy"), ("sạch sẽ", "that is clean"),
        ("có menu tiếng Anh", "that has an English menu"), ("không gian đẹp", "with a nice atmosphere"),
    ],
    "drink": [
        ("cà phê", "coffee"), ("cà phê muối", "salted coffee"), ("trà sữa", "milk tea"),
        ("trà đào", "peach tea"), ("sinh tố", "smoothies"), ("cà phê trứng", "egg coffee"),
        ("cà phê phin", "Vietnamese drip coffee"), ("nước ép", "fresh juice"),
    ],
    "cafefeat": [
        ("có wifi mạnh", "that has strong Wi-Fi"), ("yên tĩnh", "that is quiet"),
        ("có ổ cắm điện", "that has power outlets"), ("mở cửa sớm", "that opens early"),
        ("có view sông", "that has a river view"), ("có view biển", "that has a sea view"),
        ("có máy lạnh", "that is air-conditioned"), ("ít người", "that is not crowded"),
        ("có chỗ ngồi ngoài trời", "that has outdoor seating"),
        ("giá sinh viên", "with student-friendly prices"),
        ("có không gian xanh", "with lots of greenery"),
        ("đẹp để chụp ảnh", "that is good for taking photos"),
    ],
    "worktask": [
        ("làm việc bằng laptop", "work on my laptop"), ("học bài", "study"),
        ("họp nhóm", "hold a team meeting"), ("đọc sách", "read a book"),
        ("làm việc từ xa", "work remotely"), ("học online", "attend online classes"),
    ],
    "atype": [
        ("điểm tham quan nổi tiếng", "famous attractions"), ("nơi ngắm hoàng hôn", "sunset viewpoints"),
        ("nơi ngắm bình minh", "sunrise spots"), ("địa điểm chụp ảnh đẹp", "great photo spots"),
        ("bảo tàng", "museums"), ("chùa", "temples"), ("bãi biển đẹp", "beautiful beaches"),
        ("công viên", "parks"), ("địa điểm lịch sử", "historical sites"),
        ("điểm check-in", "check-in spots"),
        ("nơi ngắm toàn cảnh thành phố", "places with panoramic city views"),
        ("địa điểm văn hóa", "cultural sites"), ("khu vui chơi", "amusement areas"),
        ("cây cầu nổi tiếng", "famous bridges"), ("làng nghề truyền thống", "traditional craft villages"),
    ],
    "attr": [
        ("Ngũ Hành Sơn", "the Marble Mountains"), ("bán đảo Sơn Trà", "Son Tra Peninsula"),
        ("Bà Nà Hills", "Ba Na Hills"), ("Cầu Vàng", "the Golden Bridge"),
        ("chùa Linh Ứng", "Linh Ung Pagoda"), ("Bảo tàng Chăm", "the Cham Museum"),
        ("phố cổ Hội An", "Hoi An Ancient Town"), ("cầu Rồng", "Dragon Bridge"),
        ("biển Mỹ Khê", "My Khe Beach"), ("đèo Hải Vân", "Hai Van Pass"),
        ("Cù Lao Chàm", "the Cham Islands"), ("rừng dừa Bảy Mẫu", "Bay Mau Coconut Forest"),
        ("thánh địa Mỹ Sơn", "My Son Sanctuary"), ("chợ Hàn", "Han Market"),
        ("Công viên Châu Á", "Asia Park"), ("chùa Cầu", "the Japanese Covered Bridge"),
    ],
    "interest": [
        ("thiên nhiên", "nature"), ("lịch sử", "history"), ("chụp ảnh", "photography"),
        ("kiến trúc", "architecture"), ("văn hóa địa phương", "local culture"),
        ("biển", "the beach"), ("leo núi", "hiking"),
    ],
    "duration": [
        ("một ngày", "one day"), ("hai ngày", "two days"), ("ba ngày", "three days"),
        ("nửa ngày", "half a day"), ("cuối tuần", "a weekend"),
        ("bốn ngày ba đêm", "four days and three nights"), ("một buổi chiều", "one afternoon"),
    ],
    "budget": [
        ("100 nghìn", "100,000 VND"), ("200 nghìn", "200,000 VND"), ("300 nghìn", "300,000 VND"),
        ("500 nghìn", "500,000 VND"), ("700 nghìn", "700,000 VND"), ("một triệu", "1 million VND"),
        ("1,5 triệu", "1.5 million VND"), ("hai triệu", "2 million VND"),
        ("ba triệu", "3 million VND"), ("năm triệu", "5 million VND"),
    ],
    "group": [
        ("hai người", "two people"), ("gia đình có trẻ nhỏ", "a family with young children"),
        ("nhóm bạn", "a group of friends"), ("bố mẹ lớn tuổi", "my elderly parents"),
        ("nhóm bốn người", "a group of four"), ("đồng nghiệp", "my colleagues"),
        ("một người", "one person"), ("người yêu", "my partner"),
    ],
    "combo": [
        ("tham quan và ăn uống", "sightseeing and food"), ("biển và núi", "beaches and mountains"),
        ("cà phê và chụp ảnh", "cafes and photo spots"), ("văn hóa và ẩm thực", "culture and local cuisine"),
        ("tham quan và nghỉ ngơi", "sightseeing and relaxation"),
        ("thiên nhiên và hải sản", "nature and seafood"),
    ],
    "constraint": [
        ("nếu trời mưa", "if it rains"), ("không đi bộ nhiều", "with minimal walking"),
        ("có thời gian nghỉ giữa các điểm", "with rest time between stops"),
        ("tránh nơi đông người", "avoiding crowded places"),
        ("phù hợp với người lớn tuổi", "suitable for elderly travelers"),
        ("phù hợp với trẻ nhỏ", "suitable for young children"),
        ("có phương án dự phòng", "with backup options"),
    ],
    "node": [
        ("sân bay Đà Nẵng", "Da Nang Airport"), ("ga Đà Nẵng", "Da Nang Train Station"),
        ("cầu Rồng", "Dragon Bridge"), ("biển Mỹ Khê", "My Khe Beach"),
        ("Ngũ Hành Sơn", "the Marble Mountains"), ("bán đảo Sơn Trà", "Son Tra Peninsula"),
        ("Bà Nà Hills", "Ba Na Hills"), ("chợ Hàn", "Han Market"),
        ("phố cổ Hội An", "Hoi An Ancient Town"), ("trung tâm thành phố", "the city center"),
        ("khách sạn của tôi", "my hotel"), ("đèo Hải Vân", "Hai Van Pass"),
        ("thánh địa Mỹ Sơn", "My Son Sanctuary"), ("bến xe trung tâm", "the central bus station"),
        ("chợ đêm Sơn Trà", "Son Tra Night Market"), ("Bảo tàng Chăm", "the Cham Museum"),
    ],
    "mode": [
        ("xe buýt", "a bus"), ("taxi", "a taxi"), ("Grab", "a Grab"),
        ("xe ôm", "a motorbike taxi"), ("xe đưa đón", "a shuttle"),
    ],
    "rent": [
        ("xe máy", "a motorbike"), ("xe đạp", "a bicycle"), ("ô tô", "a car"),
        ("ô tô có tài xế", "a car with a driver"),
    ],
    # --- nhan bo sung ---
    "htype": [
        ("khách sạn", "hotel"), ("homestay", "homestay"), ("nhà nghỉ", "guesthouse"),
        ("hostel", "hostel"), ("resort", "resort"), ("căn hộ cho thuê ngắn ngày", "short-term apartment"),
    ],
    "hfeat": [
        ("có hồ bơi", "with a swimming pool"), ("có bữa sáng miễn phí", "with free breakfast"),
        ("yên tĩnh", "that is quiet"), ("có view biển", "with an ocean view"),
        ("giá rẻ", "that is cheap"), ("phù hợp cho gia đình", "that is family-friendly"),
        ("gần biển", "near the beach"), ("gần trung tâm", "near the city center"),
    ],
    "wtime": [
        ("hôm nay", "today"), ("ngày mai", "tomorrow"), ("cuối tuần này", "this weekend"),
        ("tuần sau", "next week"), ("tháng 7", "in July"), ("tháng 12", "in December"),
        ("tối nay", "tonight"), ("sáng mai", "tomorrow morning"), ("chiều nay", "this afternoon"),
        ("tháng 9", "in September"), ("mùa hè", "in summer"), ("mùa mưa", "during the rainy season"),
        ("dịp Tết", "during Tet"), ("tuần này", "this week"),
    ],
    "otask": [
        ("một đoạn code Python", "a Python script"), ("một bài thơ về mùa thu", "a poem about autumn"),
        ("email xin nghỉ phép", "a leave request email"),
        ("một bài luận về biến đổi khí hậu", "an essay about climate change"),
        ("bản tóm tắt một cuốn sách kinh doanh", "a summary of a business book"),
    ],
    "oconcept": [
        ("trí tuệ nhân tạo", "artificial intelligence"), ("blockchain", "blockchain"),
        ("thuyết tương đối", "the theory of relativity"), ("lạm phát", "inflation"),
        ("quang hợp", "photosynthesis"), ("học máy", "machine learning"),
    ],
    "otopic": [
        ("tỷ giá USD hôm nay", "today's USD exchange rate"),
        ("kết quả trận bóng đá tối qua", "last night's football match result"),
        ("giá vàng hôm nay", "today's gold price"), ("ai là tổng thống Pháp", "who the president of France is"),
        ("thủ đô nước Úc là gì", "what the capital of Australia is"),
        ("giá cổ phiếu Apple", "the Apple stock price"),
        ("cách sửa máy tính không khởi động", "how to fix a computer that will not boot"),
    ],
    "omath": [
        ("một phương trình bậc hai", "a quadratic equation"), ("một bài toán xác suất", "a probability problem"),
        ("một bài toán đạo hàm", "a derivative problem"), ("hệ hai phương trình", "a system of two equations"),
    ],
}

# ---------------------------------------------------------------------------
# MAU CAU THEO NHAN. Moi nhom nen co >= 5 mau (20% cuoi se vao tap eval).
# ---------------------------------------------------------------------------
TEMPLATES = {
    "food": {
        "vi": [
            "Tìm quán {dish} ngon {area}", "Quán {dish} nào ngon {area}", "Tôi muốn ăn {dish} {area}",
            "Gợi ý nhà hàng {foodtype} {area}", "Ở đâu bán {dish} ngon {area}",
            "Có quán {dish} nào ngon và giá hợp lý không", "Muốn thử {dish}, nên ăn ở đâu",
            "Tìm chỗ ăn {meal} {area}", "Gợi ý quán ăn {meal} cho {group}",
            "Đi ăn {meal} với {group}, nên chọn quán nào", "Tìm quán ăn {foodfeat} {area}",
            "Món {dish} chỗ nào ngon nhất", "Tìm nhà hàng {foodtype} cho {group}",
            "Chỗ nào bán {dish} giá dưới {budget}", "Cho mình danh sách quán {dish} {area}",
            "Quán ăn nào {foodfeat}", "Tôi đói rồi, có quán {dish} nào {area} không",
            "Giới thiệu đặc sản {dish} cho khách du lịch",
            "Nhà hàng {foodtype} nào được nhiều người khen {area}", "Tìm quán {dish} {foodfeat} {area}",
            "Mình muốn ăn {dish} cùng {group}, gợi ý giúp", "Quán {dish} nào mở cửa {meal}",
            "Có nhà hàng {foodtype} nào hợp ngân sách {budget} không",
            "Ăn {dish} ở đâu {area} mới đúng vị địa phương",
        ],
        "en": [
            "Find a good place for {dish} {area}", "Where can I eat {dish} {area}",
            "I want to try {dish} {area}", "Recommend a {foodtype} restaurant {area}",
            "Which restaurant serves the best {dish} {area}",
            "Is there a good and affordable {dish} place around", "I would like to try {dish}. Where should I go",
            "Find a place to eat {meal} {area}", "Suggest a place to eat {meal} with {group}",
            "I am going out to eat {meal} with {group}. Which restaurant should I choose",
            "Find a restaurant {foodfeat} {area}", "Where is the best {dish} in town",
            "Find a {foodtype} restaurant for {group}", "Where can I eat {dish} for under {budget}",
            "Give me a list of {dish} places {area}", "What local specialties should I try {area}",
            "Where is a restaurant {foodfeat}", "I am hungry. Is there a {dish} place {area}",
            "Where can a tourist try {dish}", "Which {foodtype} restaurant do locals recommend {area}",
            "Find a {dish} place {foodfeat} {area}", "I want to eat {dish} with {group}. Any suggestions",
            "Which {dish} place is open for {meal}",
            "Is there a {foodtype} restaurant that fits a budget of {budget}",
            "Where should I eat {dish} {area} to get an authentic local taste",
        ],
    },
    "cafe": {
        "vi": [
            "Tìm quán cà phê {cafefeat} {area}", "Quán cà phê nào {cafefeat} {area}",
            "Gợi ý quán {drink} {cafefeat}", "Tôi muốn uống {drink} {area}",
            "Có quán {drink} nào {cafefeat} không", "Tìm quán cà phê để {worktask} {area}",
            "Tôi cần chỗ ngồi để {worktask} {area}", "Quán {drink} nào {cafefeat} cho {group}",
            "Gợi ý quán nước {cafefeat} để {worktask}", "Có quán {drink} nào gần đây không",
            "Tìm chỗ uống {drink} {area}", "Quán nào {cafefeat} để {worktask}",
            "Muốn tìm quán {drink} {cafefeat} {area}", "Đi uống {drink} với {group}, quán nào {cafefeat}",
            "Tôi cần một quán cà phê {cafefeat} {area} để {worktask}", "Cho mình xin vài quán {drink} {area}",
            "Quán cà phê nào mở cửa đến khuya {area}", "Tìm quán trà sữa {cafefeat} {area}",
            "Chỗ nào uống {drink} ngon {area}", "Ở đâu có quán {drink} {cafefeat}",
        ],
        "en": [
            "Find a cafe {cafefeat} {area}", "Is there a cafe {cafefeat} {area}",
            "Recommend a place for {drink} {cafefeat}", "I want to drink {drink} {area}",
            "Is there a place for {drink} {cafefeat}", "Find a cafe where I can {worktask} {area}",
            "I need a place to sit and {worktask} {area}", "Suggest a place for {drink} {cafefeat} for {group}",
            "Recommend a coffee shop {cafefeat} where I can {worktask}",
            "Is there a place for {drink} nearby", "Where can I have {drink} {area}",
            "Where can I {worktask} in a cafe {cafefeat}",
            "I am looking for a {drink} spot {cafefeat} {area}",
            "I am going for {drink} with {group}. Which place {cafefeat} do you suggest",
            "I need a cafe {cafefeat} {area} to {worktask}", "Give me a few {drink} places {area}",
            "Which cafes stay open until late {area}", "Find a milk tea shop {cafefeat} {area}",
            "Where is the best place for {drink} {area}", "Where can I find a cafe {cafefeat}",
        ],
    },
    "attraction": {
        "vi": [
            "Gợi ý {atype} {area}", "Có {atype} nào đáng đi {area} không", "Tôi muốn tham quan {attr}",
            "{attr} có gì đặc biệt", "{attr} có đáng đi không", "Nên làm gì ở {attr}",
            "Giá vé tham quan {attr} là bao nhiêu", "{attr} mở cửa lúc mấy giờ",
            "Tôi thích {interest}, nên đến đâu {area}", "Tìm {atype} cho {group} {area}",
            "Đà Nẵng có {atype} nào nổi tiếng", "Cho mình biết những {atype} đáng ghé thăm {area}",
            "Lần đầu đến Đà Nẵng, nên tham quan {atype} nào", "Có {atype} nào miễn phí {area} không",
            "Gợi ý nơi tham quan phù hợp với {group}", "Thời điểm nào đẹp nhất để đến {attr}",
            "Nơi nào đáng ghé thăm nếu tôi thích {interest}", "Giới thiệu về {attr} cho khách du lịch",
            "Có điểm tham quan nào {area} phù hợp với {group}", "{attr} có phù hợp cho {group} không",
        ],
        "en": [
            "Recommend {atype} {area}", "Are there any {atype} worth visiting {area}",
            "I want to visit {attr}", "What makes {attr} special", "Is {attr} worth visiting",
            "What can I do at {attr}", "How much is the entrance ticket for {attr}",
            "What are the opening hours of {attr}", "I love {interest}. Where should I go {area}",
            "Find {atype} for {group} {area}", "What are the most famous {atype} in Da Nang",
            "Tell me about {atype} worth visiting {area}",
            "This is my first time in Da Nang. Which {atype} should I see",
            "Are there any {atype} {area} that are free", "Suggest a place to visit that suits {group}",
            "When is the best time to visit {attr}", "If I enjoy {interest}, which places should I visit",
            "Give a short introduction to {attr} for tourists",
            "Which attractions {area} are good for {group}", "Is {attr} suitable for {group}",
        ],
    },
    "itinerary": {
        "vi": [
            "Lập lịch trình {duration} ở Đà Nẵng", "Lập lịch trình {duration} ở Đà Nẵng cho {group}",
            "Tôi có {duration} ở Đà Nẵng, nên đi đâu và làm gì",
            "Lên kế hoạch du lịch với ngân sách {budget} cho {group}",
            "Sắp xếp lịch trình kết hợp {combo}", "Lập lịch trình {duration} {constraint}",
            "Tôi có {budget} cho {duration}, hãy lên kế hoạch đi chơi",
            "Sắp xếp thứ tự tham quan {attr} và {attr2} trong một ngày",
            "Hãy tạo lịch trình {duration} kết hợp {combo}",
            "Lên kế hoạch cho chuyến đi {duration} với ngân sách {budget}",
            "Tạo lịch trình tối ưu thời gian di chuyển giữa {attr} và {attr2}",
            "Tôi muốn một lịch trình {constraint}, đi trong {duration}",
            "Gợi ý kế hoạch du lịch Đà Nẵng {duration} cho {group}",
            "Giúp tôi lên kế hoạch tham quan {attr} và ăn uống gần đó trong một ngày",
            "Sắp xếp các điểm đến trong {duration} sao cho ít phải đi lại",
            "Lập kế hoạch đi chơi {duration} {constraint} cho {group}",
            "Tạo hành trình {duration} có cả điểm tham quan, quán ăn và quán cà phê",
            "Chia lịch trình {duration} thành từng buổi sáng, chiều, tối",
            "Hãy đề xuất tour {duration} tiết kiệm với ngân sách {budget}",
            "Lập kế hoạch từng ngày cho chuyến đi Đà Nẵng {duration}",
        ],
        "en": [
            "Plan my itinerary for {duration} in Da Nang",
            "Create an itinerary for {duration} in Da Nang for {group}",
            "I have {duration} in Da Nang. What should I do and where should I go",
            "Plan a trip with a budget of {budget} for {group}",
            "Create an itinerary that combines {combo}", "Create an itinerary for {duration} {constraint}",
            "I have {budget} for {duration}. Please plan my trip",
            "Arrange the best order to visit {attr} and {attr2} in one day",
            "Make a schedule for {duration} combining {combo}",
            "Plan a trip for {duration} on a budget of {budget}",
            "Build a route that minimizes travel time between {attr} and {attr2}",
            "Make a travel plan for {duration}, {constraint}",
            "Suggest a travel plan for {group} who have {duration} in Da Nang",
            "Help me plan a day visiting {attr} and eating nearby",
            "Arrange my stops over {duration} so I travel as little as possible",
            "Plan an outing for {group} for {duration} {constraint}",
            "Create a route for {duration} that includes sights, restaurants and cafes",
            "Split my plan for {duration} into morning, afternoon and evening",
            "Propose a cheap tour for {duration} within {budget}",
            "Write a day-by-day plan for my Da Nang trip lasting {duration}",
        ],
    },
    "transport": {
        "vi": [
            "Đi từ {node} đến {node2} bằng gì", "Từ {node} đến {node2} đi như thế nào",
            "Chỉ đường từ {node} đến {node2}", "Đi từ {node} đến {node2} mất bao lâu",
            "Nên đi {mode} hay {mode2} từ {node} đến {node2}",
            "Giá {mode} từ {node} đến {node2} khoảng bao nhiêu",
            "Thuê {rent} ở Đà Nẵng giá bao nhiêu", "Có tuyến xe buýt nào đến {node2} không",
            "Có dịch vụ đưa đón từ {node} không", "Chỗ đậu xe gần {node2}",
            "Cách di chuyển quanh Đà Nẵng cho {group}", "Tôi muốn thuê {rent} để đi {node2}",
            "Đi {mode} từ {node} đến {node2} có tiện không", "Làm sao để đến {node2} từ {node}",
            "Từ {node} đến {node2} cách nhau bao xa", "Tìm chỗ thuê {rent} gần {node}",
            "Đường nào nhanh nhất để đến {node2}", "Đi {mode} đến {node2} có an toàn vào buổi tối không",
            "Có thể đi bộ từ {node} đến {node2} không", "Phương tiện nào phù hợp cho {group} đi {node2}",
        ],
        "en": [
            "What is the best way to get from {node} to {node2}", "How do I get from {node} to {node2}",
            "Give me directions from {node} to {node2}",
            "How long does it take to travel from {node} to {node2}",
            "Should I take {mode} or {mode2} from {node} to {node2}",
            "How much is {mode} from {node} to {node2}", "Where can I rent {rent} in Da Nang",
            "Is there a bus to {node2}", "Is there a shuttle service from {node}",
            "Where can I park near {node2}", "How can I get around Da Nang with {group}",
            "I want to rent {rent} to go to {node2}",
            "Is {mode} from {node} to {node2} convenient", "How can I reach {node2} from {node}",
            "How far is {node2} from {node}", "Where can I rent {rent} near {node}",
            "What is the fastest route to {node2}", "Is {mode} to {node2} safe at night",
            "Can I walk from {node} to {node2}", "What transport suits {group} going to {node2}",
        ],
    },
    # ------------------------- nhan bo sung (--extra-labels) -------------------------
    "accommodation": {
        "vi": [
            "Tìm {htype} {hfeat} {area}", "Gợi ý {htype} giá dưới {budget} một đêm",
            "Tôi cần đặt phòng {htype} cho {group}", "Có {htype} nào {hfeat} {area} không",
            "Nên ở {htype} nào {area}", "Tìm chỗ ở {hfeat} cho {group}",
            "{htype} nào đáng ở nhất {area}", "Tôi muốn thuê {htype} trong {duration}",
            "So sánh {htype} và {htype2} {area}", "Giá phòng {htype} {area} khoảng bao nhiêu",
        ],
        "en": [
            "Find a {htype} {hfeat} {area}", "Suggest a {htype} under {budget} per night",
            "I need to book a {htype} for {group}", "Is there a {htype} {hfeat} {area}",
            "Which {htype} should I stay at {area}", "Find accommodation {hfeat} for {group}",
            "What is the best {htype} {area}", "I want to book a {htype} for {duration}",
            "Compare a {htype} and a {htype2} {area}", "How much is a {htype} room {area}",
        ],
    },
    "weather": {
        "vi": [
            "Thời tiết Đà Nẵng {wtime} thế nào", "Trời có mưa {wtime} không",
            "Mùa nào đẹp nhất để du lịch Đà Nẵng", "Dự báo thời tiết {wtime} ở Đà Nẵng",
            "Biển Đà Nẵng {wtime} có sóng lớn không", "Nhiệt độ ở Đà Nẵng {wtime} bao nhiêu độ",
            "{wtime} có bão không", "Có nên mang áo mưa khi đi chơi {wtime} không",
            "Trời {wtime} nóng hay lạnh", "Tôi nên mặc gì khi đi biển {wtime}",
            "Thời tiết {wtime} ở Hội An ra sao", "Đà Nẵng {wtime} có nắng không",
            "Độ ẩm ở Đà Nẵng {wtime} thế nào", "Tôi cần xem dự báo mưa {wtime}",
            "Gió biển {wtime} có mạnh không", "Đà Nẵng {wtime} có nắng nóng gay gắt không",
        ],
        "en": [
            "What is the weather like in Da Nang {wtime}", "Will it rain in Da Nang {wtime}",
            "What is the best season to visit Da Nang", "Give me the weather forecast for Da Nang {wtime}",
            "Are the waves big at the beach {wtime}", "What is the temperature in Da Nang {wtime}",
            "Is there a storm in Da Nang {wtime}", "Should I bring a raincoat when going out {wtime}",
            "Is it hot or cold in Da Nang {wtime}", "What should I wear to the beach {wtime}",
            "How is the weather in Hoi An {wtime}", "Will it be sunny in Da Nang {wtime}",
            "What is the humidity in Da Nang {wtime}", "I need the rain forecast for {wtime}",
            "Is the sea wind strong {wtime}", "Is it going to be very hot in Da Nang {wtime}",
        ],
    },
    "out_of_scope": {
        "vi": [
            "Viết giúp tôi {otask}", "Giải thích {oconcept} cho tôi", "Cho tôi biết {otopic}",
            "Giải {omath} giúp tôi", "Bạn có thể giải thích {oconcept} đơn giản không",
            "Hãy viết {otask}", "Tôi muốn biết {otopic}", "{oconcept} là gì",
            "Tóm tắt giúp tôi {oconcept} trong ba câu", "Tôi cần bạn giải {omath}",
            "Cho tôi ví dụ về {oconcept}", "So sánh {oconcept} và {oconcept2}",
            "Hướng dẫn tôi học {oconcept} từ đầu", "Bạn nghĩ gì về {oconcept}",
            "Viết {otask} dưới 100 từ", "Nói cho tôi nghe về {oconcept} bằng ngôn ngữ đơn giản",
        ],
        "en": [
            "Write {otask} for me", "Explain {oconcept} to me", "Tell me {otopic}",
            "Solve {omath} for me", "Can you explain {oconcept} in simple terms",
            "Please write {otask}", "I want to know {otopic}", "What is {oconcept}",
            "Summarize {oconcept} in three sentences", "I need you to solve {omath}",
            "Give me an example of {oconcept}", "Compare {oconcept} and {oconcept2}",
            "How do I start learning {oconcept}", "What do you think about {oconcept}",
            "Write {otask} in under 100 words", "Describe {oconcept} in plain language",
        ],
    },
}

# ---------------------------------------------------------------------------
# BIEN THE TU NHIEN
# ---------------------------------------------------------------------------
OPENERS = {
    "vi": ["", "", "", "", "Cho mình hỏi, ", "Bạn ơi, ", "Xin chào, ", "Giúp mình với, ",
           "Mình đang ở Đà Nẵng, ", "Cho tôi hỏi, ", "Ê, ", "Alo, "],
    "en": ["", "", "", "", "Hi, ", "Hello, ", "Excuse me, ", "Hey, ", "Quick question: ",
           "I am in Da Nang. ", "Can you help me? "],
}
CLOSERS = {
    "vi": ["", "", "", "", " nhé", " giúp mình với", " với ạ", " nha", " được không?"],
    "en": ["", "", "", "", " please", " thanks", " if possible", " for me"],
}
FORMATTER = string.Formatter()


def strip_accents(text):
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def norm_key(text):
    """Khoa chong trung: bo dau, bo dau cau, viet thuong."""
    text = strip_accents(str(text)).casefold()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def fill(template, lang, rng):
    chosen, values = {}, {}
    for _, field, _, _ in FORMATTER.parse(template):
        if not field:
            continue
        base = field.rstrip("0123456789")
        pair = rng.choice(SLOTS[base])
        for _ in range(12):  # tranh chon trung gia tri trong cung mot cau
            if pair not in chosen.get(base, []):
                break
            pair = rng.choice(SLOTS[base])
        chosen.setdefault(base, []).append(pair)
        values[field] = pair[0 if lang == "vi" else 1]
    text = template.format(**values)
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s+([?.,!])", r"\1", text)


def add_typo(text, rng):
    words = text.split()
    candidates = [i for i, w in enumerate(words) if len(w) >= 5 and w.isalpha()]
    if not candidates:
        return text
    i = rng.choice(candidates)
    w = words[i]
    j = rng.randrange(1, len(w) - 2)
    words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
    return " ".join(words)


def decorate(core, template, lang, rng):
    opener = rng.choice(OPENERS[lang])
    if ("Đà Nẵng" in opener or "Da Nang" in opener) and ("Đà Nẵng" in core or "Da Nang" in core):
        opener = ""  # tranh lap "o Da Nang ... Da Nang"
    proper_starts = ("I ", "I'", "Đà Nẵng", "Da Nang", "Hội An", "Hoi An", "Grab")
    if opener and not template.startswith("{") and not core.startswith(proper_starts):
        core = core[0].lower() + core[1:]
    closer = rng.choice(CLOSERS[lang])
    punct = "" if closer.endswith("?") else rng.choice(["", "", ".", "?"])
    text = f"{opener}{core}{closer}{punct}".strip()
    text = text[0].upper() + text[1:]

    # nhieu: nguoi dung thuc te hay go khong dau, viet thuong, thieu dau cau
    if lang == "vi" and rng.random() < 0.15:
        text = strip_accents(text)
    if rng.random() < 0.30:
        text = text.lower()
    if rng.random() < 0.35:
        text = re.sub(r"[?.!,]", "", text)
    if lang == "en" and rng.random() < 0.06:
        text = add_typo(text, rng)
    return text.strip()


def split_templates(templates):
    train = [t for i, t in enumerate(templates) if i % 5 != 4]
    held_out = [t for i, t in enumerate(templates) if i % 5 == 4]
    return train, held_out


def generate(label, lang, templates, n, rng, seen):
    rows, attempts = [], 0
    while len(rows) < n and attempts < n * 60:
        attempts += 1
        template = rng.choice(templates)
        text = decorate(fill(template, lang, rng), template, lang, rng)
        key = norm_key(text)
        if len(key) < 6 or key in seen:
            continue
        seen.add(key)
        rows.append({"text": text, "label": label, "lang": lang})
    if len(rows) < n:
        print(f"  [canh bao] {label}/{lang}: chi tao duoc {len(rows)}/{n} mau doc nhat "
              f"- hay them mau cau hoac gia tri cho nhan nay.")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--total", type=int, default=60000, help="Tong so mau train (50000-80000)")
    parser.add_argument("--eval-ratio", type=float, default=0.10, help="Ty le tap eval so voi train")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--extra-labels", action="store_true",
                        help="Them nhan accommodation, weather, out_of_scope")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    labels = CORE_LABELS + (EXTRA_LABELS if args.extra_labels else [])

    seen = set()
    if HUMAN_PATH.exists():
        human = pd.read_csv(HUMAN_PATH)
        seen.update(norm_key(t) for t in human["text"].dropna())
        print(f"Da nap {len(seen)} cau viet tay de loai trung: {HUMAN_PATH}")

    per_label_train = args.total // len(labels)
    per_label_eval = int(per_label_train * args.eval_ratio)

    train_rows, eval_rows = [], []
    for label in labels:
        for lang in ("vi", "en"):
            train_tpl, eval_tpl = split_templates(TEMPLATES[label][lang])
            if not eval_tpl:
                raise ValueError(f"{label}/{lang} can it nhat 5 mau cau.")
            n_tr = per_label_train // 2 + (per_label_train % 2 if lang == "vi" else 0)
            n_ev = per_label_eval // 2
            train_rows += generate(label, lang, train_tpl, n_tr, rng, seen)
            eval_rows += generate(label, lang, eval_tpl, n_ev, rng, seen)

    train_df = pd.DataFrame(train_rows).sample(frac=1, random_state=args.seed).reset_index(drop=True)
    eval_df = pd.DataFrame(eval_rows).sample(frac=1, random_state=args.seed).reset_index(drop=True)
    train_df["source"] = "synthetic_train"
    eval_df["source"] = "synthetic_eval"

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    train_path = DATA_DIR / "intents_synthetic_train.csv"
    eval_path = DATA_DIR / "intents_synthetic_eval.csv"
    train_df.to_csv(train_path, index=False, encoding="utf-8-sig")
    eval_df.to_csv(eval_path, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print(f"TRAIN: {len(train_df)} mau  ->  {train_path}")
    print(train_df.groupby(["label", "lang"]).size().unstack().to_string())
    print(f"\nEVAL (mau cau giu rieng): {len(eval_df)} mau  ->  {eval_path}")
    print("\n10 mau ngau nhien de kiem tra bang mat:")
    print(train_df.sample(10, random_state=1)[["text", "label"]].to_string(index=False))


if __name__ == "__main__":
    main()
