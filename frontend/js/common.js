
/* =========================================
   DA NANG GUIDE - COMMON JAVASCRIPT
========================================= */

// ===== HAM TIEN ICH =====

const $ = sel => document.querySelector(sel);
const $$ = sel => [...document.querySelectorAll(sel)];

const esc = s => String(s ?? '').replace(
  /[&<>"']/g,
  c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[c])
);



const flashTimers = new WeakMap();

function flash(
  message,
  type = 'danger',
  target = '#message',
  shouldScroll = true
) {
  const box = $(target);
  if (!box) return;

  // Huy bo dem cu neu co thong bao moi
  const oldTimer = flashTimers.get(box);

  if (oldTimer !== undefined) {
    clearTimeout(oldTimer);
  }

  // Hien thi thong bao
  box.innerHTML = `
    <div class="alert alert-${type}" role="alert">
      ${esc(message)}
    </div>
  `;
  // Chi cuon trang khi can thiet
  if (shouldScroll) {
    box.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest'
    });
  }

  // Tu dong an sau 3 giay
  const timer = setTimeout(() => {
    box.replaceChildren();
    flashTimers.delete(box);
  }, 3000);

  flashTimers.set(box, timer);
}



// ===== KIEM TRA DANG NHAP =====



async function protect() {

  // 1. Neu dang chay che do Demo
  if (window.LOCAL_GUIDE_CONFIG?.USE_MOCK) {

    if (API.isLogged()) {
      return true;
    }

    window.location.replace("login.html");
    return false;
  }

  // 2. Kiem tra dang nhap voi Backend
  try {

    // API.getProfile() goi /auth/me bang JWT
    const user = await API.getProfile();

    if (user) {
      console.log("Dang nhap thanh cong:", user.name);
      return true;
    }

  } catch (error) {
    console.error(
      "Loi xac minh tai khoan:",
      error
    );
  }

  // 3. Chua dang nhap hoac token khong hop le
  window.location.replace("login.html");

  return false;
}

// =========================================
// ANH DIA DIEM
// =========================================

const placeImages = {
  "Cầu Rồng": "images/caurong.jpg",
  "Bãi biển Mỹ Khê": "images/bien-my-khe-da-nang.jpg",
  "Ngũ Hành Sơn": "images/nguhanhson.jpg",
  "Bán đảo Sơn Trà": "images/Ban-dao-son-tra.jpg",
  "Bảo tàng Điêu khắc Chăm": "images/bao-tang-dieu-khac-cham.jpg",
  "Chợ Hàn": "images/chohan.jpg",
  "Cầu Tình Yêu": "images/cautinhyeu.webp",
  "Đỉnh Bàn Cờ": "images/dinhbanco.jpg",
  "Ghềnh Bàng": "images/ghenhbang.jpg",
  "Bãi Bụt": "images/baibut.webp",
  "Mũi Nghê": "images/Muinghe.webp",
  "Hải đăng Tiên Sa": "images/haidangtiensa.jpg",
  "Nhất Lâm Thủy Trang Trà": "images/nhatlamthuytrangtra.jpg",
  "Cầu vòm Đồn Cả": "images/cauvomdonca.jpg",
  "Thác Ba Đờ Phọt": "images/thacbadophot.jpg",
  "Hồ Hòa Trung": "images/hohoatrung.jpg",
  "Giếng Trời": "images/giengtroi.webp",
  "Bãi Rạn Nam Ô": "images/rannamo.webp",
  "Rừng thông Bồ Bồ": "images/rungthongbobo.jpg",
  "Thánh địa Mỹ Sơn": "images/thanhdiamyson.jpg",
  "Công viên Văn hóa Ấn Tượng Hội An": "images/congvienantuonghoian.jpg",
  "Sun World Bà Nà Hills và Cầu Vàng": "images/banahillscauvang.jpg",
  "Chùa Linh Ứng Sơn Trà": "images/chualinhung.jpg",
  "Bãi biển Non Nước": "images/baibiennonnuoc.jpg",
  "Nhà thờ Chính tòa Đà Nẵng": "images/nhathochinhtoa.webp",
  "Làng đá mỹ nghệ Non Nước": "images/langdanonnuoc.jpg",
  "Đèo Hải Vân": "images/deohaivan.jpg",
  "Phố cổ Hội An": "images/phocohoian.jpg",
  "Chùa Cầu Hội An": "images/chuacauhoian.webp",
  "Rừng dừa Bảy Mẫu": "images/rungduabaymau.jpg",
  "Biển An Bàng": "images/bienanbang.jpg",
  "Làng gốm Thanh Hà": "images/langgomthanhha.webp",
  "Làng rau Trà Quế": "images/langrautraque.jpg",
  "Bánh xèo Bà Dưỡng": "images/banhxeobaduong.jpg",
  "Mì Quảng Bà Mua": "images/miquangbamua.jpg",
  "Bánh tráng cuốn thịt heo Trần": "images/banhtrangcuonthitheo.jpg",
  "Bún chả cá Nguyễn Chí Thanh": "images/bunchacanguyenchithanh.jpg",
  "Bánh mì Phượng": "images/banhmiphuong.jpg",
  "Cao lầu Thanh": "images/caolauthanh.jpg",
  "Cơm gà Bà Buội": "images/comgababuoi.jpg",
  "Cộng Cà Phê Bạch Đằng": "images/congcaphebachdang.jpg",
  "Hội An Roastery": "images/hoianroastery.jpg",
  "Faifo Coffee": "images/faifocoffee.webp",
  "Trình Cà Phê": "images/trinhcaphe.jpg",
  "Wonderlust Danang": "images/wonderlustdanang.jpg",
  "Chợ Cồn": "images/chocon.jpg",
  "Chợ đêm Sơn Trà": "images/chodemsontra.jpg",
  "Chợ Hội An": "images/chohoian.jpg",
  "Chợ đêm Hội An": "images/chodemhoian.jpg",

};

