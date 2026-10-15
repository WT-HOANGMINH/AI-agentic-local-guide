// ============================================
// CONFIGURATION & CONSTANTS
// ============================================

// Base URL Backend API
export const API_BASE_URL = (() => {
    // Nếu trang đang chạy trực tiếp từ backend (cùng origin)
    if (window.location.port === "8000") {
        return window.location.origin;
    }
    // Mặc định kết nối tới FastAPI backend local
    return "http://127.0.0.1:8000";
})();

// Tọa độ trung tâm thành phố Đà Nẵng
export const DA_NANG = {
    lat: 16.0544,
    lng: 108.2022,
    defaultZoom: 13
};

// Ánh xạ danh mục địa điểm (Tên hiển thị, icon emoji, màu sắc)
export const CATEGORIES = {
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
export const QUICK_TAGS = [
    { label: "Cầu Rồng", query: "Cầu Rồng" },
    { label: "Bà Nà Hills", query: "Bà Nà" },
    { label: "Bán đảo Sơn Trà", query: "Sơn Trà" },
    { label: "Bánh xèo", query: "Bánh xèo" },
    { label: "Quán cafe", query: "Cafe" },
    { label: "Chợ Hàn", query: "Chợ Hàn" }
];

// Dữ liệu mẫu phong phú của Đà Nẵng dự phòng khi Database trống hoặc chưa khởi động MySQL
export const MOCK_PLACES = [
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
        is_active: true
    }
];
