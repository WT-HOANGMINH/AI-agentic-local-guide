
/*
  DaNang Guide - OAuth UI
  Google Login: HttpOnly Cookie
  Email Login: Bearer JWT
*/

(() => {
  const CFG = window.LOCAL_GUIDE_CONFIG || {};

  const BACKEND_URL = (
    CFG.API_BASE || "http://127.0.0.1:8000"
  ).replace(/\/$/, "");

  const TOKEN_KEY = CFG.TOKEN_KEY || "localguide_token";

  // =====================================
  // LAY THONG TIN NGUOI DUNG
  // =====================================

  async function getOAuthUser() {
    const params = new URLSearchParams(window.location.search);

    // Neu vua dang nhap Google, xoa Bearer token cu
    // de Backend uu tien cookie Google.
    if (params.get("auth") === "success") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem("lg_current_user");
    }

    const token = localStorage.getItem(TOKEN_KEY);

    const headers = {
      Accept: "application/json"
    };

    // Dang nhap email van su dung Bearer token
    if (token && token !== "demo-token") {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(
      `${BACKEND_URL}/auth/me`,
      {
        method: "GET",
        headers,
        credentials: "include",
        cache: "no-store"
      }
    );

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem("lg_current_user");
      }

      return null;
    }

    const data = await response.json();

    if (!data.id || !data.email) {
      return null;
    }

    const user = {
      id: data.id,
      name: data.username || data.name || data.email,
      email: data.email,
      role: data.role || "user"
    };

    localStorage.setItem(
      "lg_current_user",
      JSON.stringify(user)
    );

    return user;
  }

  // =====================================
  // TIM LINK MENU
  // =====================================

  function findNavLink(nav, filename) {
    return [...nav.querySelectorAll("a[href]")].find(link => {
      const url = new URL(link.href, window.location.href);

      return url.pathname.split("/").pop() === filename;
    });
  }

  // =====================================
  // DANG XUAT
  // =====================================

  async function logout() {
    const response = await fetch(
      `${BACKEND_URL}/auth/logout`,
      {
        method: "POST",
        credentials: "include"
      }
    );

    if (!response.ok) {
      throw new Error("Backend khong the dang xuat.");
    }

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("lg_current_user");
    sessionStorage.removeItem("danang_oauth_user");

    window.location.replace("login.html");
  }

  // =====================================
  // CAP NHAT THANH MENU
  // =====================================

  function updateNavbar(user) {
    const nav = document.getElementById("site-nav");

    if (!nav) return false;

    const loginLink = findNavLink(nav, "login.html");
    const registerLink = findNavLink(nav, "register.html");

    if (!loginLink || !registerLink) {
      return false;
    }

    const username = document.createElement("span");

    username.className = "fw-semibold";
    username.style.color = "#116b61";
    username.textContent = "👤 " + user.name;

    loginLink.replaceWith(username);

    registerLink.textContent = "Đăng xuất";
    registerLink.href = "#";

    registerLink.addEventListener("click", async (event) => {
      event.preventDefault();

      try {
        await logout();
      } catch (error) {
        console.error("Logout error:", error);
        alert("Không thể đăng xuất. Vui lòng thử lại.");
      }
    });

    return true;
  }

  // =====================================
  // THONG BAO DANG NHAP GOOGLE
  // =====================================

  function showSuccessMessage(user) {
    const params = new URLSearchParams(window.location.search);

    if (params.get("auth") !== "success") {
      return;
    }

    const main = document.querySelector("main");

    if (main) {
      const message = document.createElement("div");

      message.className = "alert alert-success mt-3";
      message.setAttribute("role", "status");

      const provider = params.get("provider") || "mạng xã hội";
      message.textContent =
        `Đăng nhập ${provider} thành công! Xin chào ${user.name}.`;

      main.prepend(message);
    }

    // Xoa tham so auth=success
    params.delete("auth");
    params.delete("provider");

    const query = params.toString();

    const cleanUrl =
      window.location.pathname +
      (query ? "?" + query : "") +
      window.location.hash;

    window.history.replaceState({}, "", cleanUrl);
  }

  // =====================================
  // KHOI TAO
  // =====================================

  document.addEventListener("DOMContentLoaded", async () => {
    const params = new URLSearchParams(window.location.search);

    try {
      const user = await getOAuthUser();

      if (!user) {
        sessionStorage.removeItem("danang_oauth_user");
        return;
      }

      sessionStorage.setItem(
        "danang_oauth_user",
        JSON.stringify(user)
      );

      if (!updateNavbar(user)) {
        const nav = document.getElementById("site-nav");

        if (nav) {
          const observer = new MutationObserver(() => {
            if (updateNavbar(user)) {
              observer.disconnect();
            }
          });

          observer.observe(nav, {
            childList: true,
            subtree: true
          });
        }
      }

      showSuccessMessage(user);

    } catch (error) {
      console.error("OAuth error:", error);

      sessionStorage.removeItem("danang_oauth_user");

      if (params.get("auth") === "success") {
        alert("Chưa thể xác minh phiên đăng nhập Google.");
      }
    }
  });
})();
