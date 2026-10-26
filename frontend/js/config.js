// ============================================
// CONFIGURATION & CONSTANTS
// ============================================

// Base URL Backend API
const API_BASE_URL = (() => {
    // Nếu trang đang chạy trực tiếp từ backend (cùng origin)
    if (typeof window !== "undefined" && window.location.port === "8000") {
        return window.location.origin;
    }
    // Mặc định kết nối tới FastAPI backend local
    return "http://127.0.0.1:8000";
})();

// Tọa độ trung tâm thành phố Đà Nẵng
const DA_NANG = {
    lat: 16.0544,
    lng: 108.2022,
    defaultZoom: 13
};

// Ánh xạ danh mục địa điểm (Tên hiển thị, icon emoji, màu sắc)
const CATEGORIES = {
    tourist_attraction: {
        name: "Điểm tham quan",
        icon: "🏛️",
        color: "#0284c7",
        bg: "#e0f2fe"
    },
    restaurant: {
        name: "Nhà hàng & Ẩm thực",
        icon: "🍲",
        color: "#ea580c",
        bg: "#ffedd5"
    },
    cafe: {
        name: "Quán cà phê",
        icon: "☕",
        color: "#854d0e",
        bg: "#fef9c3"
    },
    shopping: {
        name: "Mua sắm & Chợ",
        icon: "🛍️",
        color: "#7c3aed",
        bg: "#ede9fe"
    }
};

// Danh sách gợi ý từ khóa tìm kiếm nhanh
const QUICK_TAGS = [
    { key: "tag.dragon_bridge", label: "Cầu Rồng", query: "Cầu Rồng" },
    { key: "tag.bana", label: "Bà Nà Hills", query: "Bà Nà" },
    { key: "tag.sontra", label: "Bán đảo Sơn Trà", query: "Sơn Trà" },
    { key: "tag.banhxeo", label: "Bánh xèo", query: "Bánh xèo" },
    { key: "tag.cafe", label: "Quán cafe", query: "Cafe" },
    { key: "tag.chohan", label: "Chợ Hàn", query: "Chợ Hàn" }
];

