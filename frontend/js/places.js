// ============================================
// PLACES SERVICE & LIST RENDERER
// ============================================

import { placesApi } from "./api.js";
import { MOCK_PLACES } from "./config.js";
import { escapeHTML, getCategoryInfo, getPriceText } from "./utils.js";
import { renderMarkers, focusPlace } from "./map.js";

let allPlaces = [];
let currentFilteredPlaces = [];
let selectedPlaceId = null;

// DOM Elements cache
let placeListEl = null;
let resultCountEl = null;
let searchInputEl = null;
let categorySelectEl = null;
let priceSelectEl = null;
let errorMessageEl = null;
let connectionStatusEl = null;

/**
 * Khởi tạo Places Controller
 */
export function initPlaces() {
    placeListEl = document.getElementById("placeList");
    resultCountEl = document.getElementById("resultCount");
    searchInputEl = document.getElementById("searchInput");
    categorySelectEl = document.getElementById("categorySelect");
    priceSelectEl = document.getElementById("priceSelect");
    errorMessageEl = document.getElementById("errorMessage");
    connectionStatusEl = document.getElementById("connectionStatus");

    // Lắng nghe sự kiện tìm kiếm và bộ lọc
    if (searchInputEl) {
        searchInputEl.addEventListener("input", debounce(applyFiltersAndRender, 250));
        searchInputEl.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                applyFiltersAndRender();
            }
        });
    }

    if (categorySelectEl) {
        categorySelectEl.addEventListener("change", applyFiltersAndRender);
    }

    if (priceSelectEl) {
        priceSelectEl.addEventListener("change", applyFiltersAndRender);
    }

    const searchBtn = document.getElementById("searchButton");
    if (searchBtn) {
        searchBtn.addEventListener("click", applyFiltersAndRender);
    }

    // Nút xóa nhanh ô tìm kiếm
    const clearSearchBtn = document.getElementById("clearSearchBtn");
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener("click", () => {
            if (searchInputEl) {
                searchInputEl.value = "";
                searchInputEl.focus();
                applyFiltersAndRender();
            }
        });
    }

    // Tải dữ liệu ban đầu
    loadPlaces();
}

/**
 * Chuẩn hóa cấu trúc dữ liệu trả về từ API Backend
 */
function normalizePlacesData(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.places)) return data.places;
    if (data && Array.isArray(data.items)) return data.items;
    return [];
}

/**
 * Tải danh sách địa điểm từ Backend API (kèm fallback thông minh)
 */
export async function loadPlaces() {
    if (!placeListEl) return;

    if (errorMessageEl) errorMessageEl.classList.add("hidden");
    placeListEl.innerHTML = `
        <div class="places-loading">
            <span class="spinner-lg"></span>
            <p>Đang tải danh sách địa điểm Đà Nẵng...</p>
        </div>
    `;

    if (connectionStatusEl) {
        connectionStatusEl.innerHTML = `<span class="status-dot status-connecting"></span> Đang kết nối Backend...`;
    }

    try {
        const data = await placesApi.getAll();
        const places = normalizePlacesData(data);

        if (places && places.length > 0) {
            allPlaces = places;
            if (connectionStatusEl) {
                connectionStatusEl.innerHTML = `<span class="status-dot status-online"></span> Đã kết nối Backend • ${allPlaces.length} địa điểm`;
            }
        } else {
            // Nếu Database chưa có dữ liệu, sử dụng MOCK_PLACES chất lượng cao
            console.info("[Places] Database chưa có dữ liệu, chuyển sang dữ liệu mẫu Đà Nẵng.");
            allPlaces = MOCK_PLACES;
            if (connectionStatusEl) {
                connectionStatusEl.innerHTML = `<span class="status-dot status-demo"></span> Chế độ Demo • ${allPlaces.length} địa điểm gợi ý`;
            }
        }

        applyFiltersAndRender();
    } catch (error) {
        console.warn("[Places] Lỗi kết nối Backend, kích hoạt chế độ Demo dữ liệu mẫu:", error.message);
        allPlaces = MOCK_PLACES;

        if (connectionStatusEl) {
            connectionStatusEl.innerHTML = `<span class="status-dot status-demo"></span> Chế độ Demo (Offline) • ${allPlaces.length} địa điểm`;
        }

        if (errorMessageEl) {
            errorMessageEl.innerHTML = `
                <div class="alert-content">
                    <strong>Lưu ý:</strong> Backend chưa được kết nối hoặc chưa khởi chạy. Hệ thống đang hiển thị dữ liệu gợi ý mẫu để bạn trải nghiệm bản đồ và giao diện.
                </div>
            `;
            errorMessageEl.classList.remove("hidden");
        }

        applyFiltersAndRender();
    }
}

/**
 * Lọc địa điểm theo từ khóa, danh mục và mức giá
 */
