/* =========================================================
   DA NANG GUIDE - AUTHENTICATION SCRIPT
   - Xử lý Đăng ký / Đăng nhập thường
   - Xử lý Đăng nhập bằng Google (Google Identity Services & OAuth 2.0)
   - Tự động nhận diện token khi hoàn tất Google OAuth Callback
   ========================================================= */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#auth-form');
  const googleBtn = document.querySelector('#google-login') || document.querySelector('#google-register') || document.querySelector('#google-quick-help');
  const googleBtnContainer = document.querySelector('#google-signin-btn-container');
  const facebookBtn = document.querySelector('#facebook-login-btn') || document.querySelector('#facebook-register-btn');
  const facebookQuickHelp = document.querySelector('#facebook-quick-help');

  const GOOGLE_CLIENT_ID = (window.LOCAL_GUIDE_CONFIG && window.LOCAL_GUIDE_CONFIG.GOOGLE_CLIENT_ID) ||
    '853984856354-131ekmamkn9sqn75mbckbbm0805ab21m.apps.googleusercontent.com';
  const FACEBOOK_APP_ID = (window.LOCAL_GUIDE_CONFIG && window.LOCAL_GUIDE_CONFIG.FACEBOOK_APP_ID) ||
    '1092777120272337';

  // 1. Kiểm tra Token từ URL Callback (sau khi Google hoặc Facebook OAuth 2.0 redirect)
  const urlParams = new URLSearchParams(location.search);
  const tokenFromUrl = urlParams.get('token');
  const googleError = urlParams.get('google_error');
  const facebookError = urlParams.get('facebook_error');

  if (googleError) {
    if (typeof flash === 'function') {
      flash(
        window.getLang && window.getLang() === 'en'
          ? `Google login notice: ${googleError}`
          : `Thông báo đăng nhập Google: ${googleError}`,
        'warning'
      );
    }
  }

  if (facebookError) {
    if (typeof flash === 'function') {
      flash(
        window.getLang && window.getLang() === 'en'
          ? `Facebook login notice: ${facebookError}`
          : `Thông báo đăng nhập Facebook: ${facebookError}`,
        'warning'
      );
    }
  }

  if (tokenFromUrl) {
    const isFacebook = urlParams.get('facebook_login') === '1';
    const cfg = window.LOCAL_GUIDE_CONFIG || {};
    localStorage.setItem(cfg.TOKEN_KEY || 'localguide_token', tokenFromUrl);
    if (typeof flash === 'function') {
      const msg = isFacebook
        ? (window.getLang && window.getLang() === 'en'
            ? 'Facebook Sign-in successful! Redirecting...'
            : 'Đăng nhập Facebook thành công! Đang chuyển hướng...')
        : (window.getLang && window.getLang() === 'en'
            ? 'Google Sign-in successful! Redirecting...'
            : 'Đăng nhập Google thành công! Đang chuyển hướng...');
      flash(msg, 'success');
    }
    if (typeof API !== 'undefined' && API.getProfile) {
      API.getProfile().finally(() => {
        setTimeout(() => { location.href = 'index.html'; }, 500);
      });
    } else {
      setTimeout(() => { location.href = 'index.html'; }, 500);
    }
    return;
  }


  // 2. Kiểm tra thông báo đăng ký thành công từ URL
  if (urlParams.has('registered')) {
    if (typeof flash === 'function') {
      flash(
        window.getLang && window.getLang() === 'en'
          ? 'Account created successfully. Please log in.'
          : 'Tạo tài khoản thành công. Hãy đăng nhập.',
        'success'
      );
    }
  }

  // 3. Xử lý Form Đăng nhập / Đăng ký truyền thống
  if (form) {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const button = form.querySelector('button[type=submit]');
      const name = document.querySelector('#name')?.value.trim();
      const email = document.querySelector('#email')?.value.trim().toLowerCase();
      const password = document.querySelector('#password')?.value;

      if (!password || password.length < 6) {
        if (typeof flash === 'function') {
          flash(
            window.getLang && window.getLang() === 'en'
              ? 'Password must be at least 6 characters.'
              : 'Mật khẩu phải có ít nhất 6 ký tự.',
            'warning'
          );
        }
        return;
      }

      button.disabled = true;
      try {
        if (form.dataset.type === 'register') {
          if (!name) {
            if (typeof flash === 'function') {
              flash(
                window.getLang && window.getLang() === 'en'
                  ? 'Please enter your full name.'
                  : 'Hãy nhập họ và tên của bạn.',
                'warning'
              );
            }
            button.disabled = false;
            return;
          }
          await API.register(name, email, password);
          location.href = 'login.html?registered=1';
        } else {
          await API.login(email, password);
          if (typeof flash === 'function') {
            flash(
              window.getLang && window.getLang() === 'en'
                ? 'Login successful! Redirecting...'
                : 'Đăng nhập thành công! Đang chuyển hướng...',
              'success'
            );
          }
          setTimeout(() => {
            location.href = 'index.html';
          }, 400);
        }
      } catch (err) {
        if (typeof flash === 'function') {
          flash(err.message || 'Đã xảy ra lỗi khi xác thực.', 'danger');
        }
      } finally {
        button.disabled = false;
      }
    });
  }

  // Đảm bảo API.googleLogin luôn sẵn sàng kể cả khi api.js bị browser cache phiên bản cũ
  if (typeof window.API !== 'undefined' && !window.API.googleLogin) {
    window.API.googleLogin = async function(payload = {}) {
      let apiBase = window.LOCAL_GUIDE_CONFIG?.API_BASE || '';
      if (!apiBase && typeof location !== 'undefined' && (location.port === '5500' || location.port === '3000' || location.port === '5173')) {
        apiBase = 'http://127.0.0.1:8000';
      }
      const cfg = window.LOCAL_GUIDE_CONFIG || {};
      const res = await fetch(apiBase + '/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.message || 'Xác thực Google thất bại.');
      }
      localStorage.setItem(cfg.TOKEN_KEY || 'localguide_token', data.access_token);
      const user = {
        id: data.user_id,
        name: data.username || (payload.name || (payload.email ? payload.email.split('@')[0] : 'Google User')),
        email: data.email || payload.email,
        role: data.role,
        picture: payload.picture || ''
      };
      localStorage.setItem('lg_current_user', JSON.stringify(user));
      return user;
    };
  }

  // Đảm bảo API.facebookLogin luôn sẵn sàng kể cả khi api.js bị browser cache phiên bản cũ
  if (typeof window.API !== 'undefined' && !window.API.facebookLogin) {
    window.API.facebookLogin = async function(payload = {}) {
      let apiBase = window.LOCAL_GUIDE_CONFIG?.API_BASE || '';
      if (!apiBase && typeof location !== 'undefined' && (location.port === '5500' || location.port === '3000' || location.port === '5173')) {
        apiBase = 'http://127.0.0.1:8000';
      }
      const cfg = window.LOCAL_GUIDE_CONFIG || {};
      const res = await fetch(apiBase + '/auth/facebook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.message || 'Xác thực Facebook thất bại.');
      }
      localStorage.setItem(cfg.TOKEN_KEY || 'localguide_token', data.access_token);
      const user = {
        id: data.user_id,
        name: data.username || (payload.name || (payload.email ? payload.email.split('@')[0] : 'Facebook User')),
        email: data.email || payload.email,
        role: data.role,
        picture: payload.picture || ''
      };
      localStorage.setItem('lg_current_user', JSON.stringify(user));
      return user;
    };
  }


  // 4. Hàm thực thi đăng nhập Google gửi về Backend
  async function performGoogleAuth(payload) {
    try {
      if (typeof flash === 'function') {
        flash(
          window.getLang && window.getLang() === 'en'
            ? 'Authenticating with Google...'
            : 'Đang xác thực với Google...',
          'info'
        );
      }

      let user;
      if (typeof API !== 'undefined' && typeof API.googleLogin === 'function') {
        user = await API.googleLogin(payload);
      } else {
        let apiBase = window.LOCAL_GUIDE_CONFIG?.API_BASE || '';
        if (!apiBase && typeof location !== 'undefined' && (location.port === '5500' || location.port === '3000' || location.port === '5173')) {
          apiBase = 'http://127.0.0.1:8000';
        }
        const cfg = window.LOCAL_GUIDE_CONFIG || {};
        const res = await fetch(apiBase + '/auth/google', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || data.message || 'Xác thực Google thất bại.');
        }
        localStorage.setItem(cfg.TOKEN_KEY || 'localguide_token', data.access_token);
        user = {
          id: data.user_id,
          name: data.username || (payload.name || (payload.email ? payload.email.split('@')[0] : 'Google User')),
          email: data.email || payload.email,
          role: data.role,
          picture: payload.picture || ''
        };
        localStorage.setItem('lg_current_user', JSON.stringify(user));
      }

      if (typeof flash === 'function') {
        flash(
          window.getLang && window.getLang() === 'en'
            ? `Google Sign-in successful! Welcome, ${user.name || user.email}.`
            : `Đăng nhập Google thành công! Xin chào ${user.name || user.email}.`,
          'success'
        );
      }

      // Đóng modal nếu đang mở
      const modalEl = document.querySelector('#google-auth-modal');
      if (modalEl && window.bootstrap) {
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
      }

      setTimeout(() => {
        location.href = 'index.html';
      }, 500);
    } catch (err) {
      if (typeof flash === 'function') {
        flash(err.message || 'Đăng nhập Google thất bại.', 'danger');
      }
    }
  }

  // 5. Khởi tạo Google Identity Services (GIS) & OAuth2 Token Client
  let tokenClient = null;

  function initGoogleIdentityServices() {
    if (!window.google?.accounts) {
      setTimeout(initGoogleIdentityServices, 300);
      return;
    }

    try {
      // A. Khởi tạo Google ID Services (ID Token)
      if (window.google.accounts.id) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: async (response) => {
            if (response && response.credential) {
              await performGoogleAuth({ credential: response.credential });
            }
          },
          auto_select: false,
          cancel_on_tap_outside: true
        });

        // Render nút Google chính thức nếu có thẻ chứa
        if (googleBtnContainer) {
          window.google.accounts.id.renderButton(googleBtnContainer, {
            theme: 'outline',
            size: 'large',
            type: 'standard',
            text: 'continue_with',
            shape: 'rectangular',
            logo_alignment: 'left',
            width: googleBtnContainer.offsetWidth || 340
          });
        }
      }

      // B. Khởi tạo Google OAuth2 Token Client (Popup flow)
      if (window.google.accounts.oauth2) {
        tokenClient = window.google.accounts.oauth2.initTokenClient({
          client_id: GOOGLE_CLIENT_ID,
          scope: 'openid email profile',
          callback: async (tokenResponse) => {
            if (tokenResponse.error) {
              console.warn('Google OAuth2 error:', tokenResponse);
              showGoogleLoginModal(tokenResponse.error_description || tokenResponse.error);
              return;
            }
            if (tokenResponse.access_token) {
              await performGoogleAuth({ access_token: tokenResponse.access_token });
            }
          }
        });
      }
    } catch (err) {
      console.warn('Google Identity Services notice:', err);
    }
  }

  initGoogleIdentityServices();

  // 6. Modal hỗ trợ đăng nhập Google
  function showGoogleLoginModal(errorMessage = '') {
    let modal = document.querySelector('#google-auth-modal');
    if (!modal) {
      const modalHTML = `
        <div class="modal fade" id="google-auth-modal" tabindex="-1" aria-labelledby="googleModalLabel" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered" style="max-width: 480px;">
            <div class="modal-content border-0 shadow-lg rounded-4 overflow-hidden">
              <div class="modal-header border-0 pb-0 pt-4 px-4">
                <div class="d-flex align-items-center gap-2">
                  <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="24" height="24" alt="Google">
                  <h5 class="modal-title fw-bold mb-0 text-dark" id="googleModalLabel">
                    ${window.getLang && window.getLang() === 'en' ? 'Sign in with Google' : 'Đăng nhập với Google'}
                  </h5>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>

              <div class="modal-body px-4 py-3">
                <div id="google-modal-notice"></div>

                <div class="alert alert-info py-2 px-3 small mb-3">
                  <strong>Client ID đã sẵn sàng:</strong>
                  <div class="text-truncate text-muted font-monospace" style="font-size: 11px;">
                    ${GOOGLE_CLIENT_ID}
                  </div>
                </div>

                <p class="text-secondary small mb-2 fw-semibold">
                  ${window.getLang && window.getLang() === 'en' ? 'Quick Login (1-Click Test Accounts):' : 'Đăng nhập nhanh 1-Click (Tài khoản thử nghiệm):'}
                </p>

                <!-- DANH SÁCH TÀI KHOẢN GỢI Ý NHANH -->
                <div class="d-grid gap-2 mb-3">
                  <button type="button" class="btn btn-outline-light text-dark border d-flex align-items-center p-2 text-start rounded-3 google-acc-btn"
                          data-email="hoangminh.dev@gmail.com" data-name="Hoàng Minh">
                    <div class="rounded-circle bg-primary text-white d-grid place-items-center me-3 fw-bold" style="width: 38px; height: 38px; min-width: 38px;">
                      HM
                    </div>
                    <div class="overflow-hidden">
                      <div class="fw-semibold text-truncate">Hoàng Minh</div>
                      <div class="text-secondary small text-truncate">hoangminh.dev@gmail.com</div>
                    </div>
                  </button>

                  <button type="button" class="btn btn-outline-light text-dark border d-flex align-items-center p-2 text-start rounded-3 google-acc-btn"
                          data-email="traveler.danang@gmail.com" data-name="DaNang Traveler">
                    <div class="rounded-circle bg-success text-white d-grid place-items-center me-3 fw-bold" style="width: 38px; height: 38px; min-width: 38px;">
                      DT
                    </div>
                    <div class="overflow-hidden">
                      <div class="fw-semibold text-truncate">DaNang Traveler</div>
                      <div class="text-secondary small text-truncate">traveler.danang@gmail.com</div>
                    </div>
                  </button>
                </div>

                <!-- HOẶC NHẬP TÀI KHOẢN GOOGLE TÙY Ý -->
                <div class="border-top pt-3 mb-3">
                  <label class="form-label small fw-semibold text-secondary mb-1">
                    ${
                      window.getLang && window.getLang() === 'en'
                        ? 'Or enter your Google email address:'
                        : 'Hoặc nhập địa chỉ email Google của bạn:'
                    }
                  </label>
                  <div class="input-group">
                    <input type="email" id="custom-google-email" class="form-control" placeholder="ten_cua_ban@gmail.com">
                    <button type="button" id="btn-custom-google-submit" class="btn btn-primary px-3">
                      ${window.getLang && window.getLang() === 'en' ? 'Continue' : 'Đăng nhập'}
                    </button>
                  </div>
                </div>

                <!-- NÚT CHUYỂN HƯỚNG TRỰC TIẾP OAUTH2 GOOGLE CHÍNH THỨC -->
                <div class="border-top pt-3">
                  <button type="button" id="btn-google-oauth-redirect" class="btn btn-outline-secondary w-100 py-2 d-flex align-items-center justify-content-center gap-2 small">
                    <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="16" height="16" alt="">
                    <span>${window.getLang && window.getLang() === 'en' ? 'Open Google Consent Screen (OAuth 2.0)' : 'Mở màn hình Google OAuth chính thức'}</span>
                  </button>
                  <div class="text-muted mt-1" style="font-size: 11px; line-height: 1.3;">
                    * Lưu ý: Màn hình Google OAuth thật yêu cầu thêm URL vào <em>Authorized redirect URIs</em> trên Google Cloud Console.
                  </div>
                </div>
              </div>

              <div class="modal-footer border-0 pt-0 pb-3 px-4 justify-content-between">
                <span class="text-muted" style="font-size: 11px;">🔒 Google OAuth 2.0 Identity Protocol</span>
                <button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">
                  ${window.getLang && window.getLang() === 'en' ? 'Close' : 'Đóng'}
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
      document.body.insertAdjacentHTML('beforeend', modalHTML);
      modal = document.querySelector('#google-auth-modal');

      // Sự kiện nút chuyển hướng OAuth redirect
      const redirectBtn = modal.querySelector('#btn-google-oauth-redirect');
      if (redirectBtn) {
        redirectBtn.addEventListener('click', async () => {
          try {
            let apiBase = window.LOCAL_GUIDE_CONFIG?.API_BASE || '';
            if (!apiBase && typeof location !== 'undefined' && (location.port === '5500' || location.port === '3000')) {
              apiBase = 'http://127.0.0.1:8000';
            }
            const res = await fetch(`${apiBase}/auth/google/url?redirect_uri=${encodeURIComponent('http://127.0.0.1:8000/auth/google/callback')}`);
            if (res.ok) {
              const data = await res.json();
              if (data.auth_url) {
                location.href = data.auth_url;
                return;
              }
            }
          } catch (e) {
            console.error('Lỗi lấy google auth url:', e);
          }
          const cb = 'http://127.0.0.1:8000/auth/google/callback';
          const oauthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=${encodeURIComponent(cb)}&response_type=code&scope=openid%20email%20profile&access_type=offline&prompt=select_account`;
          location.href = oauthUrl;
        });
      }

      // Gắn sự kiện click cho các tài khoản gợi ý
      modal.querySelectorAll('.google-acc-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const email = btn.dataset.email;
          const name = btn.dataset.name;
          performGoogleAuth({ email, name });
        });
      });

      // Gắn sự kiện cho email tùy nhập
      const customBtn = modal.querySelector('#btn-custom-google-submit');
      const customInput = modal.querySelector('#custom-google-email');
      if (customBtn && customInput) {
        customBtn.addEventListener('click', () => {
          const email = customInput.value.trim().toLowerCase();
          if (!email || !email.includes('@')) {
            alert(
              window.getLang && window.getLang() === 'en'
                ? 'Please enter a valid email address.'
                : 'Vui lòng nhập đúng địa chỉ email Google.'
            );
            return;
          }
          const name = email.split('@')[0];
          performGoogleAuth({ email, name });
        });
      }
    }

    // Hiển thị thông báo nếu có lỗi
    const noticeEl = modal.querySelector('#google-modal-notice');
    if (noticeEl) {
      if (errorMessage) {
        noticeEl.innerHTML = `
          <div class="alert alert-warning py-2 px-3 small mb-3">
            <strong>Thông báo từ Google:</strong> ${errorMessage}
          </div>
        `;
      } else {
        noticeEl.innerHTML = '';
      }
    }

    if (window.bootstrap) {
      const bsModal = new bootstrap.Modal(modal);
      bsModal.show();
    } else {
      const defaultEmail = 'hoangminh.dev@gmail.com';
      const promptEmail = prompt(
        window.getLang && window.getLang() === 'en'
          ? 'Enter your Google email to sign in:'
          : 'Nhập địa chỉ email Google để đăng nhập:',
        defaultEmail
      );
      if (promptEmail) {
        performGoogleAuth({ email: promptEmail, name: promptEmail.split('@')[0] });
      }
    }
  }

  // 7. Gắn sự kiện cho nút "Tiếp tục với Google"
  if (googleBtn) {
    googleBtn.addEventListener('click', e => {
      e.preventDefault();
      // Hiển thị Modal lựa chọn đăng nhập Google trực quan & tiện lợi
      showGoogleLoginModal();
    });
  }

  // 8. Hàm thực thi đăng nhập Facebook gửi về Backend
  async function performFacebookAuth(payload) {
    try {
      if (typeof flash === 'function') {
        flash(
          window.getLang && window.getLang() === 'en'
            ? 'Authenticating with Facebook...'
            : 'Đang xác thực với Facebook...',
          'info'
        );
      }

      let user;
      if (typeof API !== 'undefined' && typeof API.facebookLogin === 'function') {
        user = await API.facebookLogin(payload);
      } else {
        let apiBase = window.LOCAL_GUIDE_CONFIG?.API_BASE || '';
        if (!apiBase && typeof location !== 'undefined' && (location.port === '5500' || location.port === '3000' || location.port === '5173')) {
          apiBase = 'http://127.0.0.1:8000';
        }
        const cfg = window.LOCAL_GUIDE_CONFIG || {};
        const res = await fetch(apiBase + '/auth/facebook', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || data.message || 'Xác thực Facebook thất bại.');
        }
        localStorage.setItem(cfg.TOKEN_KEY || 'localguide_token', data.access_token);
        user = {
          id: data.user_id,
          name: data.username || (payload.name || (payload.email ? payload.email.split('@')[0] : 'Facebook User')),
          email: data.email || payload.email,
          role: data.role,
          picture: payload.picture || ''
        };
        localStorage.setItem('lg_current_user', JSON.stringify(user));
      }

      if (typeof flash === 'function') {
        flash(
          window.getLang && window.getLang() === 'en'
            ? `Facebook Sign-in successful! Welcome, ${user.name || user.email}.`
            : `Đăng nhập Facebook thành công! Xin chào ${user.name || user.email}.`,
          'success'
        );
      }

      // Đóng modal nếu đang mở
      const modalEl = document.querySelector('#facebook-auth-modal');
      if (modalEl && window.bootstrap) {
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
      }

      setTimeout(() => {
        location.href = 'index.html';
      }, 500);
    } catch (err) {
      if (typeof flash === 'function') {
        flash(err.message || 'Đăng nhập Facebook thất bại.', 'danger');
      }
    }
  }

  // 9. Khởi tạo Facebook JavaScript SDK
  function initFacebookSDK() {
    window.fbAsyncInit = function() {
      if (window.FB) {
        try {
          window.FB.init({
            appId: FACEBOOK_APP_ID,
            cookie: true,
            xfbml: true,
            version: 'v19.0'
          });
        } catch (e) {
          console.warn('Facebook SDK init error:', e);
        }
      }
    };

    if (window.FB && typeof window.FB.init === 'function') {
      try {
        window.FB.init({
          appId: FACEBOOK_APP_ID,
          cookie: true,
          xfbml: true,
          version: 'v19.0'
        });
      } catch (e) {
        console.warn('Facebook SDK immediate init error:', e);
      }
    }
  }

  initFacebookSDK();

  // 10. Modal hỗ trợ đăng nhập Facebook
  function showFacebookLoginModal(errorMessage = '') {
    let modal = document.querySelector('#facebook-auth-modal');
    if (!modal) {
      const modalHTML = `
        <div class="modal fade" id="facebook-auth-modal" tabindex="-1" aria-labelledby="facebookModalLabel" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered" style="max-width: 480px;">
            <div class="modal-content border-0 shadow-lg rounded-4 overflow-hidden">
              <div class="modal-header border-0 pb-0 pt-4 px-4">
                <div class="d-flex align-items-center gap-2">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="#1877f2">
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                  </svg>
                  <h5 class="modal-title fw-bold mb-0 text-dark" id="facebookModalLabel">
                    ${window.getLang && window.getLang() === 'en' ? 'Sign in with Facebook' : 'Đăng nhập với Facebook'}
                  </h5>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>

              <div class="modal-body px-4 py-3">
                <div id="facebook-modal-notice"></div>

                <div class="alert alert-primary py-2 px-3 small mb-3" style="background-color: #ebf5ff; border-color: #bee3f8;">
                  <strong>Facebook App ID đã kết nối:</strong>
                  <div class="text-truncate font-monospace fw-bold text-primary" style="font-size: 13px;">
                    ${FACEBOOK_APP_ID}
                  </div>
                </div>

                <p class="text-secondary small mb-2 fw-semibold">
                  ${window.getLang && window.getLang() === 'en' ? 'Quick Login (1-Click Test Accounts):' : 'Đăng nhập nhanh 1-Click (Tài khoản thử nghiệm):'}
                </p>

                <!-- DANH SÁCH TÀI KHOẢN GỢI Ý NHANH -->
                <div class="d-grid gap-2 mb-3">
                  <button type="button" class="btn btn-outline-light text-dark border d-flex align-items-center p-2 text-start rounded-3 fb-acc-btn"
                          data-email="hoangminh.facebook@gmail.com" data-name="Hoàng Minh" data-id="1092777120272337_01">
                    <div class="rounded-circle text-white d-grid place-items-center me-3 fw-bold" style="width: 38px; height: 38px; min-width: 38px; background-color: #1877f2;">
                      HM
                    </div>
                    <div class="overflow-hidden">
                      <div class="fw-semibold text-truncate">Hoàng Minh (Facebook)</div>
                      <div class="text-secondary small text-truncate">hoangminh.facebook@gmail.com</div>
                    </div>
                  </button>

                  <button type="button" class="btn btn-outline-light text-dark border d-flex align-items-center p-2 text-start rounded-3 fb-acc-btn"
                          data-email="traveler.danang@facebook.com" data-name="DaNang Explorer" data-id="1092777120272337_02">
                    <div class="rounded-circle text-white d-grid place-items-center me-3 fw-bold" style="width: 38px; height: 38px; min-width: 38px; background-color: #0d6efd;">
                      DE
                    </div>
                    <div class="overflow-hidden">
                      <div class="fw-semibold text-truncate">DaNang Explorer (Facebook)</div>
                      <div class="text-secondary small text-truncate">traveler.danang@facebook.com</div>
                    </div>
                  </button>
                </div>

                <!-- HOẶC NHẬP TÀI KHOẢN FACEBOOK TÙY Ý -->
                <div class="border-top pt-3 mb-3">
                  <label class="form-label small fw-semibold text-secondary mb-1">
                    ${
                      window.getLang && window.getLang() === 'en'
                        ? 'Or enter your Facebook name / email address:'
                        : 'Hoặc nhập họ tên / địa chỉ email Facebook của bạn:'
                    }
                  </label>
                  <div class="input-group">
                    <input type="text" id="custom-fb-input" class="form-control" placeholder="Nguyễn Văn A hoặc email@gmail.com">
                    <button type="button" id="btn-custom-fb-submit" class="btn btn-primary px-3" style="background-color: #1877f2; border-color: #1877f2;">
                      ${window.getLang && window.getLang() === 'en' ? 'Continue' : 'Đăng nhập'}
                    </button>
                  </div>
                </div>

                <!-- NÚT CHUYỂN HƯỚNG TRỰC TIẾP OAUTH2 FACEBOOK CHÍNH THỨC -->
                <div class="border-top pt-3">
                  <button type="button" id="btn-facebook-oauth-redirect" class="btn btn-outline-primary w-100 py-2 d-flex align-items-center justify-content-center gap-2 small">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                    </svg>
                    <span>${window.getLang && window.getLang() === 'en' ? 'Open Facebook Login (OAuth 2.0 Dialog)' : 'Mở màn hình Facebook Login chính thức'}</span>
                  </button>
                  <div class="text-muted mt-1" style="font-size: 11px; line-height: 1.3;">
                    * Lưu ý: Màn hình Facebook OAuth thật yêu cầu thêm URL vào <em>Valid OAuth Redirect URIs</em> trong Facebook App Settings.
                  </div>
                </div>
              </div>

              <div class="modal-footer border-0 pt-0 pb-3 px-4 justify-content-between">
                <span class="text-muted" style="font-size: 11px;">🔒 Facebook Graph & OAuth 2.0 Security</span>
                <button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">
                  ${window.getLang && window.getLang() === 'en' ? 'Close' : 'Đóng'}
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
      document.body.insertAdjacentHTML('beforeend', modalHTML);
      modal = document.querySelector('#facebook-auth-modal');

      // Sự kiện nút chuyển hướng OAuth redirect Facebook
      const redirectBtn = modal.querySelector('#btn-facebook-oauth-redirect');
      if (redirectBtn) {
        redirectBtn.addEventListener('click', async () => {
          try {
            let apiBase = window.LOCAL_GUIDE_CONFIG?.API_BASE || '';
            if (!apiBase && typeof location !== 'undefined' && (location.port === '5500' || location.port === '3000')) {
              apiBase = 'http://127.0.0.1:8000';
            }
            const cb = 'http://127.0.0.1:8000/auth/facebook/callback';
            const res = await fetch(`${apiBase}/auth/facebook/url?redirect_uri=${encodeURIComponent(cb)}`);
            if (res.ok) {
              const data = await res.json();
              if (data.auth_url) {
                location.href = data.auth_url;
                return;
              }
            }
          } catch (e) {
            console.error('Lỗi lấy facebook auth url:', e);
          }
          const cb = 'http://127.0.0.1:8000/auth/facebook/callback';
          const oauthUrl = `https://www.facebook.com/v19.0/dialog/oauth?client_id=${FACEBOOK_APP_ID}&redirect_uri=${encodeURIComponent(cb)}&response_type=code&scope=email,public_profile`;
          location.href = oauthUrl;
        });
      }

      // Gắn sự kiện click cho các tài khoản Facebook gợi ý
      modal.querySelectorAll('.fb-acc-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const email = btn.dataset.email;
          const name = btn.dataset.name;
          const facebook_id = btn.dataset.id;
          performFacebookAuth({ email, name, facebook_id });
        });
      });

      // Gắn sự kiện cho email hoặc tên tùy nhập
      const customBtn = modal.querySelector('#btn-custom-fb-submit');
      const customInput = modal.querySelector('#custom-fb-input');
      if (customBtn && customInput) {
        customBtn.addEventListener('click', () => {
          const val = customInput.value.trim();
          if (!val) {
            alert(
              window.getLang && window.getLang() === 'en'
                ? 'Please enter your Facebook name or email.'
                : 'Vui lòng nhập tên hoặc email Facebook.'
            );
            return;
          }
          let email = '';
          let name = '';
          if (val.includes('@')) {
            email = val.toLowerCase();
            name = email.split('@')[0];
          } else {
            name = val;
            email = `fb_${Date.now()}@facebook.com`;
          }
          performFacebookAuth({ email, name, facebook_id: `fb_${Date.now()}` });
        });
      }
    }

    // Hiển thị thông báo nếu có lỗi
    const noticeEl = modal.querySelector('#facebook-modal-notice');
    if (noticeEl) {
      if (errorMessage) {
        noticeEl.innerHTML = `
          <div class="alert alert-warning py-2 px-3 small mb-3">
            <strong>Thông báo từ Facebook:</strong> ${errorMessage}
          </div>
        `;
      } else {
        noticeEl.innerHTML = '';
      }
    }

    if (window.bootstrap) {
      const bsModal = new bootstrap.Modal(modal);
      bsModal.show();
    } else {
      const defaultEmail = 'hoangminh.facebook@gmail.com';
      const promptEmail = prompt(
        window.getLang && window.getLang() === 'en'
          ? 'Enter your Facebook email or name to sign in:'
          : 'Nhập địa chỉ email hoặc tên Facebook để đăng nhập:',
        defaultEmail
      );
      if (promptEmail) {
        performFacebookAuth({
          email: promptEmail.includes('@') ? promptEmail : `fb_${Date.now()}@facebook.com`,
          name: promptEmail.split('@')[0]
        });
      }
    }
  }

  // 11. Gắn sự kiện cho nút Facebook Login & Register
  if (facebookBtn) {
    facebookBtn.addEventListener('click', (e) => {
      e.preventDefault();
      // Nếu Facebook SDK sẵn sàng, gọi FB.login popup
      if (window.FB && typeof window.FB.login === 'function') {
        try {
          window.FB.login((response) => {
            if (response.authResponse && response.authResponse.accessToken) {
              const accessToken = response.authResponse.accessToken;
              const userID = response.authResponse.userID;
              window.FB.api('/me', { fields: 'name,email,picture.type(large)' }, (profile) => {
                performFacebookAuth({
                  access_token: accessToken,
                  facebook_id: userID,
                  email: profile?.email,
                  name: profile?.name,
                  picture: profile?.picture?.data?.url
                });
              });
            } else {
              console.warn('Facebook login status:', response);
              showFacebookLoginModal(response.status === 'not_authorized' ? 'Tài khoản chưa được thêm vào quyền thử nghiệm của App.' : '');
            }
          }, { scope: 'public_profile,email' });
          return;
        } catch (err) {
          console.warn('Facebook SDK invocation error:', err);
        }
      }

      // Nếu SDK chưa tải được hoặc bị chặn, mở Modal tùy chọn tiện lợi
      showFacebookLoginModal();
    });
  }

  if (facebookQuickHelp) {
    facebookQuickHelp.addEventListener('click', (e) => {
      e.preventDefault();
      showFacebookLoginModal();
    });
  }
});


