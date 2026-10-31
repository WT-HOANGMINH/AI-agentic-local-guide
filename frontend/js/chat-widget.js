
/* DANANG GUIDE - FLOATING AI CHAT
   Chat truc tiep voi FastAPI, khong dung iframe.
*/

(() => {
  // Khong hien 2 khung chat tren trang chat cu
  if (location.pathname.endsWith("/chat.html")) return;
  if (document.getElementById("dgfw-root")) return;

  // Tu nap CSS cua widget
  const css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = "css/chat-widget.css";
  document.head.appendChild(css);

  const root = document.createElement("div");
  root.id = "dgfw-root";

  root.innerHTML = `
    <div class="dgfw-greeting" id="dgfw-greeting">
      <span>Xin chào! 👋 Cần gợi ý du lịch Đà Nẵng?</span>
      <button type="button" id="dgfw-dismiss"
              aria-label="Ẩn lời chào">×</button>
    </div>

    <button type="button"
            class="dgfw-launcher"
            id="dgfw-launcher"
            aria-label="Mở trợ lý AI"
            aria-expanded="false"
            aria-controls="dgfw-panel">

    <img
        src="images/chatbot-ai.jpg"
        alt=""
        class="dgfw-bot-image"
        aria-hidden="true"
    />

      <span class="dgfw-ai-tag" aria-hidden="true">AI</span>
    </button>

    <section class="dgfw-panel"
             id="dgfw-panel"
             aria-label="Trợ lý du lịch DaNang Guide"
             hidden>

      <header class="dgfw-header">
        <div class="dgfw-avatar" aria-hidden="true">✦</div>

        <div class="dgfw-heading">
          <strong>DaNang Guide AI</strong>
          <small>
            <span class="dgfw-status-dot"></span>
            Trợ lý du lịch của bạn
          </small>
        </div>

        <button type="button"
                id="dgfw-close"
                class="dgfw-close"
                aria-label="Đóng trò chuyện">×</button>
      </header>

      <div class="dgfw-messages"
           id="dgfw-messages"
           role="log"
           aria-label="Nội dung trò chuyện"
           aria-live="polite">
      </div>

      <div class="dgfw-suggestions" id="dgfw-suggestions">
        <button type="button"
                data-dgfw-prompt="Gợi ý 5 địa điểm nổi tiếng ở Đà Nẵng">
          📍 Địa điểm nổi tiếng
        </button>

        <button type="button"
                data-dgfw-prompt="Đà Nẵng có những món ăn đặc sản nào?">
          🍜 Ăn gì ở Đà Nẵng?
        </button>

        <button type="button"
                data-dgfw-prompt="Lên lịch trình du lịch Đà Nẵng 2 ngày 1 đêm">
          🗺️ Lên lịch trình
        </button>
      </div>

      <form class="dgfw-form" id="dgfw-form">
        <input id="dgfw-input"
               type="text"
               placeholder="Hỏi AI về Đà Nẵng..."
               aria-label="Nhập câu hỏi cho AI"
               maxlength="2000"
               autocomplete="off"
               required>

        <button id="dgfw-send"
                type="submit"
                aria-label="Gửi câu hỏi">
          ➤
        </button>
      </form>

      <div class="dgfw-note">
        ✨ Khám phá Đà Nẵng cùng trợ lý AI
      </div>
    </section>
  `;

  document.body.appendChild(root);

  const launcher = root.querySelector("#dgfw-launcher");
  const panel = root.querySelector("#dgfw-panel");
  const closeButton = root.querySelector("#dgfw-close");
  const greeting = root.querySelector("#dgfw-greeting");

  // Ghi nho neu nguoi dung da tat loi chao
  let greetingDismissed = false;

  // Dat bong bong loi chao ngay canh robot
  function positionGreeting() {
    if (greetingDismissed || !panel.hidden) {
      greeting.hidden = true;
      return;
    }

    greeting.hidden = false;

    const robot = launcher.getBoundingClientRect();
    const bubbleWidth = greeting.offsetWidth;
    const bubbleHeight = greeting.offsetHeight;

    const gap = 12;
    const margin = 8;

    // Uu tien hien ben phai robot
    let left = robot.right + gap;

    // Neu khong du cho thi hien ben trai
    if (left + bubbleWidth > window.innerWidth - margin) {
      left = robot.left - bubbleWidth - gap;
    }

    // Giu bong bong trong khung man hinh
    left = Math.max(
      margin,
      Math.min(left, window.innerWidth - bubbleWidth - margin)
    );

    let top = robot.top + (robot.height - bubbleHeight) / 2;

    top = Math.max(
      margin,
      Math.min(top, window.innerHeight - bubbleHeight - margin)
    );

    greeting.style.right = "auto";
    greeting.style.bottom = "auto";
    greeting.style.left = left + "px";
    greeting.style.top = top + "px";
  }

  const dismiss = root.querySelector("#dgfw-dismiss");
  const messages = root.querySelector("#dgfw-messages");
  const form = root.querySelector("#dgfw-form");
  const input = root.querySelector("#dgfw-input");
  const sendButton = root.querySelector("#dgfw-send");

  let sending = false;

  function addMessage(type, content) {
    const bubble = document.createElement("div");

    bubble.className =
      "dgfw-message " +
      (type === "user" ? "dgfw-user" : "dgfw-assistant");

    // TextContent de tranh chen HTML khong an toan
    bubble.textContent = String(content || "");

    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;

    return bubble;
  }

  addMessage(
    "assistant",
    "Xin chào! 👋 Mình là trợ lý AI của DaNang Guide. " +
    "Bạn muốn khám phá địa điểm, thưởng thức ẩm thực " +
    "hay lên lịch trình du lịch Đà Nẵng?"
  );

  function openChat() {
    panel.hidden = false;
    greeting.hidden = true;

    launcher.setAttribute("aria-expanded", "true");
    launcher.setAttribute("aria-label", "Đóng trợ lý AI");

    input.focus();
    messages.scrollTop = messages.scrollHeight;
  }

  function closeChat() {
    panel.hidden = true;

    launcher.setAttribute("aria-expanded", "false");
    launcher.setAttribute("aria-label", "Mở trợ lý AI");

    launcher.focus();
  }


// ===== DRAG AND DROP CHATBOT AI =====

let dragStart = null;
let isDragging = false;

// Giu robot ben trong man hinh
function limit(value, min, max) {
  return Math.max(min, Math.min(value, max));
}

// Dat khung chat gan vi tri robot
function positionChatPanel() {
  if (panel.hidden) return;

  const robot = launcher.getBoundingClientRect();
  const panelWidth = panel.offsetWidth;
  const panelHeight = panel.offsetHeight;

  const margin = 8;
  const gap = 12;

  // Uu tien hien khung chat phia tren robot
  let left = robot.right - panelWidth;
  let top = robot.top - panelHeight - gap;

  // Neu khong du cho phia tren thi hien phia duoi
  if (top < margin) {
    if (robot.bottom + gap + panelHeight <= window.innerHeight) {
      top = robot.bottom + gap;
    } else {
      top = robot.top - panelHeight / 2;
    }
  }

  // Khong cho khung chat vuot ra ngoai man hinh
  left = limit(
    left,
    margin,
    Math.max(margin, window.innerWidth - panelWidth - margin)
  );

  top = limit(
    top,
    margin,
    Math.max(margin, window.innerHeight - panelHeight - margin)
  );

  panel.style.right = "auto";
  panel.style.bottom = "auto";
  panel.style.left = left + "px";
  panel.style.top = top + "px";
}

// Bat dau giu chuot vao robot
launcher.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;

  const rect = launcher.getBoundingClientRect();

  dragStart = {
    pointerId: event.pointerId,
    mouseX: event.clientX,
    mouseY: event.clientY,
    left: rect.left,
    top: rect.top,
    width: rect.width,
    height: rect.height
  };

  isDragging = false;

  launcher.setPointerCapture(event.pointerId);
});

