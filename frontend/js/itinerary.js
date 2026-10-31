
/* =====================================
   DA NANG GUIDE - ITINERARY
   Quan ly lich trinh du lich
===================================== */

document.addEventListener('DOMContentLoaded', async () => {

  // =====================================
  // 1. KIEM TRA DANG NHAP
  // =====================================

  // Ho tro Google OAuth va tai khoan Demo
  if (!(await protect())) {
    return;
  }

  // =====================================
  // 2. LAY CAC THANH PHAN GIAO DIEN
  // =====================================

  const host = $('#itinerary-list');
  const count = $('#itinerary-count');

  if (!host) {
    return;
  }

  // =====================================
  // 3. HAM TAI DANH SACH LICH TRINH
  // =====================================

  async function load() {

    host.innerHTML = `
      <div class="muted">
        Đang tải lịch trình...
      </div>
    `;

    try {

      // Lay danh sach ID dia diem da luu
      const ids = await API.itinerary();

      // Lay danh sach tat ca dia diem
      const places = await API.places({});

      // Tim thong tin dia diem theo ID
      const selected = ids
        .map(id => {
          return places.find(
            place => String(place.id) === String(id)
          );
        })
        .filter(Boolean);

      // =====================================
      // 4. HIEN THI LICH TRINH
      // =====================================

      if (selected.length > 0) {

        host.innerHTML = selected.map((place, index) => {

          return `
            <div class="itinerary-item d-flex
                        justify-content-between
                        align-items-center">

              <span>
                <b>${index + 1}.</b>
                ${esc(place.name)}

                <small class="muted">
                  (${esc(place.district)})
                </small>
              </span>

              <button
                type="button"
                class="btn btn-sm btn-outline-danger"
                data-remove="${esc(place.id)}"
              >
                Xóa
              </button>

            </div>
          `;

        }).join('');

      } else {

        host.innerHTML = `
          <div class="empty">
            Chưa có địa điểm.
            Vào trang Địa điểm để thêm vào lịch trình.
          </div>
        `;
      }

      // Cap nhat so luong diem dung
      if (count) {
        count.textContent =
          selected.length + ' điểm dừng';
      }

    } catch (error) {

      host.innerHTML = '';

      flash(
        error.message || 'Không thể tải lịch trình.'
      );
    }
  }

  // =====================================
  // 5. XOA DIA DIEM KHOI LICH TRINH
  // =====================================

  host.addEventListener('click', async event => {

    const button = event.target.closest('[data-remove]');

    if (!button) {
      return;
    }

    button.disabled = true;

    try {

      // Lay danh sach dia diem da luu
      const ids = await API.itinerary();

      // Lay ID dia diem can xoa
      const removeId = button.dataset.remove;

      // Loc bo dia diem can xoa
      const updatedIds = ids.filter(
        id => String(id) !== String(removeId)
      );

      // Luu lich trinh moi
      await API.saveItinerary(updatedIds);

      // Cap nhat lai giao dien
      await load();

    } catch (error) {

      flash(
        error.message || 'Không thể xóa địa điểm.'
      );

      button.disabled = false;
    }
  });

  // =====================================
  // 6. TAI LICH TRINH KHI MO TRANG
  // =====================================

  await load();

});
