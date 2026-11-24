// ============================================
// INTERNATIONALIZATION (i18n) SERVICE
// English (EN) & Tiếng Việt (VI)
// ============================================

const LANG_STORAGE_KEY = "localguide_lang";

// Ngôn ngữ hiện tại (Mặc định: Tiếng Việt)
let currentLang = localStorage.getItem(LANG_STORAGE_KEY) || "vi";

// Danh sách các listener lắng nghe sự kiện đổi ngôn ngữ
const changeListeners = [];

// Từ điển đa ngôn ngữ hoàn chỉnh
const TRANSLATIONS = {
    vi: {
        // Tài liệu & Tiêu đề trang
        "doc.title": "Agentic AI Local Guide | Khám Phá Đà Nẵng",
        "doc.description": "Trợ lý du lịch thông minh, tìm kiếm địa điểm ăn uống, tham quan và bản đồ tương tác tại Đà Nẵng",

        // Topbar
        "topbar.brand_title_pre": "Local",
        "topbar.brand_title_highlight": "Guide",
        "topbar.brand_tagline": "AI Travel Companion",
        "topbar.location": "Đà Nẵng, Việt Nam",
        "topbar.api_link": "Backend API",
        "topbar.login": "Đăng nhập",
        "topbar.register": "Đăng ký",
        "topbar.default_user": "Người dùng",
        "topbar.role_member": "Thành viên",
        "topbar.role_admin": "Quản trị viên",
        "topbar.logout_title": "Đăng xuất khỏi tài khoản",
        "topbar.logout_aria": "Đăng xuất",

        // Sidebar Intro
        "intro.eyebrow": "YOUR LOCAL AI COMPANION",
        "intro.title": "Khám phá Đà Nẵng <span>theo cách của bạn.</span>",
        "intro.desc": "Tìm kiếm địa điểm tham quan đặc sắc, ẩm thực địa phương, quán cà phê và điểm vui chơi giải trí.",

        // Form Tìm kiếm & Bộ lọc
        "search.placeholder": "Bạn muốn khám phá gì ở Đà Nẵng?",
        "search.clear_title": "Xóa tìm kiếm",
        "search.clear_aria": "Xóa tìm kiếm",
        "search.cat_label": "Danh mục",
        "search.cat_all": "Tất cả danh mục",
        "search.cat_attraction": "🏛️ Điểm tham quan",
        "search.cat_restaurant": "🍲 Nhà hàng & Ẩm thực",
        "search.cat_cafe": "☕ Quán cà phê",
        "search.cat_shopping": "🛍️ Mua sắm & Chợ",

        "search.price_label": "Mức giá tối đa",
        "search.price_all": "Tất cả mức giá",
        "search.price_1": "₫ (Bình dân)",
        "search.price_2": "₫₫ (Hợp lý)",
        "search.price_3": "₫₫₫ (Trung cấp)",
        "search.price_4": "₫₫₫₫ (Cao cấp)",
        "search.price_5": "₫₫₫₫₫ (Thượng lưu)",

        "search.btn": "Khám phá ngay",
        "search.quick_tags_label": "Gợi ý:",

        // Quick tags
        "tag.dragon_bridge": "Cầu Rồng",
        "tag.bana": "Bà Nà Hills",
        "tag.sontra": "Bán đảo Sơn Trà",
        "tag.banhxeo": "Bánh xèo",
        "tag.cafe": "Quán cafe",
        "tag.chohan": "Chợ Hàn",

        // Kết quả & Thẻ địa điểm
        "results.heading": "Địa điểm gợi ý",
        "results.loading": "Đang tải...",
        "results.count": "{count} địa điểm",
        "places.loading_msg": "Đang tải danh sách địa điểm Đà Nẵng...",
        "places.empty_title": "Không tìm thấy địa điểm phù hợp",
        "places.empty_desc": "Hãy thử tìm bằng từ khóa khác hoặc điều chỉnh lại bộ lọc danh mục/mức giá.",
        "places.reset_filter": "Xóa bộ lọc",
        "places.no_address": "Chưa có địa chỉ",
        "places.no_hours": "Chưa cập nhật",
        "places.view_map": "Xem trên bản đồ &rarr;",
        "places.directions": "Chỉ đường Google Maps ↗",
        "places.price_unspecified": "Chưa cập nhật giá",

        // Tên danh mục hiển thị
        "cat.tourist_attraction": "Điểm tham quan",
        "cat.restaurant": "Nhà hàng & Ẩm thực",
        "cat.cafe": "Quán cà phê",
        "cat.shopping": "Mua sắm & Chợ",

        // Khu vực Bản đồ
        "map.title": "Bản đồ tương tác",
        "map.subtitle": "Khám phá trực quan các địa điểm",
        "map.route_btn": "Lộ trình Tour",
        "map.route_title": "Vẽ lộ trình du lịch Đà Nẵng mẫu",
        "map.area_btn": "Vùng Sơn Trà",
        "map.area_title": "Vẽ ranh giới Bán đảo Sơn Trà",
        "map.locate_btn": "Vị trí của tôi",
        "map.locate_title": "Xem vị trí hiện tại của tôi kèm bán kính",
        "map.reset_btn": "Về Đà Nẵng",
        "map.reset_title": "Đặt lại góc nhìn về trung tâm Đà Nẵng",
        "map.hint": "💡 Nhấp vào thẻ địa điểm hoặc ghim trên bản đồ để xem chi tiết và đường đi.",

        // Trạng thái kết nối Backend
        "map.status_connecting": "Đang kết nối Backend...",
        "map.status_online": "Đã kết nối Backend • {count} địa điểm",
        "map.status_demo": "Chế độ Demo • {count} địa điểm gợi ý",
        "map.status_offline": "Chế độ Demo (Offline) • {count} địa điểm",
        "map.offline_alert": "Backend chưa được kết nối hoặc chưa khởi chạy. Hệ thống đang hiển thị dữ liệu gợi ý mẫu để bạn trải nghiệm bản đồ và giao diện.",

        // Thông báo Toast Bản đồ
        "map.toast_reset": "Đã quay về trung tâm Đà Nẵng!",
        "map.toast_locating": "Đang xác định vị trí của bạn...",
        "map.toast_located": "Đã xác định vị trí & vẽ vùng bán kính 3km quanh bạn!",
        "map.toast_gps_unsupported": "Trình duyệt của bạn không hỗ trợ định vị GPS.",
        "map.toast_gps_denied": "Bạn đã từ chối quyền truy cập vị trí trên trình duyệt.",
        "map.toast_gps_unavailable": "Thông tin vị trí không khả dụng.",
        "map.toast_gps_timeout": "Hết thời gian yêu cầu vị trí.",
        "map.toast_gps_error": "Không thể lấy vị trí hiện tại.",
        "map.toast_route_hide": "Đã ẩn lộ trình du lịch.",
        "map.toast_route_show": "Đã vẽ Lộ trình du lịch 1 ngày khám phá Đà Nẵng!",
        "map.toast_area_hide": "Đã ẩn ranh giới Bán đảo Sơn Trà.",
        "map.toast_area_show": "Đã vẽ ranh giới Khu bảo tồn thiên nhiên Bán đảo Sơn Trà!",

        // Lớp bản đồ
        "map.layer_google": "🗺️ Bản đồ Google Maps",
        "map.layer_osm": "📍 Bản đồ Du lịch OSM",
        "map.layer_satellite": "🛰️ Bản đồ Vệ tinh",
        "map.user_pos_title": "📍 Vị trí hiện tại của bạn",
        "map.user_radius_desc": "Bán kính tìm kiếm khám phá xung quanh: <strong>3 km</strong>",

        // Điểm dừng Lộ trình tour
        "map.tour_1_title": "Cầu Rồng Đà Nẵng",
        "map.tour_1_desc": "Khởi hành chụp ảnh biểu tượng Cầu Rồng và bờ sông Hàn.",
        "map.tour_2_title": "Chợ Hàn Đà Nẵng",
        "map.tour_2_desc": "Mua sắm quà lưu niệm & thưởng thức đặc sản miền Trung.",
        "map.tour_3_title": "Bãi biển Mỹ Khê",
        "map.tour_3_desc": "Dạo biển, tắm mát và ngắm cảnh bờ biển đẹp nhất hành tinh.",
        "map.tour_4_title": "Chùa Linh Ứng Bãi Bụt (Sơn Trà)",
        "map.tour_4_desc": "Chiêm bái tượng Phật Bà cao 67m ngắm hoàng hôn vịnh Đà Nẵng.",
        "map.tour_5_title": "Danh thắng Ngũ Hành Sơn",
        "map.tour_5_desc": "Khám phá quần thể hang động và làng đá mỹ nghệ Non Nước.",

        // Footer
        "footer.ecosystem": "Hệ sinh thái AI hỗ trợ du lịch địa phương",

        // Modal Đăng nhập / Đăng ký
        "modal.title": "Tài khoản LocalGuide",
        "modal.tab_login": "Đăng nhập",
        "modal.tab_register": "Đăng ký",
        "modal.close_aria": "Đóng cửa sổ",
        "modal.email_label": "Địa chỉ Email",
        "modal.email_placeholder": "name@example.com",
        "modal.pass_label": "Mật khẩu",
        "modal.pass_placeholder": "Nhập mật khẩu của bạn",
        "modal.pass_placeholder_reg": "Tối thiểu 6 ký tự",
        "modal.confirm_pass_label": "Xác nhận mật khẩu",
        "modal.confirm_pass_placeholder": "Nhập lại mật khẩu để xác nhận",
        "modal.username_label": "Tên người dùng (Username)",
        "modal.username_placeholder": "nguyenvana (3-50 ký tự)",
        "modal.btn_login": "Đăng nhập",
        "modal.btn_register": "Tạo tài khoản",
        "modal.no_account": "Chưa có tài khoản?",
        "modal.have_account": "Đã có tài khoản?",
        "modal.link_register": "Đăng ký ngay",
        "modal.link_login": "Đăng nhập ngay",
        "modal.toggle_pass_aria": "Hiển thị mật khẩu",

        // Auth Toasts & Alerts
        "auth.login_success": "Đăng nhập thành công! Chào mừng bạn trở lại.",
        "auth.logout_success": "Đã đăng xuất khỏi tài khoản.",
        "auth.register_success": "Đăng ký thành công! Hãy đăng nhập để trải nghiệm.",
        "auth.error_prefix": "Lỗi xác thực: "
    },

    en: {
        // Document & Title
        "doc.title": "Agentic AI Local Guide | Explore Da Nang",
        "doc.description": "Smart AI-powered local travel assistant, discover attractions, food spots, cafes, and interactive map in Da Nang, Vietnam",

        // Topbar
        "topbar.brand_title_pre": "Local",
        "topbar.brand_title_highlight": "Guide",
        "topbar.brand_tagline": "AI Travel Companion",
        "topbar.location": "Da Nang, Vietnam",
        "topbar.api_link": "Backend API",
        "topbar.login": "Sign In",
        "topbar.register": "Sign Up",
        "topbar.default_user": "User",
        "topbar.role_member": "Member",
        "topbar.role_admin": "Admin",
        "topbar.logout_title": "Log out of account",
        "topbar.logout_aria": "Log out",

        // Sidebar Intro
        "intro.eyebrow": "YOUR LOCAL AI COMPANION",
        "intro.title": "Explore Da Nang <span>your own way.</span>",
        "intro.desc": "Discover must-visit attractions, authentic local cuisine, cozy cafes, and entertainment hubs.",

        // Search Form & Filters
        "search.placeholder": "What do you want to explore in Da Nang?",
        "search.clear_title": "Clear search",
        "search.clear_aria": "Clear search",
        "search.cat_label": "Category",
        "search.cat_all": "All categories",
        "search.cat_attraction": "🏛️ Attractions",
        "search.cat_restaurant": "🍲 Restaurants & Food",
        "search.cat_cafe": "☕ Cafes",
        "search.cat_shopping": "🛍️ Shopping & Markets",

        "search.price_label": "Max price",
        "search.price_all": "All price levels",
        "search.price_1": "₫ (Budget)",
        "search.price_2": "₫₫ (Moderate)",
        "search.price_3": "₫₫₫ (Mid-range)",
        "search.price_4": "₫₫₫₫ (Upscale)",
        "search.price_5": "₫₫₫₫₫ (Luxury)",

        "search.btn": "Explore now",
        "search.quick_tags_label": "Suggestions:",

        // Quick tags
        "tag.dragon_bridge": "Dragon Bridge",
        "tag.bana": "Ba Na Hills",
        "tag.sontra": "Son Tra Peninsula",
        "tag.banhxeo": "Crispy Pancake",
        "tag.cafe": "Coffee Shops",
        "tag.chohan": "Han Market",

        // Results & Place Cards
        "results.heading": "Suggested Places",
        "results.loading": "Loading...",
        "results.count": "{count} place(s)",
        "places.loading_msg": "Loading Da Nang places list...",
        "places.empty_title": "No matching places found",
        "places.empty_desc": "Try a different search keyword or adjust your category and price filters.",
        "places.reset_filter": "Reset filters",
        "places.no_address": "No address provided",
        "places.no_hours": "Not specified",
        "places.view_map": "View on map &rarr;",
        "places.directions": "Google Maps Directions ↗",
        "places.price_unspecified": "Price not specified",

        // Categories
        "cat.tourist_attraction": "Attractions",
        "cat.restaurant": "Restaurant & Food",
        "cat.cafe": "Cafes",
        "cat.shopping": "Shopping & Markets",

        // Map Section
        "map.title": "Interactive Map",
        "map.subtitle": "Visually explore destinations",
        "map.route_btn": "Tour Route",
        "map.route_title": "Draw sample Da Nang tour itinerary",
        "map.area_btn": "Son Tra Area",
        "map.area_title": "Draw Son Tra Peninsula boundary",
        "map.locate_btn": "My Location",
        "map.locate_title": "View my current location with radius",
        "map.reset_btn": "Reset View",
        "map.reset_title": "Reset view to Da Nang center",
        "map.hint": "💡 Click on a place card or map pin to view details and directions.",

        // Backend Status
        "map.status_connecting": "Connecting to Backend...",
        "map.status_online": "Connected to Backend • {count} places",
        "map.status_demo": "Demo Mode • {count} suggested places",
        "map.status_offline": "Demo Mode (Offline) • {count} places",
        "map.offline_alert": "Backend is not connected or not running yet. The system is showing sample curated places for you to explore the map and interface.",

        // Map Toasts
        "map.toast_reset": "Returned to Da Nang center!",
        "map.toast_locating": "Locating your position...",
        "map.toast_located": "Location found & 3km radius drawn around you!",
        "map.toast_gps_unsupported": "Your browser does not support GPS geolocation.",
        "map.toast_gps_denied": "You denied location access permission in your browser.",
        "map.toast_gps_unavailable": "Location information is unavailable.",
        "map.toast_gps_timeout": "Location request timed out.",
        "map.toast_gps_error": "Unable to retrieve current location.",
        "map.toast_route_hide": "Tour itinerary hidden.",
        "map.toast_route_show": "Sample 1-day Da Nang tour itinerary drawn!",
        "map.toast_area_hide": "Son Tra Peninsula boundary hidden.",
        "map.toast_area_show": "Son Tra Peninsula Nature Reserve boundary drawn!",

        // Map Layers
        "map.layer_google": "🗺️ Google Maps",
        "map.layer_osm": "📍 OSM Tourist Map",
        "map.layer_satellite": "🛰️ Satellite Map",
        "map.user_pos_title": "📍 Your current location",
        "map.user_radius_desc": "Nearby discovery search radius: <strong>3 km</strong>",

        // Tour Waypoints
        "map.tour_1_title": "Dragon Bridge Da Nang",
        "map.tour_1_desc": "Start the tour photographing the iconic Dragon Bridge and Han River banks.",
        "map.tour_2_title": "Han Market Da Nang",
        "map.tour_2_desc": "Shop souvenirs & taste Central Vietnam specialties.",
        "map.tour_3_title": "My Khe Beach",
        "map.tour_3_desc": "Stroll along the beach, swim, and admire one of the world's best coastlines.",
        "map.tour_4_title": "Linh Ung Pagoda Bai But (Son Tra)",
        "map.tour_4_desc": "Admire the 67m Lady Buddha statue and sunset over Da Nang Bay.",
        "map.tour_5_title": "Marble Mountains",
        "map.tour_5_desc": "Explore caves, sacred shrines, and Non Nuoc stone carving village.",

        // Footer
        "footer.ecosystem": "AI ecosystem for local travel assistance",

        // Auth Modal
        "modal.title": "LocalGuide Account",
        "modal.tab_login": "Sign In",
        "modal.tab_register": "Sign Up",
        "modal.close_aria": "Close dialog",
        "modal.email_label": "Email Address",
        "modal.email_placeholder": "name@example.com",
        "modal.pass_label": "Password",
        "modal.pass_placeholder": "Enter your password",
        "modal.pass_placeholder_reg": "At least 6 characters",
        "modal.confirm_pass_label": "Confirm Password",
        "modal.confirm_pass_placeholder": "Re-enter password to confirm",
        "modal.username_label": "Username",
        "modal.username_placeholder": "johndoe (3-50 characters)",
        "modal.btn_login": "Sign In",
        "modal.btn_register": "Create Account",
        "modal.no_account": "Don't have an account?",
        "modal.have_account": "Already have an account?",
        "modal.link_register": "Sign up now",
        "modal.link_login": "Sign in now",
        "modal.toggle_pass_aria": "Show password",

        // Auth Toasts & Alerts
        "auth.login_success": "Login successful! Welcome back.",
        "auth.logout_success": "Successfully logged out.",
        "auth.register_success": "Registration successful! You can now sign in.",
        "auth.error_prefix": "Authentication error: "
    }
};

