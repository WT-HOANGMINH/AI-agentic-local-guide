/* DA NANG GUIDE - KET NOI CHAT AI (tu huan luyen, khong dung API ben ngoai) */

(function () {
  window.API = window.API || {};

  let userPosition = {};
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      position => {
        userPosition = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        };
      },
      () => {},
      { timeout: 8000 }
    );
  }

  // Cho phep API_BASE co hoac khong co hau to /api
  function base() {
    const cfg = window.LOCAL_GUIDE_CONFIG || {};
    return String(cfg.API_BASE || '').replace(/\/+$/, '').replace(/\/api$/, '');
  }

  function getSid() {
    try { return sessionStorage.getItem('dg_sid') || null; } catch (e) { return null; }
  }

  function setSid(v) {
    try { sessionStorage.setItem('dg_sid', v); } catch (e) { /* bo qua */ }
  }

  function chatPayload(message) {
    return {
      message,
      session_id: getSid(),
      ...userPosition
    };
  }

  async function post(path, body) {
    let response;
    try {
      response = await fetch(base() + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
    } catch (error) {
      throw new Error('Không kết nối được Chat AI. Hãy kiểm tra FastAPI ở cổng 8000.');
    }
    return response;
  }

  // Ban khong streaming (du phong): tra ve toan bo cau tra loi
  window.API.chat = async function (message) {
    const response = await post('/api/ai-guide/chat', chatPayload(message));
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.error || result.detail || `Lỗi HTTP ${response.status}`);
    }
    if (result.session_id) setSid(result.session_id);
    return result.reply || 'AI chưa trả về nội dung.';
  };

  // Nhận token và metadata từ backend cho giao diện chat.
  window.API.chatStream = async function (message, handlers) {
    const h = handlers || {};
    const response = await post('/api/ai-guide/chat-stream', chatPayload(message));
    if (!response.ok || !response.body) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.error || result.detail || `Lỗi HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    async function dispatchFrame(frame) {
      if (!frame.startsWith('data: ')) return;
      let event;
      try {
        event = JSON.parse(frame.slice(6));
      } catch {
        throw new Error('Phản hồi streaming từ máy chủ không hợp lệ.');
      }

      if (event.type === 'session') setSid(event.session_id);
      else if (event.type === 'step' && h.onStep) h.onStep(event.text);
      else if (event.type === 'token' && h.onToken) h.onToken(event.text);
      else if (event.type === 'result') {
        if (!event.streaming && event.text && h.onToken) {
          const characters = Array.from(event.text);
          for (let index = 0; index < characters.length; index += 5) {
            h.onToken(characters.slice(index, index + 5).join(''));
            await new Promise(resolve => setTimeout(resolve, 12));
          }
          if (h.onResult) h.onResult({ ...event, text: '' });
        } else if (h.onResult) {
          h.onResult(event);
        }
      } else if (event.type === 'error' && h.onError) h.onError(event.text);
      else if (event.type === 'done' && h.onDone) h.onDone();
    }

    try {
      for (;;) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });

        let index;
        while ((index = buffer.indexOf('\n\n')) >= 0) {
          await dispatchFrame(buffer.slice(0, index));
          buffer = buffer.slice(index + 2);
        }
      }

      buffer += decoder.decode();
      if (buffer.trim()) await dispatchFrame(buffer.trim());
    } finally {
      reader.releaseLock();
    }
  };
})();