// Di chuyen robot
launcher.addEventListener("pointermove", (event) => {
  if (!dragStart) return;
  if (event.pointerId !== dragStart.pointerId) return;

  const dx = event.clientX - dragStart.mouseX;
  const dy = event.clientY - dragStart.mouseY;

  // Phan biet nhan chuot voi keo tha
  if (!isDragging && Math.hypot(dx, dy) < 7) {
    return;
  }

isDragging = true;
launcher.classList.add("dgfw-dragging");
// An loi chao ngay khi bat dau keo
greeting.hidden = true;


  const newLeft = limit(
    dragStart.left + dx,
    8,
    Math.max(8, window.innerWidth - dragStart.width - 8)
  );

  const newTop = limit(
    dragStart.top + dy,
    8,
    Math.max(8, window.innerHeight - dragStart.height - 8)
  );

  launcher.style.right = "auto";
  launcher.style.bottom = "auto";
  launcher.style.left = newLeft + "px";
  launcher.style.top = newTop + "px";

  positionChatPanel();
});

// Tha chuot hoac cham ket thuc
launcher.addEventListener("pointerup", (event) => {
  if (!dragStart) return;
  if (event.pointerId !== dragStart.pointerId) return;

  const wasDragging = isDragging;

  dragStart = null;
  isDragging = false;

  launcher.classList.remove("dgfw-dragging");

  if (launcher.hasPointerCapture(event.pointerId)) {
    launcher.releasePointerCapture(event.pointerId);
  }

  // Neu khong keo thi xem nhu mot lan click

if (wasDragging) {
  // Tha robot: loi chao xuat hien o vi tri moi
  positionGreeting();
} else {
  // Nhan robot: mo hoac dong Chat AI
  if (panel.hidden) {
    openChat();
    positionChatPanel();
  } else {
    closeChat();
    positionGreeting();
  }
}
});

