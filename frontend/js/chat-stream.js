/* chat-stream.js v2 - nối widget chat với POST /api/ai-guide/chat-stream (SSE).
 *
 * Hiển thị:
 *  - các bước xử lý THẬT do backend báo ("Đang truy cập cơ sở dữ liệu...", "Đang truy cập dữ liệu thời tiết...")
 *  - chữ hiện dần (stream thật từ Gemini nếu có key; nếu không, câu trả lời từ dữ liệu địa phương
 *    được hiện dần phía trình duyệt - đây là hiệu ứng, không phải stream thật)
 *  - gợi ý bấm/tick chọn: 1 lựa chọn -> gửi ngay; nhiều lựa chọn -> tick rồi bấm "Gửi lựa chọn"
 *  - nút bản đồ Google Maps, nút "Dùng vị trí của tôi", nút Dừng, nút Thử lại
 *
 * Dùng (đặt sau chat-widget.js):
 *   DGChat.init({ messages: "#chat-messages", input: "#chat-input", send: "#chat-send", chips: "#chat-chips" });
 * (đổi selector cho đúng HTML của widget; xem hướng dẫn)
 */
(function () {
  const SID_KEY = "dg_session_id";
  const state = { pos: null, controller: null, busy: false, cfg: null };

  function defaultApiBase() {
    if (window.API_BASE_URL) return String(window.API_BASE_URL).replace(/\/$/, "");
    if (window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) return String(window.APP_CONFIG.API_BASE_URL).replace(/\/$/, "");
    const h = location.hostname;
    // chạy local (frontend :5500) -> backend :8000; chạy thật (frontend do backend phục vụ ở /app) -> cùng origin
    return h === "localhost" || h === "127.0.0.1" ? "http://127.0.0.1:8000" : "";
  }

  const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  function fmt(raw) {
    return esc(raw)
      .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
      .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
  }
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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
    box.appendChild(wrap);
    let active = null;
    return {
      add(text) {
        if (active) { active.classList.remove("active"); active.classList.add("done"); }
        active = el("div", "dg-step active");
        active.textContent = text;
        wrap.appendChild(active);
        toBottom(box);
      },
      finish() {
        if (active) { active.classList.remove("active"); active.classList.add("done"); }
        const n = wrap.children.length;
        if (!n) { wrap.remove(); return; }
        const d = el("details", "dg-steps-done");
        d.appendChild(el("summary", "", "Đã thực hiện " + n + " bước"));
        while (wrap.firstChild) d.appendChild(wrap.firstChild);
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

  // ---------- hiện chữ dần cho câu trả lời có sẵn ----------
  async function reveal(node, text, signal) {
    const step = Math.max(2, Math.ceil(text.length / 140));
    for (let i = 0; i < text.length; i += step) {
      if (signal.aborted) break;
      node.innerHTML = fmt(text.slice(0, i + step)) + '<span class="dg-cursor"></span>';
      toBottom(node.parentElement);
      await sleep(14);
    }
    node.innerHTML = fmt(text);
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

    const body = { message: text, session_id: sessionStorage.getItem(SID_KEY) || undefined };
    if (state.pos) Object.assign(body, state.pos);

    setBusy(true);
    const steps = makeSteps(box);
    steps.add("Đang phân tích yêu cầu của bạn...");
    let bot = null, raw = "", gotResult = false, failed = false;
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
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf("\n\n")) >= 0) {
          const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
          if (!chunk.startsWith("data: ")) continue;
          const ev = JSON.parse(chunk.slice(6));
          if (ev.type === "session") sessionStorage.setItem(SID_KEY, ev.session_id);
          else if (ev.type === "step") steps.add(ev.text);
          else if (ev.type === "token") {
            if (!bot) { steps.finish(); bot = addMsg(box, "bot", ""); }
            raw += ev.text;
            bot.innerHTML = fmt(raw) + '<span class="dg-cursor"></span>';
            toBottom(box);
          } else if (ev.type === "result") {
            gotResult = true;
            steps.finish();
            if (ev.text) {
              bot = bot || addMsg(box, "bot", "");
              raw = ev.text;
              if (c.revealLocal) await reveal(bot, raw, signal); else bot.innerHTML = fmt(raw);
            } else if (bot) bot.innerHTML = fmt(raw);
            renderSuggestions(box, ev);
          } else if (ev.type === "error") {
            failed = true;
            if (bot) bot.innerHTML = fmt(raw);
            showError(box, text, showText, ev.text);
          }
        }
      }
    } catch (e) {
      if (e.name === "AbortError") {
        if (bot) bot.innerHTML = fmt(raw) + " <i>(đã dừng)</i>";
      } else {
        failed = true;
        showError(box, text, showText, "Mình gặp sự cố kết nối. ");
      }
    } finally {
      if (!gotResult) steps.finish();
      if (bot && !failed) bot.innerHTML = fmt(raw);
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
      endpoint: "/api/ai-guide/chat-stream", apiBase: defaultApiBase(), revealLocal: true,
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