const placeImageAliases = {
  'Bãi Biển Nam Ô': 'Bãi Rạn Nam Ô',
  'Bãi Biển Mỹ Khê': 'Bãi biển Mỹ Khê',
  'Bãi biển Nam Ô': 'Bãi Rạn Nam Ô',
  'Bãi Bụt Sơn Trà': 'Bãi Bụt',
  'Bảo tàng Điêu khắc Chăm': 'Bảo tàng Điêu khắc Chăm',
  'Cầu Rồng Đà Nẵng': 'Cầu Rồng',
  'Cầu Tình Yêu Đà Nẵng': 'Cầu Tình Yêu',
  'Cầu vòm Đồn Cả': 'Cầu vòm Đồn Cả',
  'Chợ Hàn': 'Chợ Hàn',
  'Đỉnh Bàn Cờ': 'Đỉnh Bàn Cờ',
  'Ghềnh Bàng': 'Ghềnh Bàng',
  'Hồ Hòa Trung': 'Hồ Hòa Trung',
  'Mũi Nghê': 'Mũi Nghê',
  'Ngọn Thủy Sơn (Ngũ Hành Sơn)': 'Ngũ Hành Sơn',
  'Thánh địa Mỹ Sơn': 'Thánh địa Mỹ Sơn',
  'Bán đảo Sơn Trà': 'Bán đảo Sơn Trà'
};



// Lay anh dua theo ten dia diem
function getPlaceImage(p) {
  if (p.image) return p.image;

  const name = String(p.name || '').trim();
  const imageName = placeImageAliases[name] || name;
  return placeImages[imageName] || "";
}


// =========================================
// THANH DIEU HUONG - NAVBAR
// =========================================

