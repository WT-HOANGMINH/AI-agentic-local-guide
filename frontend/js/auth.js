// ============================================
// AUTHENTICATION & MODAL CONTROLLER
// ============================================

import { authApi } from "./api.js";
import { escapeHTML, showToast } from "./utils.js";

const TOKEN_KEY = "access_token";
const USER_KEY = "user_profile";

/**
 * Trả về JWT Access Token hiện tại từ localStorage
 * @returns {string|null}
 */
export function getAccessToken() {
    return localStorage.getItem(TOKEN_KEY);
}

/**
 * Trả về thông tin người dùng đang đăng nhập
 * @returns {{ id: number, username: string, email: string, role: string }|null}
 */
export function getCurrentUser() {
    try {
        const raw = localStorage.getItem(USER_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

/**
 * Lưu thông tin phiên đăng nhập vào localStorage
 * @param {string} token 
 * @param {object} user 
 */
export function saveSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * Xóa phiên đăng nhập khỏi localStorage
 */
export function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

/**
 * Kiểm tra xem người dùng đã đăng nhập chưa
 * @returns {boolean}
 */
export function isAuthenticated() {
    return !!getAccessToken();
}

// ============================================
// QUẢN LÝ GIAO DIỆN MODAL ĐĂNG NHẬP / ĐĂNG KÝ
// ============================================

let authDialog = null;
let authAlert = null;
let loginForm = null;
let registerForm = null;

/**
 * Khởi tạo toàn bộ sự kiện cho hệ thống xác thực
 */
export function initAuth() {
    authDialog = document.getElementById("authDialog");
    authAlert = document.getElementById("authAlert");
    loginForm = document.getElementById("loginForm");
    registerForm = document.getElementById("registerForm");

    // Các nút kích hoạt Modal trên Topbar
    const openLoginBtn = document.getElementById("openLoginBtn");
    const openRegisterBtn = document.getElementById("openRegisterBtn");
    const closeDialogBtn = document.getElementById("closeAuthDialogBtn");
    const logoutBtn = document.getElementById("logoutBtn");

    if (openLoginBtn) {
        openLoginBtn.addEventListener("click", () => openAuthModal("login"));
    }
    if (openRegisterBtn) {
        openRegisterBtn.addEventListener("click", () => openAuthModal("register"));
    }
    if (closeDialogBtn) {
        closeDialogBtn.addEventListener("click", closeAuthModal);
    }
    if (logoutBtn) {
        logoutBtn.addEventListener("click", handleLogout);
    }

    // Đóng modal khi nhấp ra ngoài backdrop
    if (authDialog) {
        authDialog.addEventListener("click", (event) => {
            const rect = authDialog.getBoundingClientRect();
            const isInDialog = (
                rect.top <= event.clientY &&
                event.clientY <= rect.top + rect.height &&
                rect.left <= event.clientX &&
                event.clientX <= rect.left + rect.width
            );
            if (!isInDialog) {
                closeAuthModal();
            }
        });

        // Lắng nghe phím ESC để đóng mượt mà
        authDialog.addEventListener("cancel", () => {
            clearAlert();
        });
    }

    // Chuyển đổi tab Đăng nhập <-> Đăng ký
    const tabButtons = document.querySelectorAll(".auth-tab-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const tabName = btn.dataset.tab;
            switchAuthTab(tabName);
        });
    });

    // Các liên kết chuyển tab bên dưới form
    const goToRegisterLink = document.getElementById("goToRegisterLink");
    const goToLoginLink = document.getElementById("goToLoginLink");

    if (goToRegisterLink) {
        goToRegisterLink.addEventListener("click", (e) => {
            e.preventDefault();
            switchAuthTab("register");
        });
    }
    if (goToLoginLink) {
        goToLoginLink.addEventListener("click", (e) => {
            e.preventDefault();
            switchAuthTab("login");
        });
    }

    // Toggle hiển thị mật khẩu
    setupPasswordToggles();

    // Lắng nghe sự kiện Submit form
    if (loginForm) {
        loginForm.addEventListener("submit", handleLoginSubmit);
    }
    if (registerForm) {
        registerForm.addEventListener("submit", handleRegisterSubmit);
    }

    // Đồng bộ trạng thái đăng nhập từ localStorage khi tải trang
    syncAuthUI();

    // Xác thực lại token với backend nếu đã có token
    if (isAuthenticated()) {
        verifySessionWithBackend();
    }
}

/**
 * Mở Modal xác thực với tab chỉ định
 * @param {"login"|"register"} tabName 
 */
