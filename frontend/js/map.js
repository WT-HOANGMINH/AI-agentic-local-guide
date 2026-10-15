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

    // Lớp bản đồ Google Maps (Đầy đủ tiếng Việt, đường phố, sông Hàn & bờ biển Đà Nẵng sắc nét)
    const googleMap = L.tileLayer("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", {
        attribution: '&copy; Google Maps',
        maxZoom: 20
    }).addTo(mapInstance);

    // Lớp bản đồ OpenStreetMap
    const osmMap = L.tileLayer("https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors',
        subdomains: "abc",
        maxZoom: 19
    });

    // Lớp bản đồ Vệ tinh (Esri World Imagery)
    const satelliteMap = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        attribution: 'Tiles &copy; Esri',
        maxZoom: 18
    });

    // Thêm hộp chọn lớp bản đồ ở góc trên bên phải
    L.control.layers({
        "🗺️ Bản đồ Google Maps": googleMap,
        "📍 Bản đồ Du lịch OSM": osmMap,
        "🛰️ Bản đồ Vệ tinh": satelliteMap
    }, null, { position: "topright" }).addTo(mapInstance);

    // Layer nhóm chứa các marker địa điểm Đà Nẵng
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
let routeLayer = null;
let areaLayer = null;
let isRouteActive = false;
let isAreaActive = false;

/**
 * Đặt lại góc nhìn bản đồ về trung tâm Đà Nẵng
 */
export function resetMapView() {
    if (!mapInstance) return;
    mapInstance.invalidateSize();
    mapInstance.flyTo([DA_NANG.lat, DA_NANG.lng], DA_NANG.defaultZoom, {
        duration: 1.0
    });
    mapInstance.closePopup();

    if (routeLayer && isRouteActive) {
        routeLayer.clearLayers();
        isRouteActive = false;
        const btn = document.getElementById("toggleRouteBtn");
        if (btn) btn.classList.remove("active");
    }
    if (areaLayer && isAreaActive) {
        areaLayer.clearLayers();
        isAreaActive = false;
        const btn = document.getElementById("toggleAreaBtn");
        if (btn) btn.classList.remove("active");
    }
    showToast("Đã quay về trung tâm Đà Nẵng!", "info", 2000);
}

/**
 * Định vị GPS người dùng hiện tại và vẽ vòng tròn bán kính tìm kiếm quanh vị trí
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

                // 1. Vẽ vòng tròn bán kính tìm kiếm lân cận (3km)
                const searchRadiusCircle = L.circle([lat, lng], {
                    radius: 3000, // 3000m = 3km
                    color: "#0284c7",
                    weight: 2,
                    dashArray: "6, 6",
                    fillColor: "#38bdf8",
                    fillOpacity: 0.12
                }).addTo(userLocationLayer);

                // 2. Vẽ marker vị trí người dùng
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
                userMarker.bindPopup(`
                    <div style="padding: 4px; font-size: 13px;">
                        <strong style="color: #0284c7;">📍 Vị trí hiện tại của bạn</strong>
                        <p style="margin: 4px 0 0; color: #64748b; font-size: 11.5px;">Bán kính tìm kiếm khám phá xung quanh: <strong>3 km</strong></p>
                    </div>
                `).openPopup();
            }

            if (mapInstance) {
                mapInstance.flyTo([lat, lng], 14, { duration: 1.2 });
            }

            showToast("Đã xác định vị trí & vẽ vùng bán kính 3km quanh bạn!", "success");

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

/**
 * Bật/Tắt vẽ Lộ Trình Du Lịch Đà Nẵng mẫu (L.polyline)
 * @returns {boolean} Trạng thái hiển thị mới
 */
