/* chat-stream.js v2 - nối widget chat với POST /api/ai-guide/chat-stream (SSE).
 *
 * Hiển thị:
 *  - các bước xử lý THẬT do backend báo ("Đang truy cập cơ sở dữ liệu...", "Đang truy cập dữ liệu thời tiết...")
 *  - chữ hiện dần chỉ khi backend thực sự stream token từ Gemini
 *  - gợi ý bấm/tick chọn: 1 lựa chọn -> gửi ngay; nhiều lựa chọn -> tick rồi bấm "Gửi lựa chọn"
 *  - nút bản đồ Google Maps, nút "Dùng vị trí của tôi", nút Dừng, nút Thử lại
 *
 * Dùng (đặt sau chat-widget.js):
 *   DGChat.init({ messages: "#chat-messages", input: "#chat-input", send: "#chat-send", chips: "#chat-chips" });
 * (đổi selector cho đúng HTML của widget; xem hướng dẫn)
 */
(function () {
  const SID_KEY = "dg_session_id";
  const TOKEN_DELAY_MS = 40;
  const state = { pos: null, controller: null, busy: false, cfg: null };
  const graphemes = text => {
    if (typeof Intl.Segmenter === "function") {
      return [...new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(text)]
        .map(part => part.segment);
    }
    return Array.from(text);
  };
  async function revealText(text, onCharacter, signal) {
    const characters = graphemes(String(text || ""));
    for (let index = 0; index < characters.length; index += 1) {
      if (signal && signal.aborted) break;
      onCharacter(characters[index]);
      if (index < characters.length - 1) {
        await new Promise(resolve => setTimeout(resolve, TOKEN_DELAY_MS));
      }
    }
  }

  function getSessionId() {
    try {
      return sessionStorage.getItem(SID_KEY);
    } catch (error) {
      console.warn("Không thể đọc phiên chat trong trình duyệt.", error);
      return null;
    }
  }
  function setSessionId(value) {
    try {
      sessionStorage.setItem(SID_KEY, value);
    } catch (error) {
      console.warn("Không thể lưu phiên chat trong trình duyệt.", error);
    }
  }

  function defaultApiBase() {
    if (window.API_BASE_URL) return String(window.API_BASE_URL).replace(/\/$/, "");
    if (window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) return String(window.APP_CONFIG.API_BASE_URL).replace(/\/$/, "");
    const h = location.hostname;
    // chạy local (frontend :5500) -> backend :8000; chạy thật (frontend do backend phục vụ ở /app) -> cùng origin
    return h === "localhost" || h === "127.0.0.1" ? "http://127.0.0.1:8000" : "";
  }

  const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const frameBoundary = /\r\n\r\n|\n\n|\r\r/;
  function parseFrame(frame) {
    const data = frame.split(/\r\n|\r|\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).replace(/^ /, ""))
      .join("\n");
    if (!data) return null;
    let event;
    try {
      event = JSON.parse(data);
    } catch {
      throw new Error("Phản hồi streaming từ máy chủ không hợp lệ.");
    }
    if (!event || typeof event !== "object" || Array.isArray(event)) {
      throw new Error("Phản hồi streaming từ máy chủ không hợp lệ.");
    }
    return event;
  }
  function fmt(raw) {
    return esc(raw)
      .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
      .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
  }
  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function nearBottom(box) { return box.scrollHeight - box.scrollTop - box.clientHeight < 90; }
  function toBottom(box, force) { if (force || nearBottom(box)) box.scrollTop = box.scrollHeight; }
  function addMsg(box, who, html) {
    const c = state.cfg;
    const m = el("div", "dg-msg " + who + " " + (who === "user" ? c.userClass : c.botClass), html || "");
    box.appendChild(m);
    toBottom(box, true);
    return m;
  }
  function clearSuggest(box) { box.querySelectorAll(".dg-suggest,.dg-links").forEach((e) => e.remove()); }

  function getGeo() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) return resolve(null);
      navigator.geolocation.getCurrentPosition(
        (p) => resolve({ latitude: p.coords.latitude, longitude: p.coords.longitude }),
        () => resolve(null),
        { timeout: 8000, maximumAge: 60000 }
      );
    });
  }

  // ---------- bước xử lý ----------
  function makeSteps(box) {
    const wrap = el("div", "dg-steps");
    const status = el("div", "dg-status");
    const completed = el("div", "dg-completed-steps");
    wrap.append(status, completed);
    box.appendChild(wrap);
    let count = 0;
    let finished = false;
    return {
      status(text) {
        status.hidden = !text;
        status.textContent = text || "";
        toBottom(box);
      },
      add(text) {
        const step = el("div", "dg-step done");
        step.textContent = text;
        completed.appendChild(step);
        count += 1;
        toBottom(box);
      },
      finish() {
        if (finished) return;
        finished = true;
        status.remove();
        if (!count) { wrap.remove(); return; }
        const d = el("details", "dg-steps-done");
        d.appendChild(el("summary", "", "Đã hoàn thành " + count + " bước xử lý"));
        d.appendChild(completed);
        wrap.replaceWith(d);
      },
      remove() { wrap.remove(); },
    };
  }

  // ---------- gợi ý ----------
  function renderSuggestions(box, meta) {
    clearSuggest(box);
    const opts = meta.suggestions || [];
    if (meta.links && meta.links.length) {
      const L = el("div", "dg-links");
      meta.links.forEach((l) => {
        const a = el("a", "dg-linkbtn", "🗺️ " + esc(l.label));
        a.href = l.url; a.target = "_blank"; a.rel = "noopener noreferrer";
        L.appendChild(a);
      });
      box.appendChild(L);
    }
    if (!opts.length) return;
    const multi = meta.suggestion_mode === "multi";
    const wrap = el("div", "dg-suggest");
    const picked = new Map();
    const submit = el("button", "dg-send", "Gửi lựa chọn");
    submit.type = "button"; submit.disabled = true;

    opts.forEach((o) => {
      const b = el("button", "dg-chip", (multi && !o.exclusive ? '<span class="dg-box"></span>' : "") + esc(o.label));
      b.type = "button";
      b.onclick = () => {
        if (!multi || o.exclusive) return sendMessage(o.message, o.label);
        if (picked.has(o.id)) picked.delete(o.id); else picked.set(o.id, o.message);
        b.classList.toggle("on", picked.has(o.id));
        submit.disabled = picked.size === 0;
      };
      wrap.appendChild(b);
    });
    if (multi) {
      submit.onclick = () => {
        const items = [...picked.values()].join(", ");
        const text = (meta.multi_template || "{items}").replace("{items}", items);
        sendMessage(text, items);
      };
      wrap.appendChild(submit);
    }
    box.appendChild(wrap);
    toBottom(box, true);
  }

  function renderItineraryAction(box, itinerary) {
    if (!itinerary || !Array.isArray(itinerary.days)) return;

    const wrap = el("div", "dg-itinerary-save");
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    const text = document.createElement("span");
    const status = document.createElement("span");

    checkbox.type = "checkbox";
    text.textContent = "Lưu lịch trình này";
    status.className = "dg-itinerary-status";
    label.append(checkbox, text);
    wrap.append(label, status);

    checkbox.addEventListener("change", async () => {
      if (!checkbox.checked) return;
      checkbox.disabled = true;
      status.textContent = "Đang lưu…";

      try {
        if (!window.API || typeof window.API.saveChatItinerary !== "function") {
          throw new Error("Chức năng lưu lịch trình chưa sẵn sàng.");
        }
        const saved = await window.API.saveChatItinerary(itinerary);
        status.textContent = "Đã lưu. Mở lịch trình trong mục Lịch trình của tôi:";
        const link = document.createElement("a");
        link.className = "dg-itinerary-open";
        link.href = `itinerary.html?id=${encodeURIComponent(saved.id)}`;
        link.textContent = "Mở lịch trình đã lưu";
        wrap.appendChild(link);
      } catch (error) {
        checkbox.checked = false;
        checkbox.disabled = false;
        if (/chưa đăng nhập|đăng nhập/i.test(error.message || "")) {
          status.textContent = "Đăng nhập để lưu lịch trình; sau đó quay lại và chọn lại ô này. ";
          const loginLink = document.createElement("a");
          loginLink.className = "dg-itinerary-open";
          loginLink.href = "login.html";
          loginLink.target = "_blank";
          loginLink.rel = "noopener noreferrer";
          loginLink.textContent = "Đăng nhập";
          status.appendChild(loginLink);
        } else {
          status.textContent = error.message || "Không thể lưu lịch trình.";
        }
      }
      toBottom(box, true);
    });

    box.appendChild(wrap);
  }

  // ---------- gửi tin ----------
  async function sendMessage(text, shown) {
    if (state.busy) return;
    const c = state.cfg, box = c.box;
    text = (text || "").trim();
    if (!text) return;

    clearSuggest(box);
    let showText = shown || text;
    if (text === "__geo__") {
      const g = await getGeo();
      if (!g) {
        addMsg(box, "bot", "Mình chưa lấy được vị trí của bạn (trình duyệt chưa cho phép). Bạn chọn một điểm xuất phát bên dưới giúp mình nhé.");
        return;
      }
      state.pos = g;
      text = "Dùng vị trí hiện tại của tôi";
      showText = "📍 Dùng vị trí của tôi";
    }
    addMsg(box, "user", esc(showText));
    c.input.value = "";

    const body = { message: text, session_id: getSessionId() || undefined };
    if (state.pos) Object.assign(body, state.pos);

    setBusy(true);
    const steps = makeSteps(box);
    steps.status("Đang gửi yêu cầu…");
    let bot = null, raw = "", failed = false, gotResult = false;
    state.controller = new AbortController();
    const signal = state.controller.signal;

    try {
      const res = await fetch(c.apiBase + c.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
        signal,
      });
      if (!res.ok || !res.body) throw new Error("HTTP " + res.status);

      const reader = res.body.getReader();
      const dec = new TextDecoder("utf-8");
      let buf = "";
      async function dispatchFrame(frame) {
        const ev = parseFrame(frame);
        if (!ev) return;
        if (ev.type === "session" && ev.session_id) setSessionId(ev.session_id);
        else if (ev.type === "status") steps.status(ev.text);
        else if (ev.type === "step") steps.add(ev.text);
        else if (ev.type === "token") {
          steps.status("Đang nhận câu trả lời từ mô hình AI…");
          if (!bot) {
            bot = addMsg(box, "bot", "");
          }
          raw += ev.text;
          bot.classList.add("dg-streaming-text");
          await revealText(ev.text, character => {
            bot.textContent += character;
            toBottom(box);
          }, signal);
        } else if (ev.type === "result") {
          gotResult = true;
          if (ev.text) {
            bot = bot || addMsg(box, "bot", "");
            const finalText = String(ev.text);
            if (finalText !== raw) {
              steps.status("Đang hiển thị câu trả lời…");
              const suffix = finalText.startsWith(raw)
                ? finalText.slice(raw.length)
                : finalText;
              if (suffix === finalText && raw) bot.textContent = "";
              raw = finalText;
              bot.classList.add("dg-streaming-text");
              if (!signal.aborted) {
                await revealText(suffix, character => {
                  bot.textContent += character;
                  toBottom(box);
                }, signal);
              }
            }
            bot.classList.remove("dg-streaming-text");
            if (!signal.aborted) bot.innerHTML = fmt(raw);
            if (signal.aborted) return;
          } else if (bot) bot.innerHTML = fmt(raw);
          steps.finish();
          renderItineraryAction(box, ev.itinerary);
          renderSuggestions(box, ev);
        } else if (ev.type === "error") {
          failed = true;
          steps.status("");
          if (bot) {
            bot.classList.remove("dg-streaming-text");
            bot.innerHTML = fmt(raw);
          }
          showError(box, text, showText, ev.text);
        }
      }

      try {
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          let boundary;
          while ((boundary = frameBoundary.exec(buf)) !== null) {
            await dispatchFrame(buf.slice(0, boundary.index));
            buf = buf.slice(boundary.index + boundary[0].length);
          }
        }
        buf += dec.decode();
        if (buf.trim()) await dispatchFrame(buf);
      } finally {
        reader.releaseLock();
      }
    } catch (e) {
      if (e.name === "AbortError") {
        if (bot) {
          bot.classList.remove("dg-streaming-text");
          bot.innerHTML = fmt(raw) + " <i>(đã dừng)</i>";
        }
      } else {
        failed = true;
        steps.status("");
        showError(box, text, showText, "Mình gặp sự cố kết nối. ");
      }
    } finally {
      steps.finish();
      if (bot) bot.classList.remove("dg-streaming-text");
      if (bot && signal.aborted) bot.innerHTML = fmt(raw) + " <i>(đã dừng)</i>";
      else if (bot && !failed && gotResult) bot.innerHTML = fmt(raw);
      state.controller = null;
      setBusy(false);
    }
  }

  function showError(box, text, shown, msg) {
    const err = addMsg(box, "bot dg-error", esc(msg || "Có lỗi xảy ra. "));
    const retry = el("button", "dg-chip", "Thử lại");
    retry.type = "button";
    retry.onclick = () => { err.remove(); sendMessage(text, shown); };
    err.appendChild(retry);
  }

  function setBusy(b) {
    state.busy = b;
    const c = state.cfg;
    c.input.disabled = b;
    c.send.classList.toggle("dg-stop", b);
    c.send.setAttribute("aria-label", b ? "Dừng" : "Gửi");
    c.send.dataset.label = c.send.dataset.label || c.send.innerHTML;
    c.send.innerHTML = b ? "■" : c.send.dataset.label;
    if (!b) c.input.focus();
  }

  function stripListeners(node) {   // thay bằng bản sao để bỏ handler cũ của chat-widget.js
    const clone = node.cloneNode(true);
    node.replaceWith(clone);
    return clone;
  }

  function init(opts) {
    const q = (s) => (typeof s === "string" ? document.querySelector(s) : s);
    const cfg = Object.assign({
      endpoint: "/api/ai-guide/chat-stream", apiBase: defaultApiBase(),
      userClass: "", botClass: "", replaceExisting: true,
    }, opts);
    cfg.box = q(opts.messages); cfg.input = q(opts.input); cfg.send = q(opts.send);
    if (!cfg.box || !cfg.input || !cfg.send) { console.error("[DGChat] Không tìm thấy phần tử widget, kiểm tra lại selector"); return; }
    if (cfg.replaceExisting) { cfg.input = stripListeners(cfg.input); cfg.send = stripListeners(cfg.send); }
    state.cfg = cfg;

    const submit = () => { if (state.busy) { state.controller && state.controller.abort(); } else sendMessage(cfg.input.value); };
    cfg.send.addEventListener("click", (e) => { e.preventDefault(); submit(); });
    cfg.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!state.busy) sendMessage(cfg.input.value); }
    });

    const chipBox = q(opts.chips);
    if (chipBox) {          // nút gợi ý nhanh có sẵn ("Địa điểm nổi tiếng"...)
      chipBox.querySelectorAll("button, a, [data-q]").forEach((old) => {
        const chip = cfg.replaceExisting ? stripListeners(old) : old;
        chip.addEventListener("click", (e) => {
          e.preventDefault();
          sendMessage(chip.dataset.q || chip.dataset.message || chip.dataset.dgfwPrompt || chip.textContent.replace(/^[^\p{L}\p{N}]+/u, "").trim());
        });
      });
    }
  }

  window.DGChat = { init, send: sendMessage, stop: () => state.controller && state.controller.abort() };
})();