function renderNav() {

  const currentPage =
    location.pathname.split('/').pop() || 'index.html';

  const host = $('#site-nav');
  if (!host) return;

  const links = [
    ['index.html', 'Trang chủ'],
    ['places.html', 'Địa điểm'],
    ['recommendations.html', 'Gợi ý'],
    ['map.html', 'Bản đồ'],
    ['chat.html', 'Chat AI']
  ];

  host.innerHTML = `
    <nav class="navbar navbar-expand-lg travel-navbar">
      <div class="container">

        <!-- LOGO -->
        <a class="navbar-brand travel-brand" href="index.html">
          <span class="travel-logo">
            <svg
              width="25"
              height="25"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="9"></circle>
              <path d="m15.5 8.5-2 5-5 2 2-5 5-2z"></path>
            </svg>
          </span>

          <span class="travel-brand-text">
            <strong>DaNang<span>Guide</span></strong>
            <small>EXPLORE DA NANG</small>
          </span>
        </a>

        <!-- MENU MOBILE -->
        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navItems"
          aria-controls="navItems"
          aria-expanded="false"
          aria-label="Mở menu"
        >
          <span class="navbar-toggler-icon"></span>
        </button>

        <!-- MENU CHINH -->
        <div class="collapse navbar-collapse" id="navItems">

          <div class="navbar-nav mx-auto travel-links">
            ${links.map(([href, label]) => `
              <a
                class="nav-link ${currentPage === href ? 'active' : ''}"
                href="${href}"
                ${currentPage === href ? 'aria-current="page"' : ''}
              >
                ${label}
              </a>
            `).join('')}
          </div>

          <div class="travel-account" id="account-actions"></div>

        </div>
      </div>
    </nav>
  `;

  const actions = $('#account-actions');

  if (API.isLogged()) {

    actions.innerHTML = `
      <span class="account-greeting">
        Xin chào, ${esc(API.user()?.name || 'bạn')}
      </span>

      <button
        class="btn btn-outline-primary"
        id="logout"
        type="button"
      >
        Đăng xuất
      </button>
    `;

    $('#logout').onclick = () => API.logout();

  } else {

    actions.innerHTML = `
      <a class="travel-login" href="login.html">
        Đăng nhập
      </a>

      <a
        class="btn btn-primary travel-register"
        href="register.html"
      >
        Đăng ký
      </a>
    `;
  }
}


// =========================================
// FOOTER
// =========================================

function renderFooter() {

  const footer = $('#site-footer');
  if (!footer) return;

  footer.innerHTML = `
    <footer class="footer">
      <div class="container d-flex flex-wrap
                  justify-content-between
                  align-items-center gap-2">

        <span>
          © 2026 DaNang Guide.
          Khám phá Đà Nẵng theo cách của bạn.
        </span>

        <span id="mode-label"></span>
      </div>
    </footer>
  `;

  const label = $('#mode-label');

  if (label) {
    label.textContent = CFG.USE_MOCK
      ? '● DEMO MODE — dữ liệu minh họa'
      : '● API MODE — FastAPI';
  }
}


// =========================================
// HIEN THI THE DIA DIEM CO ANH
// =========================================