export function toggleTourRoute() {
    if (!mapInstance) return false;

    if (!routeLayer) {
        routeLayer = L.layerGroup().addTo(mapInstance);
    }

    if (isRouteActive) {
        routeLayer.clearLayers();
        isRouteActive = false;
        showToast("Đã ẩn lộ trình du lịch.", "info");
        return false;
    }

    // Danh sách 5 điểm dừng chân tiêu biểu của chuyến khám phá Đà Nẵng 1 ngày
    const tourWaypoints = [
        {
            order: 1,
            name: "Cầu Rồng Đà Nẵng",
            time: "08:30 - 09:30",
            coords: [16.0611, 108.2272],
            desc: "Khởi hành chụp ảnh biểu tượng Cầu Rồng và bờ sông Hàn."
        },
        {
            order: 2,
            name: "Chợ Hàn Đà Nẵng",
            time: "10:00 - 11:30",
            coords: [16.0678, 108.2241],
            desc: "Mua sắm quà lưu niệm & thưởng thức đặc sản miền Trung."
        },
        {
            order: 3,
            name: "Bãi biển Mỹ Khê",
            time: "14:30 - 16:30",
            coords: [16.0592, 108.2435],
            desc: "Dạo biển, tắm mát và ngắm cảnh bờ biển đẹp nhất hành tinh."
        },
        {
            order: 4,
            name: "Chùa Linh Ứng Bãi Bụt (Sơn Trà)",
            time: "17:00 - 18:30",
            coords: [16.1001, 108.2778],
            desc: "Chiêm bái tượng Phật Bà cao 67m ngắm hoàng hôn vịnh Đà Nẵng."
        },
        {
            order: 5,
            name: "Danh thắng Ngũ Hành Sơn",
            time: "19:00 - 21:00",
            coords: [16.0042, 108.2618],
            desc: "Khám phá quần thể hang động và làng đá mỹ nghệ Non Nước."
        }
    ];

    routeLayer.clearLayers();

    // 1. Vẽ đường Polyline nối các điểm
    const latlngs = tourWaypoints.map(wp => wp.coords);
    const polyline = L.polyline(latlngs, {
        color: "#0284c7",
        weight: 5,
        opacity: 0.85,
        dashArray: "10, 8",
        lineCap: "round",
        lineJoin: "round"
    }).addTo(routeLayer);

    // 2. Thêm các waypoint markers đánh số 1, 2, 3, 4, 5
    tourWaypoints.forEach(wp => {
        const stepIcon = L.divIcon({
            className: "tour-step-marker",
            html: `
                <div class="step-pin">
                    <span class="step-num">${wp.order}</span>
                </div>
            `,
            iconSize: [32, 32],
            iconAnchor: [16, 16],
            popupAnchor: [0, -18]
        });

        const m = L.marker(wp.coords, { icon: stepIcon }).addTo(routeLayer);
        m.bindPopup(`
            <div style="font-size: 13px; line-height: 1.4;">
                <span style="display:inline-block; padding: 2px 8px; border-radius: 12px; background: #e0f2fe; color: #0284c7; font-size: 11px; font-weight: 700; margin-bottom: 4px;">
                    Chặng ${wp.order} • ${wp.time}
                </span>
                <h4 style="margin: 2px 0 6px; font-size: 14px; font-weight: 700; color: #0f172a;">${escapeHTML(wp.name)}</h4>
                <p style="margin: 0; color: #475569; font-size: 12px;">${escapeHTML(wp.desc)}</p>
            </div>
        `);
    });

    // 3. Tự động căn chỉnh bao quát toàn bộ lộ trình
    mapInstance.fitBounds(polyline.getBounds(), { padding: [50, 50] });

    isRouteActive = true;
    showToast("Đã vẽ Lộ trình Du lịch Đà Nẵng 1 ngày (5 chặng)! Nhấp vào từng số để xem chi tiết.", "success", 4000);
    return true;
}

/**
 * Bật/Tắt vẽ Ranh Giới Đa Giác Bán Đảo Sơn Trà (L.polygon)
 * @returns {boolean} Trạng thái hiển thị mới
 */
export function toggleSonTraArea() {
    if (!mapInstance) return false;

    if (!areaLayer) {
        areaLayer = L.layerGroup().addTo(mapInstance);
    }

    if (isAreaActive) {
        areaLayer.clearLayers();
        isAreaActive = false;
        showToast("Đã ẩn ranh giới Bán đảo Sơn Trà.", "info");
        return false;
    }

    // Tọa độ đa giác bao quanh Bán đảo Sơn Trà
    const sonTraBoundary = [
        [16.095, 108.240],
        [16.128, 108.225],
        [16.148, 108.260],
        [16.145, 108.305],
        [16.115, 108.320],
        [16.082, 108.285],
        [16.088, 108.255]
    ];

    areaLayer.clearLayers();

    const polygon = L.polygon(sonTraBoundary, {
        color: "#059669",
        weight: 3,
        fillColor: "#10b981",
        fillOpacity: 0.22,
        dashArray: "6, 6"
    }).addTo(areaLayer);

    polygon.bindPopup(`
        <div style="font-size: 13px; line-height: 1.45;">
            <div style="display:inline-block; padding: 2px 8px; border-radius: 12px; background: #ecfdf5; color: #059669; font-size: 11px; font-weight: 700; margin-bottom: 6px;">
                Khu bảo tồn thiên nhiên
            </div>
            <h4 style="margin: 0 0 6px; font-size: 15px; color: #064e3b; font-weight: 800;">⛰️ Bán Đảo Sơn Trà (Lá Phổi Xanh)</h4>
            <p style="margin: 0 0 6px; color: #334155; font-size: 12px;">Diện tích hơn 4.400 ha rừng nguyên sinh, nơi cư ngụ của "Nữ hoàng linh trưởng" - loài Voọc Chà Vá Chân Nâu quý hiếm.</p>
            <p style="margin: 0; color: #059669; font-size: 11.5px; font-weight: 600;">✨ Điểm nổi bật: Chùa Linh Ứng, Đỉnh Bàn Cờ, Cây Đa Ngàn Năm, Bãi Bụt, Bãi Rạng.</p>
        </div>
    `);

    mapInstance.fitBounds(polygon.getBounds(), { padding: [40, 40] });
    polygon.openPopup();

    isAreaActive = true;
    showToast("Đã vẽ ranh giới bảo tồn thiên nhiên Bán đảo Sơn Trà!", "success", 3500);
    return true;
}
