// ============================================
// AGENTIC AI LOCAL GUIDE - MAIN BOOTSTRAP
// ============================================

import { initAuth } from "./auth.js";
import { initMap, resetMapView, locateUser, toggleTourRoute, toggleSonTraArea } from "./map.js?v=20261015_01";
import { initPlaces, setQuickSearch } from "./places.js";
import { QUICK_TAGS } from "./config.js";

/**
 * Khởi tạo toàn bộ ứng dụng
 */
function initApp() {
    console.info("🚀 Khởi chạy Agentic AI Local Guide (Đà Nẵng)...");

    // 1. Khởi tạo bản đồ tương tác Leaflet
    initMap("map");

    // 2. Khởi tạo phân hệ xác thực tài khoản & Modal
    initAuth();

    // 3. Khởi tạo quản lý danh sách địa điểm & tìm kiếm
    initPlaces();

    // 4. Khởi tạo các nút thao tác trên bản đồ
    setupMapControls();

    // 5. Khởi tạo các thẻ gợi ý tìm kiếm nhanh (Quick Tags)
    setupQuickTags();
}

/**
 * Thiết lập các nút điều khiển bản đồ
 */
function setupMapControls() {
    // 1. Nút đặt lại góc nhìn bản đồ
    const resetMapBtn = document.getElementById("resetMapButton");
    if (resetMapBtn) {
        resetMapBtn.addEventListener("click", () => {
            resetMapView();
        });
    }

    // 2. Nút định vị GPS và vẽ bán kính
    const locateMeBtn = document.getElementById("locateMeButton");
    if (locateMeBtn) {
        locateMeBtn.addEventListener("click", () => {
            locateUser();
        });
    }

    // 3. Nút bật/tắt vẽ Lộ trình du lịch mẫu
    const toggleRouteBtn = document.getElementById("toggleRouteBtn");
    if (toggleRouteBtn) {
        toggleRouteBtn.addEventListener("click", () => {
            const isActive = toggleTourRoute();
            toggleRouteBtn.classList.toggle("active", isActive);
        });
    }

    // 4. Nút bật/tắt vẽ Ranh giới Bán đảo Sơn Trà
    const toggleAreaBtn = document.getElementById("toggleAreaBtn");
    if (toggleAreaBtn) {
        toggleAreaBtn.addEventListener("click", () => {
            const isActive = toggleSonTraArea();
            toggleAreaBtn.classList.toggle("active", isActive);
        });
    }
}

/**
 * Hiển thị danh sách gợi ý tìm kiếm nhanh
 */
function setupQuickTags() {
    const container = document.getElementById("quickTagsContainer");
    if (!container) return;

    container.innerHTML = QUICK_TAGS.map(tag => `
        <button type="button" class="quick-tag" data-query="${tag.query}">
            ${tag.label}
        </button>
    `).join("");

    container.querySelectorAll(".quick-tag").forEach(btn => {
        btn.addEventListener("click", () => {
            const query = btn.dataset.query;
            setQuickSearch(query);
        });
    });
}

// Khởi chạy khi DOM sẵn sàng
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApp);
} else {
    initApp();
}
