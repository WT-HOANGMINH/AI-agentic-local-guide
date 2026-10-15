// ============================================
// MAP CONTROLLER (LEAFLET INTEGRATION)
// ============================================

import { DA_NANG } from "./config.js";
import { escapeHTML, getCategoryInfo, getPriceText, showToast } from "./utils.js";

let mapInstance = null;
let markerLayer = null;
let userLocationLayer = null;
const markersMap = new Map(); // Map<placeId, L.Marker>

/**
 * Khởi tạo Leaflet Map
 * @param {string} containerId - ID của phần tử chứa bản đồ (mặc định "map")
 * @returns {L.Map}
 */
export function initMap(containerId = "map") {
    if (mapInstance) {
        return mapInstance;
    }

    const mapElement = document.getElementById(containerId);
    if (!mapElement) {
        console.error(`Không tìm thấy phần tử #${containerId} để khởi tạo bản đồ`);
        return null;
    }

    // Khởi tạo bản đồ với tọa độ trung tâm Đà Nẵng
    mapInstance = L.map(containerId, {
        zoomControl: true,
        scrollWheelZoom: true
    }).setView([DA_NANG.lat, DA_NANG.lng], DA_NANG.defaultZoom);

    // Lớp bản đồ nền OpenStreetMap chất lượng cao
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(mapInstance);

    // Layer nhóm chứa các marker địa điểm
    markerLayer = L.layerGroup().addTo(mapInstance);

    // Layer nhóm chứa vị trí người dùng
    userLocationLayer = L.layerGroup().addTo(mapInstance);

    // Tự động căn chỉnh kích thước bản đồ sau khi render DOM
    setTimeout(() => {
        if (mapInstance) {
            mapInstance.invalidateSize();
        }
    }, 250);

    window.addEventListener("resize", () => {
        if (mapInstance) {
            mapInstance.invalidateSize();
        }
    });

    return mapInstance;
}

/**
 * Tạo icon marker màu sắc tuỳ biến theo danh mục
 * @param {string} categoryKey 
 * @returns {L.DivIcon}
 */
function createCustomPin(categoryKey) {
    const info = getCategoryInfo(categoryKey);
    return L.divIcon({
        className: "custom-map-pin",
        html: `
            <div class="pin-marker" style="--pin-color: ${info.color};">
                <span class="pin-icon">${info.icon}</span>
            </div>
            <div class="pin-pulse" style="--pin-color: ${info.color};"></div>
        `,
        iconSize: [36, 42],
        iconAnchor: [18, 42],
        popupAnchor: [0, -38]
    });
}

/**
 * Hiển thị danh sách markers của các địa điểm lên bản đồ
 * @param {Array<object>} places 
 * @param {(place: object, index: number) => void} onMarkerSelect - Callback khi click vào marker
 */
export function renderMarkers(places = [], onMarkerSelect = null) {
    if (!mapInstance || !markerLayer) return;

    markerLayer.clearLayers();
    markersMap.clear();

    const validPlaces = places.filter(place => {
        const lat = Number(place.latitude);
        const lng = Number(place.longitude);
        return (
            place.latitude !== null &&
            place.latitude !== undefined &&
            place.longitude !== null &&
            place.longitude !== undefined &&
            Number.isFinite(lat) &&
            Number.isFinite(lng) &&
            Math.abs(lat) <= 90 &&
            Math.abs(lng) <= 180
        );
    });

    validPlaces.forEach((place, index) => {
        const lat = Number(place.latitude);
        const lng = Number(place.longitude);

        const categoryInfo = getCategoryInfo(place.category);
        const pinIcon = createCustomPin(place.category);

        const marker = L.marker([lat, lng], { icon: pinIcon }).addTo(markerLayer);

        // Nội dung popup hiện đại
        const popupContent = `
            <div class="map-popup-card">
                <div class="popup-badge" style="background: ${categoryInfo.bg}; color: ${categoryInfo.color};">
                    ${categoryInfo.icon} ${escapeHTML(categoryInfo.name)}
                </div>
                <h4 class="popup-title">${escapeHTML(place.name || "Địa điểm")}</h4>
                <p class="popup-address">📍 ${escapeHTML(place.address || "Chưa có địa chỉ")}</p>
                ${place.description ? `<p class="popup-desc">${escapeHTML(place.description)}</p>` : ""}
                <div class="popup-meta">
                    <span>🕒 ${escapeHTML(place.opening_hours || "Chưa cập nhật")}</span>
                    <span>💰 ${escapeHTML(getPriceText(place.price_level))}</span>
                </div>
                <a class="popup-action-btn" href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.name + ' Đà Nẵng')}" target="_blank" rel="noopener">
                    Chỉ đường Google Maps ↗
                </a>
            </div>
        `;

        marker.bindPopup(popupContent, {
            maxWidth: 300,
            className: "modern-leaflet-popup"
        });

        marker.on("click", () => {
            if (typeof onMarkerSelect === "function") {
                onMarkerSelect(place, index);
            }
        });

        if (place.id) {
            markersMap.set(place.id, marker);
        }
    });
}