// Dịch địa danh mẫu sang tiếng Anh cho trải nghiệm hoàn hảo
const PLACE_TRANSLATIONS_EN = {
    101: {
        name: "Dragon Bridge Da Nang",
        address: "Nguyen Van Linh St., Phuoc Ninh, Hai Chau, Da Nang",
        description: "Unique architectural landmark of the city featuring fire and water breathing shows every Saturday and Sunday at 21:00.",
        opening_hours: "Open 24/7 (Fire show 21:00 Sat & Sun)"
    },
    102: {
        name: "Sun World Ba Na Hills & Golden Bridge",
        address: "Hoa Phu Commune, Hoa Vang District, Da Nang",
        description: "Highland resort complex atop Mount Chua featuring the world-famous Golden Bridge, medieval French Village, and 4 seasons in one day.",
        opening_hours: "07:30 - 21:30 daily"
    },
    103: {
        name: "Linh Ung Pagoda - Son Tra Peninsula",
        address: "Bai But, Son Tra Peninsula, Tho Quang, Son Tra, Da Nang",
        description: "Serene sea-facing pagoda featuring the 67-meter tall Lady Buddha statue overlooking the East Sea and Da Nang Bay.",
        opening_hours: "06:00 - 20:30 daily"
    },
    104: {
        name: "My Khe Beach",
        address: "Vo Nguyen Giap St., Phuoc My, Son Tra, Da Nang",
        description: "Voted by Forbes magazine as one of the most attractive beaches on the planet with soft white sand and gentle blue waves.",
        opening_hours: "Open 24/7"
    },
    105: {
        name: "Ba Duong Crispy Jumping Shrimp Pancake",
        address: "K280/23 Hoang Dieu St., Binh Hien, Hai Chau, Da Nang",
        description: "Decades-old famous Da Nang brand known for extra crispy pancakes with savory peanut liver sauce and grilled lemongrass pork skewers.",
        opening_hours: "09:30 - 21:30"
    },
    106: {
        name: "Ba Mua Quang Noodles",
        address: "19-21 Tran Binh Trong St., Hai Chau, Da Nang",
        description: "Traditional Quang-style noodles with savory shrimp, pork, quail eggs, native chicken, fresh herbs, and toasted sesame rice crackers.",
        opening_hours: "06:30 - 22:00"
    },
    107: {
        name: "Trinh Coffee - Greenery & Vintage Vibe",
        address: "34/4 Nguyen Huu Tho St., Hoa Thuan Nam, Hai Chau, Da Nang",
        description: "Rustic cafe with vintage decor serving signature rich avocado coffee, featuring a tranquil garden to work and relax.",
        opening_hours: "07:00 - 22:30"
    },
    108: {
        name: "Wonderlust Danang - Concept Cafe",
        address: "96 Tran Phú St., Hai Chau 1, Hai Chau, Da Nang",
        description: "Modern open-concept cafe bathed in natural sunlight through a soaring glass ceiling, serving refreshing craft drinks and pastries.",
        opening_hours: "07:30 - 23:00"
    },
    109: {
        name: "Han Market Da Nang",
        address: "119 Tran Phu St., Hai Chau 1, Hai Chau, Da Nang",
        description: "Bustling traditional market in the city center, a paradise for authentic Da Nang local specialties like beef sausage, fermented dips, and dried squid.",
        opening_hours: "06:00 - 19:00"
    },
    110: {
        name: "Son Tra Night Market",
        address: "Mai Hac De St., An Hai Trung, Son Tra, Da Nang (near Dragon Bridge)",
        description: "Vibrant night market with hundreds of street food stalls, sizzling grilled seafood, local crafts, and lively street entertainment.",
        opening_hours: "18:00 - 24:00 daily"
    }
};