function placeCard(p, fav = false, eagerImage = false) {

  // Lay duong dan anh
  const imageUrl = getPlaceImage(p);

  // Kiem tra toa do
  const hasCoordinates =
    p.latitude !== null &&
    p.latitude !== undefined &&
    p.longitude !== null &&
    p.longitude !== undefined &&
    Number.isFinite(Number(p.latitude)) &&
    Number.isFinite(Number(p.longitude));

  const mapUrl = hasCoordinates
    ? `map.html?place=${encodeURIComponent(p.id)}`
    : `https://www.openstreetmap.org/search?query=${
        encodeURIComponent(p.name + ', Đà Nẵng, Việt Nam')
      }`;

  return `
    <article class="card-soft place-card">

      <!-- HINH ANH DIA DIEM -->
      <div class="place-art">

        ${
          imageUrl
            ? `
              <img
                src="${esc(imageUrl)}"
                alt="${esc(p.name)}"
                class="place-image"
                loading="${eagerImage ? 'eager' : 'lazy'}"
                onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
              >
              <span
                class="place-fallback"
                style="display:none"
                aria-hidden="true"
              >
                ${esc(p.emoji || '📍')}
              </span>
            `
            : `
              <span class="place-fallback" aria-hidden="true">
                ${esc(p.emoji || '📍')}
              </span>
            `
        }

        <!-- DANH GIA -->
        <span class="badge text-bg-light">
          ${
            p.rating == null
              ? 'Địa điểm mới'
              : '⭐ ' + esc(p.rating)
          }
        </span>

      </div>

      <!-- NOI DUNG -->
      <div class="card-body">

        <span class="tag">
          ${esc(p.category || 'Địa điểm')}
        </span>

        <h5>${esc(p.name)}</h5>

        <p class="small muted mb-2">
          📍 ${esc(p.district || 'Đà Nẵng')}
        </p>

        <p class="muted small">
          ${esc(p.description || '')}
        </p>

        ${
          p.distanceNote
            ? `<p class="small muted">
                 📏 ${esc(p.distanceNote)}
               </p>`
            : ''
        }

        <!-- CAC NUT CHUC NANG -->
        <div class="d-flex gap-2 flex-wrap">

          <a
           class="btn btn-sm btn-primary"
          href="place.html?id=${encodeURIComponent(p.id)}"
          >
          Chi tiết
          </a>

          <a
            class="btn btn-sm btn-outline-primary"
            href="${mapUrl}"
            ${!hasCoordinates
              ? 'target="_blank" rel="noopener noreferrer"'
              : ''}
          >
            ${hasCoordinates ? 'Xem bản đồ' : 'Tra vị trí'}
          </a>

          ${
            API.isLogged()
              ? `
                <button
                  type="button"
                  data-favorite="${esc(p.id)}"
                  class="btn btn-sm ${
                    fav ? 'btn-primary' : 'btn-outline-secondary'
                  }"
                >
                  ${fav ? '♥ Đã lưu' : '♡ Yêu thích'}
                </button>

                <button
                  type="button"
                  data-add="${esc(p.id)}"
                  class="btn btn-sm btn-outline-secondary"
                >
                  + Lịch trình
                </button>
              `
              : ''
          }

        </div>
      </div>
    </article>
  `;
}


// =========================================
// XU LY YEU THICH VA LICH TRINH
// =========================================

function markItineraryButton(button, added) {
  if (!button) return;
  button.dataset.added = String(added);
  button.textContent = added
    ? '✓ Đã thêm · Bỏ'
    : '+ Lịch trình';

  button.classList.toggle('btn-success', added);
  button.classList.toggle('btn-outline-secondary', !added);

  // Khong khoa nut sau khi them thanh cong
  button.disabled = false;
}

// Cap nhat trang thai cac nut khi tai danh sach
async function syncItineraryButtons(container) {
  if (!container || !API.isLogged()) return;

  const buttons = container.querySelectorAll('[data-add]');
  if (!buttons.length) return;

  try {
    const ids = await API.itinerary();
    const savedIds = new Set(ids.map(Number));

    buttons.forEach(button => {
      const id = Number(button.dataset.add);

      markItineraryButton(
        button,
        savedIds.has(id)
      );
    });

  } catch (error) {
    console.warn(
      'Khong the tai trang thai lich trinh:',
      error
    );
  }
}

