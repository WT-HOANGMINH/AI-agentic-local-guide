// ============================================
// API CLIENT SERVICE
// ============================================

import { API_BASE_URL } from "./config.js";

/**
 * Hàm gọi API tổng quát với xử lý JWT Token tự động
 * @param {string} endpoint - Đường dẫn endpoint (bắt đầu bằng /)
 * @param {RequestInit} [options={}] - Tuỳ chọn fetch
 * @returns {Promise<any>}
 */
export async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    // Đính kèm JWT Token nếu đã đăng nhập trong localStorage
    const token = localStorage.getItem("access_token");
    if (token && !headers["Authorization"]) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers
    };

    try {
        const response = await fetch(url, config);

        // Kiểm tra xem phản hồi có phải là JSON không
        const contentType = response.headers.get("content-type");
        const isJson = contentType && contentType.includes("application/json");
        const data = isJson ? await response.json() : await response.text();

        if (!response.ok) {
            // Xử lý thông báo lỗi chi tiết từ FastAPI backend
            let errorMessage = `Yêu cầu thất bại (Mã lỗi ${response.status})`;
            if (data && typeof data === "object") {
                if (data.detail) {
                    if (Array.isArray(data.detail)) {
                        // Trường hợp validation error của Pydantic
                        errorMessage = data.detail.map(item => item.msg || item.message).join(", ");
                    } else {
                        errorMessage = String(data.detail);
                    }
                } else if (data.message) {
                    errorMessage = String(data.message);
                }
            } else if (typeof data === "string" && data.length > 0) {
                errorMessage = data;
            }

            const error = new Error(errorMessage);
            error.status = response.status;
            error.data = data;
            throw error;
        }

        return data;
    } catch (error) {
        // Nếu lỗi kết nối mạng (Network Error / Backend chưa chạy)
        if (error.name === "TypeError" && error.message.includes("fetch")) {
            console.warn(`[API] Không thể kết nối tới Backend tại ${API_BASE_URL}`);
            const netError = new Error(`Không thể kết nối đến máy chủ (${API_BASE_URL}). Vui lòng đảm bảo Backend FastAPI đang hoạt động.`);
            netError.isNetworkError = true;
            throw netError;
        }
        throw error;
    }
}

// ============================================
// CÁC DỊCH VỤ API CHUYÊN BIỆT
// ============================================

export const authApi = {
    /**
     * Đăng nhập tài khoản
     * @param {{ email: string, password: string }} credentials 
     */
    login(credentials) {
        return apiFetch("/auth/login", {
            method: "POST",
            body: JSON.stringify(credentials)
        });
    },

    /**
     * Đăng ký tài khoản mới
     * @param {{ username: string, email: string, password: string }} userData 
     */
    register(userData) {
        return apiFetch("/auth/register", {
            method: "POST",
            body: JSON.stringify(userData)
        });
    },

    /**
     * Lấy thông tin tài khoản hiện tại từ token
     */
    getMe() {
        return apiFetch("/auth/me", {
            method: "GET"
        });
    }
};

export const placesApi = {
    /**
     * Lấy danh sách địa điểm có lọc
     * @param {{ keyword?: string, category?: string, max_price?: number, skip?: number, limit?: number }} params 
     */
    getAll(params = {}) {
        const query = new URLSearchParams();
        if (params.keyword) query.append("keyword", params.keyword);
        if (params.category) query.append("category", params.category);
        if (params.max_price !== undefined && params.max_price !== null && params.max_price < 5) {
            query.append("max_price", params.max_price);
        }
        if (params.skip) query.append("skip", params.skip);
        if (params.limit) query.append("limit", params.limit);

        const queryString = query.toString();
        const endpoint = queryString ? `/places/?${queryString}` : "/places/";
        return apiFetch(endpoint, { method: "GET" });
    },

    /**
     * Tìm địa điểm lân cận theo tọa độ GPS
     * @param {{ latitude: number, longitude: number, radius_km?: number, category?: string }} params 
     */
    getNearby(params) {
        const query = new URLSearchParams({
            latitude: params.latitude,
            longitude: params.longitude,
            radius_km: params.radius_km || 5
        });
        if (params.category) query.append("category", params.category);
        return apiFetch(`/places/nearby?${query.toString()}`, { method: "GET" });
    },

    /**
     * Lấy chi tiết một địa điểm theo ID
     * @param {number} id 
     */
    getById(id) {
        return apiFetch(`/places/${id}`, { method: "GET" });
    }
};

export const preferencesApi = {
    /**
     * Lấy sở thích của người dùng đang đăng nhập
     */
    getMe() {
        return apiFetch("/preferences/me", { method: "GET" });
    },

    /**
     * Cập nhật sở thích người dùng
     * @param {{ favorite_categories?: string[], preferred_price_level?: number, travel_style?: string, dietary_preferences?: string, interests?: string[] }} data 
     */
    updateMe(data) {
        return apiFetch("/preferences/me", {
            method: "PUT",
            body: JSON.stringify(data)
        });
    },

    /**
     * Đặt lại/xoá sở thích
     */
    resetMe() {
        return apiFetch("/preferences/me", { method: "DELETE" });
    }
};

export const recommendationsApi = {
    /**
     * Gửi tin nhắn chat tới AI Agent gợi ý du lịch
     * @param {string} message 
     * @param {boolean} [usePreferences=true] 
     */
    chat(message, usePreferences = true) {
        return apiFetch("/recommendations/chat", {
            method: "POST",
            body: JSON.stringify({
                message,
                use_preferences: usePreferences
            })
        });
    },

    /**
     * Lấy gợi ý địa điểm cá nhân hóa theo hồ sơ sở thích
     * @param {number} [limit=6] 
     */
    getForMe(limit = 6) {
        return apiFetch(`/recommendations/for-me?limit=${limit}`, { method: "GET" });
    },

    /**
     * Lấy danh sách địa điểm thịnh hành
     * @param {number} [limit=6] 
     */
    getTrending(limit = 6) {
        return apiFetch(`/recommendations/trending?limit=${limit}`, { method: "GET" });
    }
};

export const systemApi = {
    checkHealth() {
        return apiFetch("/health", { method: "GET" });
    }
};