/**
 * Lấy ngôn ngữ hiện tại ("vi" hoặc "en")
 * @returns {"vi"|"en"}
 */
function getLang() {
    return currentLang === "en" ? "en" : "vi";
}

/**
 * Lấy chuỗi bản dịch theo khóa
 * @param {string} key 
 * @param {Record<string, any>} [params={}] 
 * @returns {string}
 */
function t(key, params = {}) {
    const lang = getLang();
    const dict = TRANSLATIONS[lang] || TRANSLATIONS.vi;
    let text = dict[key] !== undefined ? dict[key] : (TRANSLATIONS.vi[key] || key);

    // Thay thế tham số {paramName}
    if (params && typeof params === "object") {
        for (const [pKey, pVal] of Object.entries(params)) {
            text = text.replace(new RegExp(`\\{${pKey}\\}`, "g"), String(pVal));
        }
    }
    return text;
}

/**
 * Lấy thông tin địa điểm theo ngôn ngữ
 * @param {object} place 
 * @returns {object}
 */
function getLocalizedPlace(place) {
    if (!place) return place;
    const lang = getLang();
    if (lang === "en" && place.id && PLACE_TRANSLATIONS_EN[place.id]) {
        return {
            ...place,
            ...PLACE_TRANSLATIONS_EN[place.id]
        };
    }
    return place;
}

