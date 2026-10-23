
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


// ===== HIEN THI THONG BAO =====

function flash(message, type = 'danger', target = '#message') {
  const box = $(target);

  if (box) {
    box.innerHTML = `
      <div class="alert alert-${type}" role="alert">
        ${esc(message)}
      </div>
    `;

    box.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest'
    });
  }
}


// ===== KIEM TRA DANG NHAP =====

function protect() {
  if (!API.isLogged()) {
    location.replace('login.html');
    return false;
  }
  return true;
}


// =========================================
// ANH DIA DIEM
// =========================================

// Ten anh phai trung voi ten file trong frontend/images/



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
  "Công viên Văn hóa Ấn Tượng Hội An": "images/congvienantuonghoian.jpg"

};



// Lay anh dua theo ten dia diem
function getPlaceImage(p) {
  return placeImages[p.name] || p.image || "";
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

function placeCard(p, fav = false) {

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
                loading="lazy"
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

async function wirePlaceActions(container) {

  container.addEventListener('click', async event => {

    const favoriteButton =
      event.target.closest('[data-favorite]');

    const addButton =
      event.target.closest('[data-add]');

    try {

      if (favoriteButton) {

        const id = Number(favoriteButton.dataset.favorite);

        await API.toggleFavorite(id);

        const wasSaved =
          favoriteButton.textContent.includes('Đã lưu');

        favoriteButton.textContent = wasSaved
          ? '♡ Yêu thích'
          : '♥ Đã lưu';

        favoriteButton.classList.toggle('btn-primary');
        favoriteButton.classList.toggle('btn-outline-secondary');
      }

      if (addButton) {

        const ids = await API.itinerary();
        const id = Number(addButton.dataset.add);

        if (ids.includes(id)) {
          flash('Địa điểm đã có trong lịch trình.', 'info');
          return;
        }

        await API.saveItinerary([...ids, id]);
        flash('Đã thêm vào lịch trình.', 'success');
      }

    } catch (error) {
      flash(error.message);
    }
  });
}


// =========================================
// KHOI TAO WEBSITE
// =========================================

document.addEventListener('DOMContentLoaded', () => {
  renderNav();
  renderFooter();
});