export function getFilteredPlaces() {
    const keyword = searchInputEl ? searchInputEl.value.trim().toLocaleLowerCase("vi") : "";
    const category = categorySelectEl ? categorySelectEl.value : "";
    const maxPrice = priceSelectEl && priceSelectEl.value ? Number(priceSelectEl.value) : 5;

    return allPlaces.filter(place => {
        // Tìm kiếm toàn diện
        const searchable = [
            place.name,
            place.category,
            place.address,
            place.description
        ].filter(Boolean).join(" ").toLocaleLowerCase("vi");

        const matchesKeyword = !keyword || searchable.includes(keyword);
        const matchesCategory = !category || place.category === category;
        const placePrice = place.price_level === null || place.price_level === undefined ? 1 : Number(place.price_level);
        const matchesPrice = placePrice <= maxPrice;

        return matchesKeyword && matchesCategory && matchesPrice;
    });
}

/**
 * Áp dụng bộ lọc và render ra cả danh sách thẻ và bản đồ
 */
export function applyFiltersAndRender() {
    currentFilteredPlaces = getFilteredPlaces();

    if (resultCountEl) {
        resultCountEl.textContent = `${currentFilteredPlaces.length} địa điểm`;
    }

    renderPlaceCards(currentFilteredPlaces);

    // Cập nhật các marker trên bản đồ
    renderMarkers(currentFilteredPlaces, (place) => {
        highlightPlaceCard(place.id);
    });
}

/**
 * Render danh sách các thẻ địa điểm trong sidebar
 * @param {Array<object>} places 
 */
export function renderPlaceCards(places) {
    if (!placeListEl) return;

    if (places.length === 0) {
        placeListEl.innerHTML = `
            <div class="empty-state-box">
                <span class="empty-icon">🔍</span>
                <h4>Không tìm thấy địa điểm phù hợp</h4>
                <p>Hãy thử tìm bằng từ khóa khác hoặc điều chỉnh lại bộ lọc danh mục/mức giá.</p>
                <button type="button" class="reset-filter-btn" id="resetFiltersBtn">Xóa bộ lọc</button>
            </div>
        `;

        const resetBtn = document.getElementById("resetFiltersBtn");
        if (resetBtn) {
            resetBtn.addEventListener("click", () => {
                if (searchInputEl) searchInputEl.value = "";
                if (categorySelectEl) categorySelectEl.value = "";
                if (priceSelectEl) priceSelectEl.value = "5";
                applyFiltersAndRender();
            });
        }
        return;
    }

    placeListEl.innerHTML = places.map((place) => {
        const categoryInfo = getCategoryInfo(place.category);
        const isSelected = selectedPlaceId === place.id;

        return `
            <article class="place-card ${isSelected ? 'selected' : ''}" data-place-id="${place.id}">
                <div class="card-header">
                    <span class="place-badge" style="background: ${categoryInfo.bg}; color: ${categoryInfo.color};">
                        ${categoryInfo.icon} ${escapeHTML(categoryInfo.name)}
                    </span>
                    <span class="place-price-tag">${escapeHTML(getPriceText(place.price_level))}</span>
                </div>

                <h3 class="place-title">${escapeHTML(place.name || "Địa điểm")}</h3>
                <p class="place-address">📍 ${escapeHTML(place.address || "Chưa có địa chỉ")}</p>
                
                ${place.description ? `<p class="place-description">${escapeHTML(place.description)}</p>` : ""}

                <div class="place-footer">
                    <span class="place-hours">🕒 ${escapeHTML(place.opening_hours || "Chưa cập nhật")}</span>
                    <span class="view-map-link">Xem trên bản đồ &rarr;</span>
                </div>
            </article>
        `;
    }).join("");

    // Gắn sự kiện click cho từng thẻ
    placeListEl.querySelectorAll(".place-card").forEach(card => {
        card.addEventListener("click", () => {
            const placeId = Number(card.dataset.placeId);
            const place = places.find(p => p.id === placeId);
            if (place) {
                selectPlace(place);
            }
        });
    });
}

/**
 * Chọn và làm nổi bật địa điểm, đồng thời di chuyển camera bản đồ
 * @param {object} place 
 */
export function selectPlace(place) {
    selectedPlaceId = place.id;

    // Đánh dấu thẻ được chọn
    placeListEl.querySelectorAll(".place-card").forEach(c => {
        if (Number(c.dataset.placeId) === place.id) {
            c.classList.add("selected");
        } else {
            c.classList.remove("selected");
        }
    });

    // Di chuyển bản đồ và mở popup
    if (place.latitude != null && place.longitude != null) {
        focusPlace(place.latitude, place.longitude, 16, place.id);
    }
}

/**
 * Làm nổi bật thẻ địa điểm khi người dùng nhấp vào marker bản đồ
 * @param {number|string} placeId 
 */
export function highlightPlaceCard(placeId) {
    selectedPlaceId = Number(placeId);

    placeListEl.querySelectorAll(".place-card").forEach(c => {
        if (Number(c.dataset.placeId) === selectedPlaceId) {
            c.classList.add("selected");
            c.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } else {
            c.classList.remove("selected");
        }
    });
}

/**
 * Đặt từ khóa tìm kiếm và lọc ngay
 * @param {string} keyword 
 */
export function setQuickSearch(keyword) {
    if (searchInputEl) {
        searchInputEl.value = keyword;
        applyFiltersAndRender();
        searchInputEl.focus();
    }
}

/**
 * Hàm Debounce hỗ trợ giảm tần suất gọi khi người dùng gõ phím
 */
function debounce(func, delay = 250) {
    let timer = null;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => func.apply(this, args), delay);
    };
}