/**
 * Đăng ký listener nhận thông báo khi ngôn ngữ thay đổi
 * @param {(lang: "vi"|"en") => void} callback 
 */
function onLanguageChange(callback) {
    if (typeof callback === "function") {
        changeListeners.push(callback);
    }
}

/**
 * Chuyển đổi ngôn ngữ hệ thống
 * @param {"vi"|"en"} newLang 
 */
function setLang(newLang) {
    const target = newLang === "en" ? "en" : "vi";
    if (currentLang === target && document.documentElement.lang === target) {
        return;
    }
    currentLang = target;
    try {
        localStorage.setItem(LANG_STORAGE_KEY, target);
    } catch {
        // bỏ qua nếu cookies/storage bị chặn
    }

    // Cập nhật thuộc tính thẻ html
    document.documentElement.lang = target;

    // Cập nhật title và description của trang
    document.title = t("doc.title");
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) {
        metaDesc.setAttribute("content", t("doc.description"));
    }

    // Dịch toàn bộ các phần tử tĩnh trong DOM
    translateDOM();

    // Cập nhật trạng thái nút chuyển đổi ngôn ngữ
    updateSwitcherUI();

    // Thông báo cho tất cả các module khác (places, map, auth, v.v.)
    changeListeners.forEach(listener => {
        try {
            listener(target);
        } catch (err) {
            console.error("[i18n] Error in change listener:", err);
        }
    });
}