// Xu ly khi thao tac bi huy
launcher.addEventListener("pointercancel", () => {
  dragStart = null;
  isDragging = false;

  launcher.classList.remove("dgfw-dragging");
});

// Cap nhat khung chat khi thay doi kich thuoc cua so
window.addEventListener("resize", () => {
  const rect = launcher.getBoundingClientRect();

  if (launcher.style.left) {
    launcher.style.left = limit(
      rect.left,
      8,
      Math.max(8, window.innerWidth - rect.width - 8)
    ) + "px";

    launcher.style.top = limit(
      rect.top,
      8,
      Math.max(8, window.innerHeight - rect.height - 8)
    ) + "px";
  }

  positionChatPanel();
});

  closeButton.addEventListener("click", closeChat);

dismiss.addEventListener("click", () => {
  greetingDismissed = true;
  greeting.hidden = true;
});

  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !panel.hidden) {
      closeChat();
    }
  });

  async function ask(question) {
    const text = String(question || "").trim();

    if (!text || sending) return;

    sending = true;
    input.value = "";
    input.disabled = true;
    sendButton.disabled = true;

    addMessage("user", text);

    const typing = addMessage(
      "assistant",
      ""
    );
    const progress = document.createElement("div");
    progress.className = "dgfw-progress";
    progress.textContent = "Đang tìm câu trả lời cho bạn... ✨";
    const answer = document.createElement("span");
    const responseSuggestions = document.createElement("div");
    responseSuggestions.className = "dgfw-response-suggestions";
    typing.append(progress, answer, responseSuggestions);

    try {
      if (typeof API === "undefined" ||
          typeof API.chatStream !== "function") {
        throw new Error("Chưa tải được API Chat.");
      }

      await API.chatStream(text, {
        onStep: step => {
          progress.textContent = step;
          messages.scrollTop = messages.scrollHeight;
        },
        onToken: token => {
          progress.textContent = "";
          answer.textContent += token;
          messages.scrollTop = messages.scrollHeight;
        },
        onResult: result => {
          progress.textContent = "";
          if (result.text && !answer.textContent) {
            answer.textContent = result.text;
          }
          if (result.notice) {
            const notice = document.createElement("div");
            notice.className = "dgfw-notice";
            notice.textContent = result.notice;
            typing.insertBefore(notice, responseSuggestions);
          }
          (result.suggestions || []).forEach(suggestion => {
            if (!suggestion.label || !suggestion.message) return;
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = suggestion.label;
            button.addEventListener("click", () => {
              responseSuggestions.remove();
              ask(suggestion.message);
            });
            responseSuggestions.appendChild(button);
          });
        },
        onError: message => {
          progress.textContent = "";
          answer.textContent += answer.textContent ? `\n\n${message}` : message;
        }
      });

      if (!answer.textContent && !progress.textContent) {
        answer.textContent = "AI chưa có câu trả lời.";
      }
    } catch (error) {
      progress.textContent = "";
      answer.textContent =
        "Không thể kết nối Chat AI. " +
        (error.message || "Vui lòng thử lại.");
    } finally {
      sending = false;
      input.disabled = false;
      sendButton.disabled = false;

      messages.scrollTop = messages.scrollHeight;

      if (!panel.hidden) input.focus();
    }
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    ask(input.value);
  });

  // Xu ly cau hoi goi y
  root.querySelectorAll("[data-dgfw-prompt]").forEach(button => {
    button.addEventListener("click", () => {
      openChat();
      ask(button.dataset.dgfwPrompt);
    });
  });

  // Neu trang chu con nut "Tro ly du lich AI"
  // thi mo widget thay vi chuyen sang chat.html
  document.addEventListener("click", event => {
    const link = event.target.closest("a[href]");

    if (!link) return;

    const target = new URL(link.href, location.href);

    if (
      target.origin === location.origin &&
      target.pathname.endsWith("/chat.html")
    ) {
      event.preventDefault();
      openChat();
    }
  });

  // Cho phep cac script khac mo widget
  window.openDaNangChat = openChat;

// Cap nhat vi tri loi chao khi thay doi kich thuoc man hinh
window.addEventListener("resize", positionGreeting);

// Dat loi chao ngay canh robot khi trang tai xong
requestAnimationFrame(positionGreeting);

})();
