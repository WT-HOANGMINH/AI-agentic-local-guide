
/*
  DaNang Guide - Google/Facebook OAuth UI
  Đồng bộ trạng thái đăng nhập từ FastAPI.
*/

(() => {
  const BACKEND_URL = "http://127.0.0.1:8000";

  // Lấy tài khoản đã xác thực từ Backend.
  async function getOAuthUser() {
    const response = await fetch(
      `${BACKEND_URL}/api/auth/me`,
      {
        method: "GET",
        credentials: "include",
        headers: {
          "Accept": "application/json"
        }
      }
    );

    if (!response.ok) {
      throw new Error("Không có phiên OAuth hợp lệ.");
    }

    const data = await response.json();
    return data.user || null;
  }

  // Tìm liên kết trên thanh điều hướng.
  function findNavLink(nav, filename) {
    return [...nav.querySelectorAll("a[href]")].find(link => {
      const url = new URL(link.href, window.location.href);
      return url.pathname.split("/").pop() === filename;
    });
  }

  // Đổi Đăng nhập / Đăng ký thành tên tài khoản / Đăng xuất.
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
    username.textContent = "👤 " + (user.name || "Tài khoản Google");

    loginLink.replaceWith(username);

    registerLink.textContent = "Đăng xuất";
    registerLink.href = "#";

    registerLink.addEventListener("click", async (event) => {
      event.preventDefault();

      try {
        const response = await fetch(
          `${BACKEND_URL}/api/auth/logout`,
          {
            method: "POST",
            credentials: "include"
          }
        );

        if (!response.ok) {
          throw new Error("Đăng xuất thất bại.");
        }

        sessionStorage.removeItem("danang_oauth_user");

        // Xóa trạng thái đăng nhập demo cũ nếu có.
        localStorage.removeItem("lg_current_user");

        if (window.LOCAL_GUIDE_CONFIG?.TOKEN_KEY) {
          localStorage.removeItem(
            window.LOCAL_GUIDE_CONFIG.TOKEN_KEY
          );
        }

        window.location.replace("login.html");

      } catch (error) {
        console.error("Logout error:", error);
        alert("Không thể đăng xuất. Vui lòng thử lại.");
      }
    });

    return true;
  }

  // Hiển thị thông báo sau khi đăng nhập thành công.
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
      message.textContent =
        `Đăng nhập Google thành công! Xin chào ${user.name || "bạn"}.`;

      main.prepend(message);
    }

    // Xóa tham số auth=success khỏi địa chỉ trang.
    params.delete("auth");

    const query = params.toString();
    const cleanUrl =
      window.location.pathname +
      (query ? "?" + query : "") +
      window.location.hash;

    window.history.replaceState({}, "", cleanUrl);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const params = new URLSearchParams(window.location.search);

    try {
      const user = await getOAuthUser();

      if (!user) return;

      // Chỉ lưu thông tin phục vụ hiển thị.
      // Quyền đăng nhập vẫn do Backend xác minh.
      sessionStorage.setItem(
        "danang_oauth_user",
        JSON.stringify(user)
      );

      if (!updateNavbar(user)) {
        // Đợi common.js dựng xong thanh menu nếu cần.
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
      sessionStorage.removeItem("danang_oauth_user");

      if (params.get("auth") === "success") {
        console.error("OAuth session error:", error);

        const main = document.querySelector("main");

        if (main) {
          const message = document.createElement("div");
          message.className = "alert alert-warning mt-3";
          message.textContent =
            "Google đã chuyển về website nhưng phiên đăng nhập " +
            "chưa được xác minh. Hãy kiểm tra kết nối Backend.";

          main.prepend(message);
        }
      }
    }
  });
})();