/**
 * Quét và cập nhật các phần tử HTML có thuộc tính data-i18n
 */
function translateDOM() {
    // 1. Text nội dung (hỗ trợ cả HTML nếu có thẻ lồng)
    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (key) {
            const translated = t(key);
            if (translated.includes("<") && translated.includes(">")) {
                el.innerHTML = translated;
            } else {
                el.textContent = translated;
            }
        }
    });

    // 2. Thuộc tính placeholder
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        const key = el.getAttribute("data-i18n-placeholder");
        if (key) {
            el.setAttribute("placeholder", t(key));
        }
    });

    // 3. Thuộc tính title (tooltip)
    document.querySelectorAll("[data-i18n-title]").forEach(el => {
        const key = el.getAttribute("data-i18n-title");
        if (key) {
            el.setAttribute("title", t(key));
        }
    });

    // 4. Thuộc tính aria-label
    document.querySelectorAll("[data-i18n-aria-label]").forEach(el => {
        const key = el.getAttribute("data-i18n-aria-label");
        if (key) {
            el.setAttribute("aria-label", t(key));
        }
    });
}

/**
 * Cập nhật giao diện của nút chuyển ngôn ngữ ở góc trên
 */
function updateSwitcherUI() {
    const activeLang = getLang();
    const isEn = activeLang === "en";
    const buttons = document.querySelectorAll(".lang-btn");
    buttons.forEach(btn => {
        const btnLang = btn.dataset.lang;
        const isActive = btnLang === activeLang;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-pressed", isActive ? "true" : "false");
    });

    const switchers = document.querySelectorAll(".lang-toggle-switch");
    switchers.forEach(sw => {
        sw.classList.toggle("is-en", isEn);
        sw.classList.toggle("is-vi", !isEn);
        sw.setAttribute("aria-checked", isEn ? "true" : "false");
    });
}