/**
 * Di chuyển camera bản đồ đến địa điểm chỉ định và mở popup
 * @param {number} lat 
 * @param {number} lng 
 * @param {number} [zoom=16] 
 * @param {number|string} [placeId] 
 */
export function focusPlace(lat, lng, zoom = 15, placeId = null) {
    if (!mapInstance) return;

    const targetLat = Number(lat);
    const targetLng = Number(lng);

    if (!Number.isFinite(targetLat) || !Number.isFinite(targetLng)) return;

    mapInstance.invalidateSize();

    mapInstance.flyTo([targetLat, targetLng], zoom, {
        duration: 0.8,
        easeLinearity: 0.3
    });

    const openPopup = () => {
        if (placeId && markersMap.has(Number(placeId))) {
            const marker = markersMap.get(Number(placeId));
            marker.openPopup();
        } else {
            // Tìm marker gần tọa độ đó nhất
            markerLayer.eachLayer(marker => {
                const pos = marker.getLatLng();
                if (
                    Math.abs(pos.lat - targetLat) < 0.0001 &&
                    Math.abs(pos.lng - targetLng) < 0.0001
                ) {
                    marker.openPopup();
                }
            });
        }
    };

    mapInstance.once("moveend", openPopup);
}

/**
 * Đặt lại góc nhìn bản đồ về trung tâm Đà Nẵng
 */
export function resetMapView() {
    if (!mapInstance) return;
    mapInstance.flyTo([DA_NANG.lat, DA_NANG.lng], DA_NANG.defaultZoom, {
        duration: 1.2
    });
    mapInstance.closePopup();
}

/**
 * Định vị GPS người dùng hiện tại và ghim lên bản đồ
 * @param {(lat: number, lng: number) => void} onSuccessCallback 
 */
export function locateUser(onSuccessCallback = null) {
    if (!navigator.geolocation) {
        showToast("Trình duyệt của bạn không hỗ trợ định vị GPS.", "error");
        return;
    }

    showToast("Đang xác định vị trí của bạn...", "info", 2000);

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            if (userLocationLayer) {
                userLocationLayer.clearLayers();

                const userIcon = L.divIcon({
                    className: "user-gps-marker",
                    html: `
                        <div class="user-gps-dot"></div>
                        <div class="user-gps-ring"></div>
                    `,
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                });

                const userMarker = L.marker([lat, lng], { icon: userIcon }).addTo(userLocationLayer);
                userMarker.bindPopup("<strong>📍 Vị trí hiện tại của bạn</strong>").openPopup();
            }

            if (mapInstance) {
                mapInstance.flyTo([lat, lng], 15, { duration: 1.2 });
            }

            showToast("Đã xác định vị trí của bạn!", "success");

            if (typeof onSuccessCallback === "function") {
                onSuccessCallback(lat, lng);
            }
        },
        (error) => {
            console.warn("Lỗi GPS:", error);
            let message = "Không thể lấy vị trí hiện tại.";
            if (error.code === error.PERMISSION_DENIED) {
                message = "Bạn đã từ chối quyền truy cập vị trí trên trình duyệt.";
            } else if (error.code === error.POSITION_UNAVAILABLE) {
                message = "Thông tin vị trí không khả dụng.";
            } else if (error.code === error.TIMEOUT) {
                message = "Hết thời gian yêu cầu vị trí.";
            }
            showToast(message, "warning");
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
}
