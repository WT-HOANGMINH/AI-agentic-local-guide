
/* =====================================
   DA NANG GUIDE - AUTHENTICATION
   Dang nhap va dang ky bang Email
===================================== */

document.addEventListener('DOMContentLoaded', () => {

  // =====================================
  // 1. LAY FORM DANG NHAP / DANG KY
  // =====================================

  const form = $('#auth-form');

  // Neu trang khong co form thi dung
  if (!form) {
    return;
  }

  // =====================================
  // 2. XU LY KHI GUI FORM
  // =====================================

  form.addEventListener('submit', async (event) => {

    // Ngan trang tu dong tai lai
    event.preventDefault();

    // Lay cac thanh phan trong form
    const button = form.querySelector('button[type="submit"]');

    const name = $('#name')?.value.trim() || '';

    const email = $('#email')?.value.trim().toLowerCase() || '';

    const password = $('#password')?.value || '';

    // =====================================
    // 3. KIEM TRA DU LIEU
    // =====================================

    if (!email) {
      flash('Vui lòng nhập email.');
      return;
    }

    if (password.length < 6) {
      flash('Mật khẩu phải có ít nhất 6 ký tự.');
      return;
    }

    // Neu la trang dang ky thi yeu cau ho ten
    if (form.dataset.type === 'register' && !name) {
      flash('Hãy nhập họ tên.');
      return;
    }

    // Chan nhan nut nhieu lan
    if (button) {
      button.disabled = true;
    }

    // =====================================
    // 4. DANG NHAP HOAC DANG KY
    // =====================================

    try {

      if (form.dataset.type === 'register') {

        // Dang ky tai khoan Email
        await API.register(name, email, password);

        // Chuyen den trang dang nhap
        window.location.href = 'login.html?registered=1';

      } else {

        // Dang nhap tai khoan Email
        await API.login(email, password);

        // Chuyen den trang chu
        window.location.href = 'index.html';
      }

    } catch (error) {

      // Hien thi thong bao loi
      flash(
        error.message || 'Có lỗi xảy ra. Vui lòng thử lại.'
      );

    } finally {

      // Mo lai nut sau khi xu ly
      if (button) {
        button.disabled = false;
      }
    }
  });

  // =====================================
  // 5. THONG BAO DANG KY THANH CONG
  // =====================================

  const params = new URLSearchParams(window.location.search);

  if (params.has('registered')) {
    flash(
      'Tạo tài khoản thành công. Hãy đăng nhập.',
      'success'
    );
  }

});