export function openAuthModal(tabName = "login") {
    if (!authDialog) return;
    clearAlert();
    switchAuthTab(tabName);

    if (typeof authDialog.showModal === "function") {
        authDialog.showModal();
    } else {
        authDialog.setAttribute("open", "");
    }

    // Focus vào ô nhập đầu tiên
    setTimeout(() => {
        if (tabName === "login") {
            const emailInput = document.getElementById("loginEmail");
            if (emailInput) emailInput.focus();
        } else {
            const usernameInput = document.getElementById("registerUsername");
            if (usernameInput) usernameInput.focus();
        }
    }, 100);
}

/**
 * Đóng Modal xác thực
 */
export function closeAuthModal() {
    if (!authDialog) return;
    if (typeof authDialog.close === "function") {
        authDialog.close();
    } else {
        authDialog.removeAttribute("open");
    }
    clearAlert();
}

/**
 * Chuyển đổi tab Đăng nhập và Đăng ký
 * @param {"login"|"register"} tabName 
 */
export function switchAuthTab(tabName) {
    clearAlert();

    const tabButtons = document.querySelectorAll(".auth-tab-btn");
    tabButtons.forEach(btn => {
        if (btn.dataset.tab === tabName) {
            btn.classList.add("active");
            btn.setAttribute("aria-selected", "true");
        } else {
            btn.classList.remove("active");
            btn.setAttribute("aria-selected", "false");
        }
    });

    const loginSection = document.getElementById("loginTabSection");
    const registerSection = document.getElementById("registerTabSection");

    if (loginSection && registerSection) {
        if (tabName === "login") {
            loginSection.classList.remove("hidden");
            registerSection.classList.add("hidden");
        } else {
            loginSection.classList.add("hidden");
            registerSection.classList.remove("hidden");
        }
    }
}

/**
 * Cài đặt nút bật/tắt hiển thị mật khẩu
 */
function setupPasswordToggles() {
    const toggleButtons = document.querySelectorAll(".toggle-password-btn");
    toggleButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.dataset.target;
            const input = document.getElementById(targetId);
            if (!input) return;

            if (input.type === "password") {
                input.type = "text";
                btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;
                btn.setAttribute("aria-label", "Ẩn mật khẩu");
            } else {
                input.type = "password";
                btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
                btn.setAttribute("aria-label", "Hiển thị mật khẩu");
            }
        });
    });
}

/**
 * Hiển thị thông báo bên trong Modal
 * @param {string} message 
 * @param {"error"|"success"|"info"} type 
 */
function showAlert(message, type = "error") {
    if (!authAlert) return;
    authAlert.className = `auth-alert auth-alert-${type}`;
    authAlert.innerHTML = `
        <span class="auth-alert-icon">${type === "success" ? "✓" : "⚠"}</span>
        <span>${escapeHTML(message)}</span>
    `;
    authAlert.classList.remove("hidden");
}

/**
 * Xóa thông báo bên trong Modal
 */
function clearAlert() {
    if (!authAlert) return;
    authAlert.innerHTML = "";
    authAlert.className = "auth-alert hidden";
}

// ============================================
// XỬ LÝ SUBMIT FORM
// ============================================

/**
 * Xử lý sự kiện đăng nhập
 */
async function handleLoginSubmit(event) {
    event.preventDefault();
    clearAlert();

    const emailInput = document.getElementById("loginEmail");
    const passwordInput = document.getElementById("loginPassword");
    const submitBtn = document.getElementById("loginSubmitBtn");

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
        showAlert("Vui lòng điền đầy đủ email và mật khẩu", "error");
        return;
    }

    setButtonLoading(submitBtn, true, "Đang đăng nhập...");

    try {
        const response = await authApi.login({ email, password });

        // Lưu token và thông tin người dùng vào localStorage
        const user = {
            id: response.user_id,
            username: response.username,
            email: response.email,
            role: response.role
        };
        saveSession(response.access_token, user);

        // Cập nhật giao diện
        syncAuthUI();
        closeAuthModal();

        // Xóa mật khẩu trong ô input
        passwordInput.value = "";

        showToast(`Xin chào ${user.username}! Đăng nhập thành công.`, "success");
    } catch (error) {
        console.error("Lỗi đăng nhập:", error);
        showAlert(error.message || "Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.", "error");
    } finally {
        setButtonLoading(submitBtn, false, "Đăng nhập");
    }
}

/**
 * Xử lý sự kiện đăng ký
 */
