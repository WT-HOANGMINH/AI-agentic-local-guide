
/* =====================================
   DA NANG GUIDE - RECOMMENDATIONS
===================================== */

document.addEventListener('DOMContentLoaded', async () => {

  // 1. Kiểm tra đăng nhập Google OAuth hoặc Email Demo
  if (!(await protect())) {
    return;
  }

  // 2. Lấy các thành phần giao diện
  const host = $('#recommend-grid');
  const sel = $('#recommend-category');

  // Kiểm tra các phần tử có tồn tại không
  if (!host || !sel) {
    return;
  }
  // Kiem tra phien dang nhap Facebook truoc khi hien thi goi y
try {
  await API.getProfile();
} catch (error) {
  console.warn('Khong the xac thuc phien:', error);
}

  // 3. Hàm tải danh sách địa điểm gợi ý
  async function load() {

    host.textContent = 'Đang lấy đề xuất…';

    try {

      // Lấy danh sách địa điểm gợi ý
      const places = await API.recommend(sel.value);

      // Lấy danh sách địa điểm yêu thích
      const favorites = await API.favorites();

      // Hiển thị danh sách địa điểm
      host.innerHTML = places.map(place => {

        const isFavorite = favorites.includes(place.id);

        return `
          <div class="col-md-6 col-xl-3">
            ${placeCard(place, isFavorite)}
          </div>
        `;

      }).join('') || '<div class="empty">Chưa có gợi ý.</div>';
      // Cap nhat nut Da them vao lich trinh
      await syncItineraryButtons(host);

    } catch (error) {

      host.textContent = '';

      flash(error.message || 'Không thể tải gợi ý địa điểm.');
    }
  }

  // 4. Lọc theo danh mục
  sel.addEventListener('change', load);

  // 5. Xử lý nút Yêu thích và Thêm lịch trình
  wirePlaceActions(host);

  // 6. Tải dữ liệu khi mở trang
  await load();

});
