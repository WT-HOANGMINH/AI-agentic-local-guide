
/* =====================================
   DA NANG GUIDE - PLACES
===================================== */

document.addEventListener('DOMContentLoaded', async () => {

  // =====================================
  // 1. LAY CAC THANH PHAN GIAO DIEN
  // =====================================

  const host = $('#places-grid');
  const form = $('#search-form');
  const q = $('#query');
  const category = $('#category');
  const count = $('#count');

  // Kiem tra cac thanh phan co ton tai khong
  if (!host || !form || !q || !category) {
    return;
  }

  // =====================================
  // 2. HAM TAI DANH SACH DIA DIEM
  // =====================================

  async function load() {

    // Hien thi trang thai dang tai
    host.innerHTML = `
      <div class="col-12 muted">
        Đang tải địa điểm…
      </div>
    `;

    try {

      // Lay danh sach dia diem theo tu khoa va danh muc
      const places = await API.places({
        q: q.value.trim(),
        category: category.value
      });

      // Lay danh sach yeu thich cua tai khoan Demo
      const saved = API.isLogged()
        ? await API.favorites()
        : [];

      // Hien thi danh sach dia diem
      if (places.length > 0) {

        host.innerHTML = places.map(place => {

          const isFavorite = saved.includes(place.id);

          return `
            <div class="col-md-6 col-xl-4">
              ${placeCard(place, isFavorite)}
            </div>
          `;

        }).join('');

      } else {

        // Khong tim thay dia diem phu hop
        host.innerHTML = `
          <div class="col-12 empty">
            Không tìm thấy địa điểm phù hợp.
          </div>
        `;
      }

      // Cap nhat so luong dia diem
      if (count) {
        count.textContent = places.length + ' địa điểm';
      }

    } catch (error) {

      // Xu ly loi khi tai du lieu
      host.innerHTML = '';

      flash(
        error.message || 'Không thể tải danh sách địa điểm.'
      );
    }
  }

  // =====================================
  // 3. XU LY FORM TIM KIEM
  // =====================================

  form.addEventListener('submit', event => {

    event.preventDefault();

    load();
  });

  // =====================================
  // 4. LOC DIA DIEM THEO DANH MUC
  // =====================================

  category.addEventListener('change', load);

  // =====================================
  // 5. XU LY YEU THICH VA THEM LICH TRINH
  // =====================================

  wirePlaceActions(host);

  // =====================================
  // 6. TAI DIA DIEM KHI MO TRANG
  // =====================================

  await load();

});
