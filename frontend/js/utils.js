// ============================================
// UTILITIES & HELPERS
// ============================================

const CATEGORIES = (typeof window !== "undefined" && window.CATEGORIES) || {};

/**
 * Thoát các ký tự đặc biệt để phòng chống tấn công XSS
 * @param {string|any} value 
 * @returns {string}
 */
export function escapeHTML(value) {
    if (value === null || value === undefined) return "";
    return String(value).replace(/[&<>"']/g, function (character) {
        const entities = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        };
        return entities[character];
    });
}

/**
 * Trả về chuỗi ký hiệu mức giá (₫)
 * @param {number|null} price 
 * @returns {string}
 */
export function getPriceText(price) {
    if (price === null || price === undefined) {
        return "Chưa cập nhật giá";
    }
    const number = Number(price);
    if (!Number.isFinite(number) || number < 1) {
        return "Chưa cập nhật giá";
    }
    const count = Math.min(Math.max(Math.round(number), 1), 5);
    return "₫".repeat(count);
}

/**
 * Lấy thông tin danh mục (Tên tiếng Việt, icon, màu sắc)
 * @param {string} categoryKey 
 * @returns {{ name: string, icon: string, color: string, bg: string }}
 */
export function getCategoryInfo(categoryKey) {
    if (CATEGORIES[categoryKey]) {
        return CATEGORIES[categoryKey];
    }
    return {
        name: categoryKey || "Địa điểm",
        icon: "📍",
        color: "#147d64",
        bg: "#e9f5ef"
    };
}

/**
 * Hiển thị thông báo Toast nổi trên màn hình
 * @param {string} message - Nội dung thông báo
 * @param {"success"|"error"|"info"|"warning"} type - Loại thông báo
 * @param {number} duration - Thời gian hiển thị (ms)
 */
export function showToast(message, type = "info", duration = 3500) {
    let container = document.getElementById("toastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "toastContainer";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const icons = {
        success: "✓",
        error: "✕",
        warning: "⚠",
        info: "ℹ"
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || "ℹ"}</span>
        <span class="toast-message">${escapeHTML(message)}</span>
        <button type="button" class="toast-close" aria-label="Đóng">&times;</button>
    `;

    const closeBtn = toast.querySelector(".toast-close");
    const removeToast = () => {
        toast.classList.add("toast-leaving");
        toast.addEventListener("animationend", () => {
            toast.remove();
        });
    };

    closeBtn.addEventListener("click", removeToast);
    container.appendChild(toast);

    if (duration > 0) {
        setTimeout(removeToast, duration);
    }
}