async function wirePlaceActions(container) {
  const modalElement = document.getElementById('addToItineraryModal');
  const totalDaysSelect = document.getElementById('trip-total-days');
  const selectedDaySelect = document.getElementById('trip-selected-day');
  const selectedPlaceName = document.getElementById('selected-place-name');
  const modalMessage = document.getElementById('itinerary-modal-message');
  const confirmButton = document.getElementById('confirm-add-to-itinerary');

  let pendingPlaceId = null;
  let manualItinerary = null;
  let saving = false;

  const modal = modalElement && window.bootstrap
    ? bootstrap.Modal.getOrCreateInstance(modalElement)
    : null;

  function showModalError(message) {
    if (modalMessage) {
      modalMessage.textContent = message;
    }
  }

  function fillDaysSelect(totalDays) {
    if (!totalDaysSelect) return;

    const days = Math.max(
      1,
      Math.min(30, Number(totalDays) || 1)
    );

    totalDaysSelect.innerHTML = Array.from(
      { length: 30 },
      (_, index) => {
        const day = index + 1;

        return `
          <option value="${day}">
            ${day} ngày
          </option>
        `;
      }
    ).join('');

    totalDaysSelect.value = String(days);
    fillSelectedDay();
  }

  function fillSelectedDay() {
    if (!selectedDaySelect || !totalDaysSelect) return;

    const total = Number(totalDaysSelect.value);
    const previous = Number(selectedDaySelect.value) || 1;

    selectedDaySelect.innerHTML = Array.from(
      { length: total },
      (_, index) => {
        const day = index + 1;

        return `
          <option value="${day}">
            Ngày ${day}
          </option>
        `;
      }
    ).join('');

    selectedDaySelect.value = String(
      Math.min(previous, total)
    );
  }

  function updatePlaceButtons(placeId, added) {
    container.querySelectorAll('[data-add]').forEach(button => {
      if (Number(button.dataset.add) === Number(placeId)) {
        markItineraryButton(button, added);
      }
    });
  }

  if (totalDaysSelect) {
    totalDaysSelect.addEventListener(
      'change',
      fillSelectedDay
    );
  }

  if (modalElement) {
    modalElement.addEventListener('hidden.bs.modal', () => {
      pendingPlaceId = null;
      manualItinerary = null;
      showModalError('');
    });
  }

  // Xu ly nut Luu trong hop thoai
  if (confirmButton) {
    confirmButton.addEventListener('click', async () => {
      if (saving || pendingPlaceId === null) return;

      saving = true;
      confirmButton.disabled = true;
      showModalError('');

      try {
        const totalDays = Number(totalDaysSelect.value);
        const selectedDay = Number(selectedDaySelect.value);

        if (
          !Number.isInteger(totalDays) ||
          totalDays < 1 ||
          totalDays > 30 ||
          !Number.isInteger(selectedDay) ||
          selectedDay < 1 ||
          selectedDay > totalDays
        ) {
          throw new Error('Số ngày du lịch không hợp lệ.');
        }

        // Tai lai du lieu moi nhat truoc khi luu
        manualItinerary = await API.getManualItinerary();

        let itineraryId;

        if (manualItinerary) {
          itineraryId = manualItinerary.id;

          const existingItems = manualItinerary.items || [];

          const alreadyAdded = existingItems.some(
            item => Number(item.place_id) === pendingPlaceId
          );

          if (alreadyAdded) {
            throw new Error(
              'Địa điểm này đã có trong lịch trình.'
            );
          }

          const maxUsedDay = existingItems.reduce(
            (max, item) => Math.max(
              max,
              Number(item.day_number) || 1
            ),
            1
          );

          if (totalDays < maxUsedDay) {
            throw new Error(
              `Lịch trình đã có địa điểm ở Ngày ${maxUsedDay}. ` +
              'Vui lòng chọn số ngày phù hợp.'
            );
          }

          // Cap nhat so ngay neu nguoi dung thay doi
          if (Number(manualItinerary.total_days) !== totalDays) {
            await API.updateItineraryDays(
              itineraryId,
              totalDays
            );
          }

          const dayItems = existingItems.filter(
            item => Number(item.day_number) === selectedDay
          );

          const nextOrder = dayItems.reduce(
            (max, item) => Math.max(
              max,
              Number(item.order_index) || 0
            ),
            0
          ) + 1;

          await API.addItineraryItem(
            itineraryId,
            pendingPlaceId,
            selectedDay,
            nextOrder
          );

        } else {
          // Tao lich trinh thu cong moi
          const created = await API.request(
            '/itineraries/',
            {
              method: 'POST',
              auth: true,
              body: {
                title: 'Lịch trình Đà Nẵng',
                description: 'manual_places_v1',
                total_days: totalDays,
                items: [
                  {
                    place_id: pendingPlaceId,
                    day_number: selectedDay,
                    order_index: 1
                  }
                ]
              }
            }
          );

          itineraryId = created.id;
        }

        updatePlaceButtons(pendingPlaceId, true);

        modal.hide();

        flash(
          `Đã thêm địa điểm vào Ngày ${selectedDay} thành công!`,
          'success',
          '#message',
          false
        );

      } catch (error) {
        showModalError(
          error.message || 'Không thể lưu địa điểm.'
        );
      } finally {
        saving = false;
        confirmButton.disabled = false;
      }
    });
  }

  // Xu ly cac nut tren the dia diem
  container.addEventListener('click', async event => {
    const favoriteButton = event.target.closest('[data-favorite]');
    const addButton = event.target.closest('[data-add]');

    if (favoriteButton) {
      try {
        const id = Number(favoriteButton.dataset.favorite);

        await API.toggleFavorite(id);

        const wasSaved = favoriteButton.textContent.includes('Đã lưu');

        favoriteButton.textContent = wasSaved
          ? '♡ Yêu thích'
          : '♥ Đã lưu';

        favoriteButton.classList.toggle('btn-primary');
        favoriteButton.classList.toggle('btn-outline-secondary');

      } catch (error) {
        flash(error.message);
      }

      return;
    }

    if (!addButton || addButton.disabled) return;

    addButton.disabled = true;

    try {
      const placeId = Number(addButton.dataset.add);

      if (!Number.isInteger(placeId) || placeId < 1) {
        throw new Error('Địa điểm không hợp lệ.');
      }

      manualItinerary = await API.getManualItinerary();

      const existingItems = manualItinerary?.items || [];

      const matchingItems = existingItems.filter(
        item => Number(item.place_id) === placeId
      );

      // Neu da them: xoa dung mot dia diem
      if (matchingItems.length > 0) {
        if (matchingItems.length !== 1) {
          throw new Error(
            'Địa điểm xuất hiện nhiều lần trong lịch trình. ' +
            'Vui lòng xóa tại trang Lịch trình của tôi.'
          );
        }

        await API.deleteItineraryItem(
          manualItinerary.id,
          matchingItems[0].id
        );

        updatePlaceButtons(placeId, false);

        flash(
          'Đã bỏ địa điểm khỏi lịch trình.',
          'success',
          '#message',
          false
        );

        return;
      }

      // Neu chua them: mo hop thoai chon ngay
      if (!modal || !totalDaysSelect || !selectedDaySelect) {
        throw new Error(
          'Không tìm thấy hộp thoại chọn ngày du lịch.'
        );
      }

      pendingPlaceId = placeId;

      const card = addButton.closest('article');
      const nameElement = card?.querySelector('h5, h3, h2');

      if (selectedPlaceName) {
        selectedPlaceName.textContent =
          nameElement?.textContent?.trim() || 'Địa điểm đã chọn';
      }

      fillDaysSelect(manualItinerary?.total_days || 1);

      showModalError('');
      modal.show();

    } catch (error) {
      flash(
        error.message || 'Không thể cập nhật lịch trình.',
        'danger',
        '#message',
        false
      );
    } finally {
      addButton.disabled = false;
    }
  });
}

