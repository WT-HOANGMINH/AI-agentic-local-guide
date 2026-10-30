"""Diễn đạt câu trả lời. Nội dung (số phút, tên điểm, ngày...) do planner/dialogue tính; ở đây chỉ chọn cách nói."""
import random
import re

from backend.services.slot_service import strip_accents

VI_CHARS = re.compile(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]")
VI_W = {"toi", "minh", "muon", "di", "an", "quan", "cho", "ngay", "khong", "gi", "nhieu", "dau", "giup",
        "lich", "trinh", "thich", "bien"}
EN_W = {"i", "want", "the", "to", "in", "a", "what", "where", "how", "plan", "trip", "go", "with", "for",
        "please", "is", "can", "my"}
LABEL = {"beach": ("biển", "beaches"), "nature": ("thiên nhiên", "nature"), "culture": ("văn hóa", "culture"),
         "food": ("ẩm thực", "food"), "sunset": ("hoàng hôn", "sunsets"), "photo": ("chụp ảnh", "photo spots")}


def detect_lang(text, default="vi"):
    if VI_CHARS.search(text.lower()):
        return "vi"
    toks = set(strip_accents(text).split())
    v, e = len(toks & VI_W), len(toks & EN_W)
    return default if v == e else ("vi" if v > e else "en")


def label(i, lang):
    return LABEL.get(i, (i, i))[0 if lang == "vi" else 1]