// Dữ liệu mẫu phong phú của Đà Nẵng dự phòng khi Database trống hoặc chưa khởi động MySQL
const MOCK_PLACES = [
    {
        id: 101,
        name: "Cầu Rồng Đà Nẵng",
        category: "tourist_attraction",
        address: "Đường Nguyễn Văn Linh, P. Phước Ninh, Q. Hải Châu, Đà Nẵng",
        description: "Biểu tượng kiến trúc độc đáo của thành phố với khả năng phun lửa và phun nước vào 21:00 tối thứ 7 và Chủ nhật hàng tuần.",
        latitude: 16.0611,
        longitude: 108.2272,
        price_level: 1,
        opening_hours: "Mở cả ngày (Phun lửa 21:00 Thứ 7 & CN)",
        is_active: true
    },
    {
        id: 102,
        name: "Sun World Bà Nà Hills & Cầu Vàng",
        category: "tourist_attraction",
        address: "Xã Hòa Phú, Huyện Hòa Vang, Đà Nẵng",
        description: "Quần thể du lịch nghỉ dưỡng trên đỉnh núi Chúa với Cầu Vàng trứ danh thế giới, Làng Pháp cổ kính và khí hậu 4 mùa trong 1 ngày.",
        latitude: 15.9988,
        longitude: 107.9877,
        price_level: 4,
        opening_hours: "07:30 - 21:30 hàng ngày",
        image: "images/banahills.jpg",
        is_active: true
    },
    {
        id: 103,
        name: "Chùa Linh Ứng - Bán Đảo Sơn Trà",
        category: "tourist_attraction",
        address: "Bãi Bụt, Bán đảo Sơn Trà, P. Thọ Quang, Q. Sơn Trà, Đà Nẵng",
        description: "Ngôi chùa thanh tịnh hướng biển với tượng Phật Bà Quan Âm cao 67 mét sừng sững nhìn ra biển Đông và toàn cảnh vịnh Đà Nẵng.",
        latitude: 16.1002,
        longitude: 108.2758,
        price_level: 1,
        opening_hours: "06:00 - 20:30 hàng ngày",
        image: "images/chualinhung.jpg",
        is_active: true
    },
    {
        id: 104,
        name: "Bãi biển Mỹ Khê",
        category: "tourist_attraction",
        address: "Đường Võ Nguyên Giáp, P. Phước Mỹ, Q. Sơn Trà, Đà Nẵng",
        description: "Được tạp chí Forbes bình chọn là một trong những bãi biển quyến rũ nhất hành tinh với bãi cát trắng mịn và làn nước trong xanh.",
        latitude: 16.0594,
        longitude: 108.2464,
        price_level: 1,
        opening_hours: "Mở cả ngày",
        is_active: true
    },
    {
        id: 105,
        name: "Bánh Xèo Tôm Nhảy Bà Dưỡng",
        category: "restaurant",
        address: "K280/23 Hoàng Diệu, P. Bình Hiên, Q. Hải Châu, Đà Nẵng",
        description: "Thương hiệu bánh xèo giòn rụm nổi tiếng nhiều thập kỷ tại Đà Nẵng, nước chấm gan mè béo ngậy đặc trưng kèm nem lụi thơm lừng.",
        latitude: 16.0592,
        longitude: 108.2173,
        price_level: 2,
        opening_hours: "09:30 - 21:30",
        image: "images/banhxeobaduong.jpg",
        is_active: true
    },
    {
        id: 106,
        name: "Mì Quảng Bà Mua",
        category: "restaurant",
        address: "19-21 Trần Bình Trọng, Q. Hải Châu, Đà Nẵng",
        description: "Đặc sản mì Quảng gia truyền với tôm thịt đậm đà, trứng cút, gà ta và rau sống tươi ngon cùng bánh tráng mè nướng giòn.",
        latitude: 16.0645,
        longitude: 108.2198,
        price_level: 2,
        opening_hours: "06:30 - 22:00",
        image: "images/miquangbamua.png",
        is_active: true
    },
    {
        id: 107,
        name: "Trình Cà Phê - Không Gian Xanh & Vintage",
        category: "cafe",
        address: "34/4 Nguyễn Hữu Thọ, P. Hòa Thuận Nam, Q. Hải Châu, Đà Nẵng",
        description: "Quán cà phê mộc mạc phong cách vintage với cà phê bơ đặc sản béo ngậy, sân vườn xanh mát yên tĩnh để làm việc và thư giãn.",
        latitude: 16.0489,
        longitude: 108.2091,
        price_level: 2,
        opening_hours: "07:00 - 22:30",
        image: "images/trinhcaphe.jpg",
        is_active: true
    },
    {
        id: 108,
        name: "Wonderlust Danang - Cà phê Concept",
        category: "cafe",
        address: "96 Trần Phú, P. Hải Châu 1, Q. Hải Châu, Đà Nẵng",
        description: "Không gian kiến trúc mở hiện đại ngập tràn ánh sáng tự nhiên với trần kính lớn, đồ uống thanh mát và bánh ngọt chuẩn vị.",
        latitude: 16.0691,
        longitude: 108.2235,
        price_level: 2,
        opening_hours: "07:30 - 23:00",
        image: "images/wonderlustdanang.png",
        is_active: true
    },

    {
        id: 109,
        name: "Chợ Hàn Đà Nẵng",
        category: "shopping",
        address: "119 Đường Trần Phú, P. Hải Châu 1, Q. Hải Châu, Đà Nẵng",
        description: "Khu chợ truyền thống sầm uất ngay trung tâm thành phố, thiên đường mua sắm đặc sản Đà Nẵng như chả bò, mắm nêm, mực rim và quà lưu niệm.",
        latitude: 16.0682,
        longitude: 108.2248,
        price_level: 2,
        opening_hours: "06:00 - 19:00",
        is_active: true
    },
    {
        id: 110,
        name: "Chợ Đêm Sơn Trà",
        category: "shopping",
        address: "Đường Mai Hắc Đế, P. An Hải Trung, Q. Sơn Trà, Đà Nẵng (gần Cầu Rồng)",
        description: "Khu chợ đêm sôi động với hàng trăm gian hàng ẩm thực đường phố, hải sản nướng thơm nức mũi và đồ thủ công mỹ nghệ.",
        latitude: 16.0617,
        longitude: 108.2325,
        price_level: 2,
        opening_hours: "18:00 - 24:00 hàng ngày",
        image: "images/chodemsontra.jpg",
        is_active: true
    },
    {
        id: 111,
        name: "Bãi biển Non Nước",
        category: "tourist_attraction",
        address: "Đường Huyền Trân Công Chúa, Hòa Hải, Ngũ Hành Sơn, Đà Nẵng",
        description: "Bãi cát trắng mịn thoai thoải và làn nước trong xanh ngay dưới chân Ngũ Hành Sơn, không gian êm đềm thích hợp tắm biển và nghỉ dưỡng.",
        latitude: 16.0004,
        longitude: 108.2696,
        price_level: 1,
        opening_hours: "Mở cửa cả ngày",
        image: "images/biennonnuoc.jpg",
        is_active: true
    },
    {
        id: 112,
        name: "Nhà thờ Chính tòa Đà Nẵng",
        category: "tourist_attraction",
        address: "156 Trần Phú, Hải Châu 1, Hải Châu, Đà Nẵng",
        description: "Nhà thờ kiến trúc Gothic Pháp với gam màu hồng phấn độc đáo và cột thu lôi hình con gà trên đỉnh tháp chuông (thường gọi là nhà thờ Con Gà).",
        latitude: 16.0670,
        longitude: 108.2237,
        price_level: 1,
        opening_hours: "Tham quan bên ngoài cả ngày; giờ lễ sáng và chiều",
        image: "images/nhathochinhtoa.png",
        is_active: true
    },
    {
        id: 113,
        name: "Làng đá mỹ nghệ Non Nước",
        category: "tourist_attraction",
        address: "Huyền Trân Công Chúa, Hòa Hải, Ngũ Hành Sơn, Đà Nẵng",
        description: "Làng nghề truyền thống hơn 400 năm tuổi nổi tiếng với các tác phẩm tượng Phật, linh vật và đồ trang sức bằng đá cẩm thạch tinh xảo.",
        latitude: 16.0030,
        longitude: 108.2650,
        price_level: 1,
        opening_hours: "07:00 - 17:30 hằng ngày",
        image: "images/langdamynghenonnuoc.png",
        is_active: true
    },
    {
        id: 114,
        name: "Đèo Hải Vân",
        category: "tourist_attraction",
        address: "Đèo Hải Vân, Hòa Hiệp Bắc, Liên Chiểu, Đà Nẵng",
        description: "Thiên hạ đệ nhất hùng quan với những cung đường đèo uốn lượn ven biển ngoạn mục, đỉnh đèo có Hải Vân Quan nhìn bao quát vịnh Lăng Cô và Đà Nẵng.",
        latitude: 16.2005,
        longitude: 108.1280,
        price_level: 1,
        opening_hours: "Mở cửa cả ngày",
        image: "images/deohaivan.jpg",
        is_active: true
    },
    {
        id: 115,
        name: "Biển An Bàng",
        category: "tourist_attraction",
        address: "Đường Hai Bà Trưng, Cẩm An, Hội An, Quảng Nam",
        description: "Bãi biển thanh bình với bờ cát mịn trải dài, làn nước trong xanh êm ả cùng chuỗi quán cà phê và nhà hàng ven biển mộc mạc thư thái.",
        latitude: 15.9125,
        longitude: 108.3370,
        price_level: 2,
        opening_hours: "Mở cửa cả ngày",
        image: "images/bienanbang.png",
        is_active: true
    },
    {
        id: 116,
        name: "Làng gốm Thanh Hà",
        category: "tourist_attraction",
        address: "Đường Phạm Phán, Thanh Hà, Hội An, Quảng Nam",
        description: "Làng nghề gốm đất nung truyền thống hơn 500 năm tuổi bên dòng sông Thu Bồn, nơi du khách được tự tay chuốt gốm và chiêm ngưỡng công viên gốm độc đáo.",
        latitude: 15.8778,
        longitude: 108.3032,
        price_level: 1,
        opening_hours: "08:00 - 17:30 hằng ngày",
        image: "images/langgomthanhha.png",
        is_active: true
    },
    {
        id: 117,
        name: "Làng rau Trà Quế",
        category: "tourist_attraction",
        address: "Thôn Trà Quế, Cẩm Hà, Hội An, Quảng Nam",
        description: "Làng trồng rau hữu cơ truyền thống trứ danh với các loại rau thơm ngát bón bằng rong biển đầm Trà Quế, mang đến trải nghiệm làm nông dân mộc mạc.",
        latitude: 15.9015,
        longitude: 108.3325,
        price_level: 1,
        opening_hours: "07:30 - 18:00 hằng ngày",
        image: "images/langrautraque.jpg",
        is_active: true
    },
    {
        id: 118,
        name: "Bánh tráng cuốn thịt heo Trần",
        category: "restaurant",
        address: "4 Lê Duẩn, Hải Châu 1, Hải Châu, Đà Nẵng",
        description: "Thương hiệu ẩm thực Trần trứ danh với món bánh tráng cuốn thịt heo hai đầu da độc đáo, đĩa rau ghém rừng hơn chục loại và bát mắm nêm đậm đà thơm nức mũi.",
        latitude: 16.0715,
        longitude: 108.2212,
        price_level: 2,
        opening_hours: "09:00 - 22:00 hằng ngày",
        image: "images/banhtrangcuonthitheotran.jpg",
        is_active: true
    },
    {
        id: 119,
        name: "Bún chả cá Nguyễn Chí Thanh",
        category: "restaurant",
        address: "109 Nguyễn Chí Thanh, Hải Châu 1, Hải Châu, Đà Nẵng",
        description: "Quán bún chả cá gia truyền nức tiếng hơn 50 năm tại Đà Nẵng, nước dùng ngọt thanh hầm từ bí đỏ, bắp cải, ăn kèm chả cá thu chiên và hấp dai giòn béo ngậy.",
        latitude: 16.0688,
        longitude: 108.2195,
        price_level: 1,
        opening_hours: "06:00 - 22:00 hằng ngày",
        image: "images/bunchacanguyenchithanh.png",
        is_active: true
    },
    {
        id: 120,
        name: "Bánh mì Phượng",
        category: "restaurant",
        address: "2B Phan Châu Trinh, Cẩm Châu, Hội An, Quảng Nam",
        description: "Tiệm bánh mì Hội An vang danh quốc tế từng được đầu bếp Anthony Bourdain ca ngợi là 'bánh mì ngon nhất thế giới', ngập tràn pate gan béo ngậy và thịt nướng đậm đà.",
        latitude: 15.8798,
        longitude: 108.3328,
        price_level: 1,
        opening_hours: "06:30 - 21:30 hằng ngày",
        image: "images/banhmiphuong.jpg",
        is_active: true
    },
    {
        id: 121,
        name: "Cao lầu Thanh",
        category: "restaurant",
        address: "26 Thái Phiên, Minh An, Hội An, Quảng Nam",
        description: "Địa chỉ thưởng thức cao lầu cổ truyền mộc mạc đúng điệu phố Hội với sợi mì dai giòn ngâm nước tro cù lao Chàm, thịt xá xíu đậm vị và da heo chiên giòn rụm.",
        latitude: 15.8810,
        longitude: 108.3285,
        price_level: 1,
        opening_hours: "06:30 - 19:30 hằng ngày",
        image: "images/caolauthanh.jpg",
        is_active: true
    },
    {
        id: 122,
        name: "Cơm gà Bà Buội",
        category: "restaurant",
        address: "22 Phan Chu Trinh, Minh An, Hội An, Quảng Nam",
        description: "Quán cơm gà gia truyền từ những năm 1950, hạt cơm vàng ươm nấu từ nước luộc gà béo ngậy, thịt gà ta xé phay giòn dai trộn gỏi hành tây chua ngọt đậm đà.",
        latitude: 15.8792,
        longitude: 108.3298,
        price_level: 2,
        opening_hours: "11:00 - 20:00 hằng ngày",
        image: "images/comgababuoi.png",
        is_active: true
    },
    {
        id: 123,
        name: "Cộng Cà Phê Bạch Đằng",
        category: "cafe",
        address: "96-98 Bạch Đằng, Hải Châu 1, Hải Châu, Đà Nẵng",
        description: "Quán cà phê mang phong cách thời bao cấp độc đáo nhìn thẳng ra sông Hàn lộng gió, nổi tiếng với cà phê cốt dừa thơm béo và không gian hoài niệm.",
        latitude: 16.0702,
        longitude: 108.2255,
        price_level: 2,
        opening_hours: "07:00 - 23:30 hằng ngày",
        image: "images/congcaphebachdang.jpg",
        is_active: true
    },
    {
        id: 124,
        name: "Hội An Roastery",
        category: "cafe",
        address: "135 Trần Phú, Phường Minh An, Hội An, Quảng Nam",
        description: "Xưởng rang xay cà phê truyền thống với không gian gỗ ấm cúng giữa phố cổ Hội An, phục vụ cà phê pha phin nguyên chất đậm đà và đồ uống hảo hạng.",
        latitude: 15.8775,
        longitude: 108.3292,
        price_level: 2,
        opening_hours: "07:00 - 22:00 hằng ngày",
        image: "images/hoianroastery.png",
        is_active: true
    },
    {
        id: 125,
        name: "Faifo Coffee",
        category: "cafe",
        address: "130 Trần Phú, Phường Minh An, Hội An, Quảng Nam",
        description: "Quán cà phê trứ danh sở hữu tầng thượng ngắm hoàng hôn và toàn cảnh mái ngói rêu phong phố cổ Hội An đẹp như tranh vẽ.",
        latitude: 15.8774,
        longitude: 108.3298,
        price_level: 2,
        opening_hours: "07:00 - 22:00 hằng ngày",
        image: "images/faifocoffee.png",
        is_active: true
    },
    {
        id: 126,
        name: "Chợ Cồn",
        category: "shopping",
        address: "290 Hùng Vương, Vĩnh Trung, Hải Châu, Đà Nẵng",
        description: "Thiên đường ẩm thực đường phố và mua sắm đặc sản sầm uất bậc nhất Đà Nẵng với vô vàn món ngon miền Trung chuẩn vị, giá bình dân.",
        latitude: 16.0683,
        longitude: 108.2148,
        price_level: 1,
        opening_hours: "07:00 - 19:30 hằng ngày",
        image: "images/chocon.png",
        is_active: true
    },
    {
        id: 127,
        name: "Chợ Hội An",
        category: "shopping",
        address: "19 Trần Phú, Cẩm Châu, Hội An, Quảng Nam",
        description: "Khu chợ trung tâm cổ kính ven sông Thu Bồn, nơi hội tụ tinh hoa ẩm thực phố Hội như cao lầu, mì Quảng, bánh hoa hồng trắng và nông sản tươi ngon.",
        latitude: 15.8770,
        longitude: 108.3330,
        price_level: 1,
        opening_hours: "06:00 - 18:00 hằng ngày",
        image: "images/chohoian.png",
        is_active: true
    },
    {
        id: 128,
        name: "Chợ đêm Hội An",
        category: "shopping",
        address: "Đường Nguyễn Hoàng, Phường An Hội, Hội An, Quảng Nam",
        description: "Chợ đêm lung linh rực rỡ sắc màu đèn lồng ven sông Hoài, tấp nập du khách dạo chơi, thưởng thức món ngon đường phố và mua quà lưu niệm thủ công.",
        latitude: 15.8760,
        longitude: 108.3245,
        price_level: 2,
        opening_hours: "17:30 - 23:00 hằng ngày",
        image: "images/chodemhoian.png",
        is_active: true
    },
    {
        id: 129,
        name: "Công viên Văn hóa Ấn Tượng Hội An",
        category: "culture",
        address: "Cồn Hến, Phường Cẩm Nam, Thành phố Hội An, Quảng Nam",
        description: "Công viên chủ đề văn hóa sống động tái hiện ký ức thương cảng Hội An thế kỷ 16-17, với điểm nhấn là show diễn thực cảnh Ký Ức Hội An lớn nhất Việt Nam.",
        latitude: 15.8775,
        longitude: 108.3375,
        price_level: 3,
        opening_hours: "16:00 - 22:00 hằng ngày",
        image: "images/congvienantuonghoian.jpg",
        is_active: true
    },
    {
        id: 130,
        name: "Phố cổ Hội An",
        category: "tourist_attraction",
        address: "Phường Minh An, Thành phố Hội An, Quảng Nam",
        description: "Di sản Văn hóa Thế giới UNESCO với những dãy nhà cổ sơn vàng rêu phong, đèn lồng lung linh huyền ảo và Chùa Cầu linh thiêng soi bóng bên dòng sông Hoài.",
        latitude: 15.8778,
        longitude: 108.3280,
        price_level: 1,
        opening_hours: "Mở cửa cả ngày (Phố đi bộ: 09:00 - 11:00 & 15:00 - 21:30)",
        image: "images/phocohoian.jpg",
        is_active: true
    },
    {
        id: 131,
        name: "Rừng dừa Bảy Mẫu",
        category: "tourist_attraction",
        address: "Thôn Vạn Lăng, Xã Cẩm Thanh, Thành phố Hội An, Quảng Nam",
        description: "Khu du lịch sinh thái rừng dừa nước bạt ngàn được ví như miền Tây giữa lòng xứ Quảng, nổi tiếng với trải nghiệm chèo thuyền thúng và múa thúng xoay vòng điêu luyện.",
        latitude: 15.8655,
        longitude: 108.3685,
        price_level: 2,
        opening_hours: "07:00 - 17:30 hằng ngày",
        image: "images/rungduabaymau.jpg",
        is_active: true
    },
    {
        id: 132,
        name: "Chùa Cầu Hội An",
        category: "tourist_attraction",
        address: "Giao đường Trần Phú và Nguyễn Thị Minh Khai, Phường Minh An, Hội An, Quảng Nam",
        description: "Biểu tượng di sản hơn 400 năm tuổi của phố cổ Hội An, chiếc cầu ngói do các thương nhân Nhật Bản xây dựng vắt qua nhánh nhỏ sông Thu Bồn.",
        latitude: 15.8771,
        longitude: 108.3260,
        price_level: 1,
        opening_hours: "Mở cửa cả ngày (vé tham quan theo tuyến phố cổ)",
        image: "images/chuacauhoian.jpg",
        is_active: true
    },
    {
        id: 133,
        name: "Bãi Bụt",
        category: "tourist_attraction",
        address: "Bán đảo Sơn Trà, Thọ Quang, Sơn Trà, Đà Nẵng",
        description: "Vịnh biển tuyệt đẹp hình vòng cung dưới chân núi Sơn Trà và Chùa Linh Ứng, nước xanh ngọc bích êm sóng với hàng dừa nghiêng và bãi cát trắng mịn.",
        latitude: 16.1015,
        longitude: 108.2780,
        price_level: 1,
        opening_hours: "Mở cửa cả ngày",
        image: "images/baibut.png",
        is_active: true
    },
    {
        id: 134,
        name: "Công viên Đất nung Thanh Hà",
        category: "tourist_attraction",
        address: "Đường Phạm Phán, Phường Thanh Hà, Hội An, Quảng Nam",
        description: "Bảo tàng và công viên gốm lớn nhất Việt Nam với kiến trúc gạch nung đỏ độc đáo, nơi trưng bày các kiệt tác gốm và mô hình kỳ quan thế giới thu nhỏ.",
        latitude: 15.8778,
        longitude: 108.3032,
        price_level: 2,
        opening_hours: "08:00 - 17:30 hằng ngày",
        image: "images/congviendatnungthanhha.png",
        is_active: true
    }
];

// Cấu hình Global cho ứng dụng
window.API_BASE_URL = API_BASE_URL;
window.DA_NANG = DA_NANG;
window.CATEGORIES = CATEGORIES;
window.QUICK_TAGS = QUICK_TAGS;
window.MOCK_PLACES = MOCK_PLACES;

window.LOCAL_GUIDE_CONFIG = {
    USE_MOCK: false,
    API_BASE: '', // tự động nhận diện 127.0.0.1:8000 khi chạy qua cổng 5500
    TOKEN_KEY: 'localguide_token',
    GOOGLE_CLIENT_ID: '853984856354-131ekmamkn9sqn75mbckbbm0805ab21m.apps.googleusercontent.com',
    FACEBOOK_APP_ID: '1092777120272337'
};
