// ============================================
// AGENTIC AI LOCAL GUIDE - FRONTEND
// ============================================

const API_BASE_URL = "http://127.0.0.1:8000";

const DA_NANG = {
    lat: 16.0544,
    lng: 108.2022
};

const map = L.map("map").setView(
    [DA_NANG.lat, DA_NANG.lng],
    13
);

// Ban do OpenStreetMap
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19
}).addTo(map);

const markerLayer = L.layerGroup().addTo(map);

let allPlaces = [];

const placeList = document.getElementById("placeList");
const resultCount = document.getElementById("resultCount");
const searchInput = document.getElementById("searchInput");
const categorySelect = document.getElementById("categorySelect");
const priceSelect = document.getElementById("priceSelect");
const searchButton = document.getElementById("searchButton");
const resetMapButton = document.getElementById("resetMapButton");
const errorMessage = document.getElementById("errorMessage");
const connectionStatus = document.getElementById("connectionStatus");

// Chuyen ma danh muc thanh ten tieng Viet
function getCategoryName(category) {
    const categories = {
        tourist_attraction: "Điểm tham quan",
        restaurant: "Nhà hàng",
        cafe: "Quán cà phê",
        shopping: "Mua sắm"
    };

    return categories[category] || category || "Địa điểm";
}

// Hien thi muc gia
function getPriceText(price) {
    if (price === null || price === undefined) {
        return "Chưa có thông tin giá";
    }

    const number = Number(price);

    if (!Number.isFinite(number)) {
        return "Chưa có thông tin giá";
    }

    return "Mức giá: " + "₫".repeat(Math.max(1, Math.min(number, 5)));
}

// Bao ve noi dung khi hien thi HTML
function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, function (character) {
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

// Chuyen du lieu API ve mang dia diem
function normalizePlaces(data) {
    if (Array.isArray(data)) {
        return data;
    }

    if (data && Array.isArray(data.items)) {
        return data.items;
    }

    if (data && Array.isArray(data.places)) {
        return data.places;
    }

    return [];
}

// Tai danh sach dia diem tu Backend
async function loadPlaces() {
    errorMessage.classList.add("hidden");
    placeList.innerHTML = '<div class="loading">Đang tải địa điểm...</div>';
    connectionStatus.textContent = "Đang kết nối Backend...";

    try {
        const response = await fetch(`${API_BASE_URL}/places/`);

        if (!response.ok) {
            throw new Error(`Backend trả về mã lỗi ${response.status}`);
        }

        const data = await response.json();
        allPlaces = normalizePlaces(data);

        connectionStatus.textContent =
            "Đã kết nối Backend • " + allPlaces.length + " địa điểm";

        renderPlaces();
    } catch (error) {
        console.error("Lỗi tải địa điểm:", error);

        allPlaces = [];
        renderPlaces();

        connectionStatus.textContent = "Chưa kết nối được Backend";

        errorMessage.textContent =
            "Không tải được địa điểm. Hãy kiểm tra Backend tại " +
            API_BASE_URL + " và thử tải lại trang.";

        errorMessage.classList.remove("hidden");
    }
}

// Loc dia diem theo tu khoa, danh muc va muc gia
function getFilteredPlaces() {
    const keyword = searchInput.value.trim().toLocaleLowerCase("vi");
    const category = categorySelect.value;
    const maxPrice = Number(priceSelect.value);

    return allPlaces.filter(function (place) {
        const searchableText = [
            place.name,
            place.category,
            place.address,
            place.description
        ].filter(Boolean).join(" ").toLocaleLowerCase("vi");

        const matchesKeyword =
            !keyword || searchableText.includes(keyword);

        const matchesCategory =
            !category || place.category === category;

        const hasPrice =
            place.price_level === null ||
            place.price_level === undefined;

        const matchesPrice =
            hasPrice || Number(place.price_level) <= maxPrice;

        return matchesKeyword && matchesCategory && matchesPrice;
    });
}

// Hien thi cac the dia diem
function renderPlaces() {
    const places = getFilteredPlaces();

    resultCount.textContent = `${places.length} địa điểm`;

    markerLayer.clearLayers();

    if (places.length === 0) {
        placeList.innerHTML = `
            <div class="empty-state">
                Chưa tìm thấy địa điểm phù hợp.<br>
                Hãy thử từ khóa hoặc bộ lọc khác.
            </div>
        `;
        return;
    }

    placeList.innerHTML = places.map(function (place, index) {
        const name = escapeHTML(place.name || "Địa điểm chưa có tên");
        const category = escapeHTML(getCategoryName(place.category));
        const address = escapeHTML(place.address || "Chưa có địa chỉ");
        const description = escapeHTML(place.description || "");
        const openingHours = escapeHTML(
            place.opening_hours || "Chưa cập nhật"
        );
        const price = escapeHTML(getPriceText(place.price_level));

        return `
            <article class="place-card" data-place-index="${index}">
                <span class="place-category">${category}</span>
                <h3>${name}</h3>
                <p>📍 ${address}</p>
                ${description ? `<p class="place-description">${description}</p>` : ""}
                <p>🕒 ${openingHours}</p>
                <p>💰 ${price}</p>
            </article>
        `;
    }).join("");

    // Tao marker cho cac dia diem co toa do
    places.forEach(function (place, index) {
        const lat = Number(place.latitude);
        const lng = Number(place.longitude);

        if (
            place.latitude === null ||
            place.latitude === undefined ||
            place.longitude === null ||
            place.longitude === undefined ||
            !Number.isFinite(lat) ||
            !Number.isFinite(lng) ||
            Math.abs(lat) > 90 ||
            Math.abs(lng) > 180
        ) {
            return;
        }

        const marker = L.marker([lat, lng]).addTo(markerLayer);

        marker.bindPopup(`
            <strong>${escapeHTML(place.name || "Địa điểm")}</strong>
            <br>
            ${escapeHTML(place.address || "")}
            <br>
            ${escapeHTML(getCategoryName(place.category))}
        `);

        marker.on("click", function () {
            const card = placeList.querySelector(
                `[data-place-index="${index}"]`
            );

            if (card) {
                card.scrollIntoView({
                    behavior: "smooth",
                    block: "nearest"
                });
            }
        });
    });

    // Bam vao the de di den marker tren ban do
    placeList.querySelectorAll(".place-card").forEach(function (card) {
        card.addEventListener("click", function () {
            const index = Number(card.dataset.placeIndex);
            const place = places[index];

            if (
                place &&
                place.latitude != null &&
                place.longitude != null
            ) {
                const lat = Number(place.latitude);
                const lng = Number(place.longitude);

                if (
                    Number.isFinite(lat) &&
                    Number.isFinite(lng) &&
                    Math.abs(lat) <= 90 &&
                    Math.abs(lng) <= 180
                ) {
                    map.flyTo([lat, lng], 16);

                    markerLayer.eachLayer(function (marker) {
                        const position = marker.getLatLng();

                        if (
                            Math.abs(position.lat - lat) < 0.000001 &&
                            Math.abs(position.lng - lng) < 0.000001
                        ) {
                            marker.openPopup();
                        }
                    });
                }
            }
        });
    });
}

// Tim kiem va loc dia diem
searchButton.addEventListener("click", renderPlaces);

searchInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        renderPlaces();
    }
});

categorySelect.addEventListener("change", renderPlaces);
priceSelect.addEventListener("change", renderPlaces);

// Dua ban do ve Da Nang
resetMapButton.addEventListener("click", function () {
    map.flyTo([DA_NANG.lat, DA_NANG.lng], 13);
});

// Khoi dong ung dung
loadPlaces();