T = {
    "greet": {"vi": ["Chào bạn! Mình là DaNang Guide. Bạn muốn tìm quán ăn, địa điểm tham quan hay lên lịch trình ở Đà Nẵng?",
                     "Xin chào! Hôm nay bạn muốn khám phá gì ở Đà Nẵng: ăn uống, tham quan hay một lịch trình trọn gói?"],
              "en": ["Hi! I'm DaNang Guide. Are you after food, sights, or a full itinerary in Da Nang?"]},
    "offscope": {"vi": ["Câu này nằm ngoài phạm vi du lịch Đà Nẵng của mình. Bạn thử hỏi về địa điểm, ăn uống hay lịch trình nhé."],
                 "en": ["That's outside what I can help with. Ask me about places, food or itineraries in Da Nang."]},
    "ask_days_interest": {"vi": ["Mình giúp bạn lên lịch nhé 🌿 Bạn đi Đà Nẵng mấy ngày? Nếu đã có điểm muốn ghé hoặc món muốn thử, cứ kể luôn; còn sở thích thì có thể chọn biển, thiên nhiên, văn hóa hay ẩm thực. Chưa quyết được thì bấm “Tùy bạn”, mình sẽ gợi ý trước."],
                          "en": ["I'd love to help plan your trip 🌿 How many days will you be in Da Nang? Tell me any must-see places or food too. If you haven't decided on a style, choose “You decide” and I'll suggest a balanced plan."]},
    "ask_days": {"vi": ["Bạn dự định đi mấy ngày để mình xếp lịch cho vừa sức nhé?", "Chuyến đi của bạn kéo dài mấy ngày vậy?"],
                 "en": ["How many days are you planning to stay?"]},
    "ask_interest": {"vi": ["Bạn thích hướng nào hơn: biển, thiên nhiên, văn hóa hay ẩm thực? Nếu không có yêu cầu, bạn nói \"tùy bạn\" nhé."],
                     "en": ["What do you prefer: beaches, nature, culture or food? Say \"you decide\" if you have no preference."]},
    "ask_food": {"vi": ["Bạn muốn ăn bữa nào (sáng, trưa hay tối) và ở khu vực nào cho tiện? Có món nào bạn đang thèm không?"],
                 "en": ["Which meal is it (breakfast, lunch or dinner), and which area suits you? Any dish you're craving?"]},
    "ask_cafe": {"vi": ["Bạn cần quán cà phê để làm việc, trò chuyện hay ngắm view? Và gần khu vực nào?"],
                 "en": ["Do you need a cafe for work, chatting or the view? And near which area?"]},
    "ask_attraction": {"vi": ["Bạn thích loại địa điểm nào: biển, thiên nhiên, văn hóa hay chụp ảnh? Đi mấy người, khu vực nào cho tiện?"],
                       "en": ["What kind of places do you like: beaches, nature, culture or photo spots? Who's coming, and where are you staying?"]},
    "ask_accommodation": {"vi": ["Bạn cần chỗ ở khu vực nào, ngân sách khoảng bao nhiêu và đi mấy người?"],
                          "en": ["Which area, what budget and how many guests for your stay?"]},
    "ask_unclear": {"vi": ["Mình chưa chắc hiểu ý bạn. Bạn muốn gợi ý địa điểm, quán ăn, quán cà phê hay lên lịch trình?"],
                    "en": ["I'm not sure what you need. Places, food, cafes, or an itinerary?"]},
    "ask_transport": {"vi": ["Bạn đi từ đâu đến đâu? Cho mình tên hai địa điểm để ước tính thời gian di chuyển nhé."],
                      "en": ["Where are you going from and to? Give me two place names and I'll estimate the trip."]},
    "ask_which_place": {"vi": ["Bạn đang hỏi về địa điểm nào vậy?"], "en": ["Which place do you mean?"]},
    "no_weather": {"vi": ["Bản hiện tại của mình chưa có dữ liệu thời tiết. Bạn nên kiểm tra dự báo trước khi đi nhé."],
                   "en": ["I don't have weather data in this version. Please check the forecast before you go."]},
    "no_result": {"vi": ["Mình chưa tìm thấy chỗ nào khớp trong dữ liệu hiện có. Bạn thử mô tả khác đi nhé?"],
                  "en": ["I couldn't find a good match in my data. Could you describe it differently?"]},
    "search_followup": {"vi": ["Bạn muốn mình đưa chỗ nào vào lịch trình không?", "Muốn mình tìm thêm hay xếp vào lịch trình luôn?"],
                        "en": ["Want me to add any of these to an itinerary?"]},
    "plan_intro": {"vi": ["Mình đã lên lịch trình {n} ngày cho bạn{topic}.", "Đây là lịch trình {n} ngày mình xếp{topic}."],
                   "en": ["Here's a {n}-day plan for you{topic}."]},
    "plan_assumed": {"vi": ["Bạn chưa nói số ngày nên mình tạm xếp 1 ngày; cho mình biết số ngày để chỉnh lại nhé."],
                     "en": ["You didn't mention the length, so I assumed 1 day; tell me the real number and I'll adjust."]},
    "plan_popular": {"vi": ["Vì chưa rõ sở thích, mình ưu tiên các điểm được đánh giá tốt và phổ biến."],
                     "en": ["Since I don't know your preferences yet, I favored well-rated, popular spots."]},
    "plan_followup": {"vi": ["Bạn muốn chỉnh gì không? Ví dụ: \"đi Bà Nà từ sớm\", \"bỏ một điểm\", \"thêm bữa sáng ngày 1\"."],
                      "en": ["Want any changes? e.g. \"go to Ba Na earlier\", \"remove a stop\", \"add breakfast on day 1\"."]},
    "explain_saved": {"vi": ["Ngày {d}: mình gom các điểm gần nhau nên tổng di chuyển chỉ khoảng {t} phút, ít hơn khoảng {s} phút so với xếp theo thứ tự ban đầu."],
                      "en": ["Day {d}: I grouped nearby stops, so travel is about {t} min, roughly {s} min less than the original order."]},
    "explain_near": {"vi": ["Ngày {d}: mình xếp quanh khu {zones} để bạn đỡ phải đi lại, tổng di chuyển khoảng {t} phút."],
                     "en": ["Day {d}: I kept stops around {zones} to limit backtracking, about {t} min of travel."]},
    "explain_near2": {"vi": ["Ngày {d}: các điểm được xếp theo thứ tự gần nhau, tổng di chuyển khoảng {t} phút."],
                      "en": ["Day {d}: stops are ordered by proximity, about {t} min of travel."]},
    "explain_long": {"vi": ["{name} cần khoảng {h} giờ tham quan nên mình cho bắt đầu từ {start} và không xếp thêm điểm xa khác trong ngày."],
                     "en": ["{name} takes about {h} hours, so I start at {start} and avoid adding far-away stops that day."]},
    "explain_meal": {"vi": ["Các bữa ăn của ngày {d} được chọn ở quán gần điểm bạn vừa tham quan để tiện đường."],
                     "en": ["Meals on day {d} are picked near the stop before, to keep the route convenient."]},
    "explain_dropped": {"vi": ["Chưa xếp vừa trong lịch: {names}. Bạn có thể thêm một ngày nữa để đi các điểm này."],
                        "en": ["Didn't fit in the plan: {names}. You could add another day for them."]},
    "modify_which": {"vi": ["Bạn muốn bỏ hoặc thêm địa điểm nào? Cho mình tên điểm đó nhé."], "en": ["Which place do you mean?"]},
    "modify_which_time": {"vi": ["Bạn muốn đổi giờ cho ngày nào, hoặc đưa địa điểm nào lên trước?"], "en": ["Which day or place should I move?"]},
    "not_in_plan": {"vi": ["{name} hiện không có trong lịch trình của bạn."], "en": ["{name} isn't in your plan."]},
    "already_in_plan": {"vi": ["{name} đã có trong lịch trình (ngày {d}) rồi."], "en": ["{name} is already in your plan (day {d})."]},
    "modify_removed": {"vi": ["Đã bỏ {name} khỏi ngày {d} và xếp lại các điểm còn lại."], "en": ["Removed {name} from day {d} and rearranged the rest."]},
    "modify_added": {"vi": ["Đã thêm {name} vào ngày {d} và xếp lại cho hợp lý."], "en": ["Added {name} to day {d} and rearranged."]},
    "modify_time": {"vi": ["Đã chỉnh ngày {d}{pin}, bắt đầu từ {start} và xếp lại toàn bộ các điểm."],
                    "en": ["Updated day {d}{pin}, starting at {start}, and rearranged everything."]},
    "earliest": {"vi": ["{name} mở cửa lúc {t} theo dữ liệu hiện có, nên đây là giờ sớm nhất bạn có thể bắt đầu."],
                 "en": ["{name} opens at {t} in my data, so that's the earliest you can start."]},
    "moved": {"vi": ["Mình chuyển {name} sang ngày {d} vì ngày này còn thời gian và khá gần."],
              "en": ["I moved {name} to day {d}; it has room and is nearby."]},
    "route": {"vi": ["Từ {a} đến {b} khoảng {k} km, đi xe máy hoặc taxi mất chừng {t} phút."],
              "en": ["{a} to {b} is about {k} km, roughly {t} min by bike or taxi."]},
    "route_est": {"vi": ["Từ {a} đến {b} mình ước lượng khoảng {t} phút di chuyển (chưa có đủ dữ liệu vị trí để tính chính xác)."],
                  "en": ["{a} to {b} is roughly {t} min (not enough location data for a precise figure)."]},
    "ask_origin": {"vi": ["Bạn xuất phát từ đâu để mình chỉ đường đến {name}? Bạn có thể chia sẻ vị trí hiện tại hoặc chọn một điểm xuất phát bên dưới nhé."],
                   "en": ["Where are you starting from to get to {name}? Share your location or pick a starting point below."]},
    "route_gps": {"vi": ["Từ vị trí của bạn đến {b} khoảng {k} km, đi xe máy chừng {t} phút."],
                  "en": ["From your location to {b} is about {k} km, roughly {t} min by bike."]},
    "route_note": {"vi": ["Đây là ước lượng theo khoảng cách địa lý, chưa tính tắc đường. Để xem đường đi tối ưu theo giao thông thực tế, bạn bấm nút Google Maps bên dưới nhé."],
                   "en": ["This is a rough estimate that ignores traffic. Tap the Google Maps button below for the best live route."]},
    "route_text_origin": {"vi": ["Mình chưa có tọa độ của “{a}” nên chưa ước lượng được quãng đường tới {b}. Bạn bấm nút Google Maps bên dưới để xem đường đi tối ưu theo giao thông thực tế nhé."],
                          "en": ["I don't have coordinates for “{a}”, so I can't estimate the distance to {b}. Tap the Google Maps button below for the best live route."]},
    "closing": {"vi": ["Bạn cần mình giúp gì thêm không? Chúc bạn có một ngày đi chơi thật vui vẻ nhé! 🌴",
                       "Cần mình hỗ trợ thêm gì cứ nhắn nhé. Chúc bạn một chuyến đi thật vui và nhiều kỷ niệm đẹp! 🌅"],
                "en": ["Anything else I can help with? Have a wonderful day out! 🌴"]},
    "farewell": {"vi": ["Rất vui được giúp bạn! Chúc bạn có một ngày đi chơi thật vui vẻ. Cần gì cứ nhắn mình bất cứ lúc nào nhé 👋"],
                 "en": ["Glad I could help! Have a great trip, and message me anytime 👋"]},
    "day": {"vi": ["Ngày"], "en": ["Day"]},
    "meal_tag": {"vi": [" (ăn)"], "en": [" (meal)"]},
}


def say(key, lang, **kw):
    opts = T[key].get(lang) or T[key]["vi"]
    return random.choice(opts).format(**kw)


def search_intro(lang, near, meal):
    if lang == "vi":
        base = f"Quanh {near} mình thấy" if near else "Mình gợi ý"
        m = {"breakfast": " cho bữa sáng", "lunch": " cho bữa trưa", "dinner": " cho bữa tối"}.get(meal, "")
        return f"{base} vài chỗ phù hợp{m}:"
    base = f"Near {near} I'd suggest" if near else "I'd suggest"
    return f"{base} these{' for ' + meal if meal else ''}:"