/**
 * Khởi tạo bộ chuyển đổi ngôn ngữ
 */
function initI18n() {
    // Cập nhật thuộc tính ban đầu
    document.documentElement.lang = getLang();
    document.title = t("doc.title");

    // Gắn sự kiện click cho các nút chuyển ngôn ngữ
    const switcher = document.getElementById("langSwitcher") || document.getElementById("lang-switcher");
    if (switcher) {
        switcher.querySelectorAll(".lang-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const targetLang = btn.dataset.lang;
                setLang(targetLang);
            });
        });

        const toggleSwitch = switcher.querySelector(".lang-toggle-switch");
        if (toggleSwitch) {
            toggleSwitch.addEventListener("click", (e) => {
                if (e.target.closest(".lang-btn")) return;
                const current = getLang();
                setLang(current === "vi" ? "en" : "vi");
            });

            toggleSwitch.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    const current = getLang();
                    setLang(current === "vi" ? "en" : "vi");
                }
            });
        }
    }

    // Dịch các phần tử DOM hiện có
    translateDOM();
    updateSwitcherUI();
}

// Gán toàn cục vào window cho trình duyệt
if (typeof window !== "undefined") {
    window.TRANSLATIONS = TRANSLATIONS;
    window.PLACE_TRANSLATIONS_EN = PLACE_TRANSLATIONS_EN;
    window.getLang = getLang;
    window.setLang = setLang;
    window.t = t;
    window.getLocalizedPlace = getLocalizedPlace;
    window.onLanguageChange = onLanguageChange;
    window.translateDOM = translateDOM;
    window.updateSwitcherUI = updateSwitcherUI;
    window.initI18n = initI18n;
    window.i18n = {
        TRANSLATIONS,
        PLACE_TRANSLATIONS_EN,
        getLang,
        setLang,
        t,
        getLocalizedPlace,
        onLanguageChange,
        translateDOM,
        updateSwitcherUI,
        initI18n
    };
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        TRANSLATIONS,
        PLACE_TRANSLATIONS_EN,
        getLang,
        setLang,
        t,
        getLocalizedPlace,
        onLanguageChange,
        translateDOM,
        updateSwitcherUI,
        initI18n
    };
}