// =========================================
// KHOI TAO WEBSITE
// =========================================

document.addEventListener('DOMContentLoaded', () => {
  renderNav();
  renderFooter();

  if (!location.pathname.endsWith('/chat.html')) {
    const streamStyles = document.createElement('link');
    streamStyles.rel = 'stylesheet';
    streamStyles.href = 'css/chat-stream.css?v=truthful-progress-2';
    document.head.appendChild(streamStyles);

    const streamScript = document.createElement('script');
    streamScript.src = 'js/chat-stream.js?v=truthful-progress-2';
    streamScript.onload = () => {
      const chatScript = document.createElement('script');
      chatScript.src = 'js/chat-widget.js?v=chat-controls-stream-2';
      chatScript.onload = () => {
        if (!window.DGChat) {
          console.error('Không khởi tạo được chat streaming.');
          return;
        }
        window.DGChat.init({
          messages: '#dgfw-messages',
          input: '#dgfw-input',
          send: '#dgfw-send',
          chips: '#dgfw-suggestions',
          userClass: 'dgfw-message dgfw-user',
          botClass: 'dgfw-message dgfw-assistant',
        });
      };
      document.body.appendChild(chatScript);
    };
    streamScript.onerror = () => {
      console.error('Không tải được bộ điều khiển chat streaming.');
    };
    document.body.appendChild(streamScript);
  }
});