async function handleRegisterSubmit(event) {
    event.preventDefault();
    clearAlert();

    const usernameInput = document.getElementById("registerUsername");
    const emailInput = document.getElementById("registerEmail");
    const passwordInput = document.getElementById("registerPassword");
    const confirmInput = document.getElementById("registerConfirmPassword");
    const submitBtn = document.getElementById("registerSubmitBtn");

    const username = usernameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const confirmPassword = confirmInput.value;

    if (!username || !email || !password) {
        showAlert("Vui lòng điền đầy đủ tất cả các trường", "error");
        return;
    }

    if (username.length < 3) {
        showAlert("Tên người dùng phải có tối thiểu 3 ký tự", "error");
        return;
    }

    if (password.length < 6) {
        showAlert("Mật khẩu phải có tối thiểu 6 ký tự", "error");
        return;
    }

    if (password !== confirmPassword) {
        showAlert("Mật khẩu xác nhận không khớp nhau", "error");
        return;
    }

    setButtonLoading(submitBtn, true, "Đang tạo tài khoản...");

    try {
        await authApi.register({ username, email, password });

        // Chuyển sang tab đăng nhập và điền sẵn email
        switchAuthTab("login");
        const loginEmailInput = document.getElementById("loginEmail");
        if (loginEmailInput) {
            loginEmailInput.value = email;
        }

        // Xóa form đăng ký
        usernameInput.value = "";
        emailInput.value = "";
        passwordInput.value = "";
        confirmInput.value = "";

        showAlert("Đăng ký tài khoản thành công! Vui lòng đăng nhập để tiếp tục.", "success");
        showToast("Tạo tài khoản thành công! Hãy đăng nhập ngay.", "success");
    } catch (error) {
        console.error("Lỗi đăng ký:", error);
        showAlert(error.message || "Đăng ký thất bại. Vui lòng thử lại.", "error");
    } finally {
        setButtonLoading(submitBtn, false, "Tạo tài khoản");
    }
}

/**
 * Xử lý đăng xuất
 */
export function handleLogout() {
    const user = getCurrentUser();
    clearSession();
    syncAuthUI();
    showToast(`Đã đăng xuất ${user ? user.username : ""}.`, "info");
}

/**
 * Cập nhật trạng thái loading cho nút bấm
 */
function setButtonLoading(button, isLoading, text) {
    if (!button) return;
    button.disabled = isLoading;
    if (isLoading) {
        button.innerHTML = `<span class="spinner-sm"></span> <span>${escapeHTML(text)}</span>`;
    } else {
        button.innerHTML = `<span>${escapeHTML(text)}</span>`;
    }
}

/**
 * Đồng bộ trạng thái hiển thị của thanh Topbar với localStorage
 */
export function syncAuthUI() {
    const authLoggedOut = document.getElementById("authLoggedOut");
    const authLoggedIn = document.getElementById("authLoggedIn");
    const userNameDisplay = document.getElementById("userNameDisplay");
    const userRoleBadge = document.getElementById("userRoleBadge");
    const userAvatarText = document.getElementById("userAvatarText");

    const user = getCurrentUser();

    if (user && isAuthenticated()) {
        if (authLoggedOut) authLoggedOut.classList.add("hidden");
        if (authLoggedIn) authLoggedIn.classList.remove("hidden");

        if (userNameDisplay) {
            userNameDisplay.textContent = user.username || "Thành viên";
        }
        if (userRoleBadge) {
            userRoleBadge.textContent = user.role === "admin" ? "Admin" : "Thành viên";
            userRoleBadge.className = `role-badge ${user.role === "admin" ? "role-admin" : "role-user"}`;
        }
        if (userAvatarText) {
            const firstChar = (user.username || "U").charAt(0).toUpperCase();
            userAvatarText.textContent = firstChar;
        }
    } else {
        if (authLoggedOut) authLoggedOut.classList.remove("hidden");
        if (authLoggedIn) authLoggedIn.classList.add("hidden");
    }
}

/**
 * Kiểm tra tính hợp lệ của token với API Backend (/auth/me)
 */
async function verifySessionWithBackend() {
    try {
        const user = await authApi.getMe();
        // Cập nhật lại thông tin mới nhất từ database
        saveSession(getAccessToken(), {
            id: user.id,
            username: user.username,
            email: user.email,
            role: user.role
        });
        syncAuthUI();
    } catch (error) {
        if (error.status === 401 || error.status === 403) {
            console.warn("Phiên đăng nhập đã hết hạn hoặc không hợp lệ. Đang dọn dẹp...");
            clearSession();
            syncAuthUI();
            showToast("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "warning");
        }
    }
}
