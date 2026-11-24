/* DA NANG GUIDE - KET NOI CHAT AI (tu huan luyen, khong dung API ben ngoai) */

(function () {
  window.API = window.API || {};

  const TYPE_DELAY_MS = 24;
  const CHARACTERS_PER_TICK = 3;
  const graphemes = text => {
    if (typeof Intl.Segmenter === 'function') {
      return [...new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(text)]
        .map(part => part.segment);
    }
    return Array.from(text);
  };
  const revealText = async (text, onCharacter) => {
    const characters = graphemes(String(text || ''));
    for (let index = 0; index < characters.length; index += CHARACTERS_PER_TICK) {
      onCharacter(characters.slice(index, index + CHARACTERS_PER_TICK).join(''));
      if (index + CHARACTERS_PER_TICK < characters.length) {
        await new Promise(resolve => setTimeout(resolve, TYPE_DELAY_MS));
      }
    }
  };
  window.API.revealText = revealText;
  const frameBoundary = /\r\n\r\n|\n\n|\r\r/;
  const parseFrame = frame => {
    const data = frame.split(/\r\n|\r|\n/)
      .filter(line => line.startsWith('data:'))
      .map(line => line.slice(5).replace(/^ /, ''))
      .join('\n');
    if (!data) return null;
    let event;
    try {
      event = JSON.parse(data);
    } catch {
      throw new Error('Phản hồi streaming từ máy chủ không hợp lệ.');
    }
    if (!event || typeof event !== 'object' || Array.isArray(event)) {
      throw new Error('Phản hồi streaming từ máy chủ không hợp lệ.');
    }
    return event;
  };

  let userPosition = null;
  let positionAt = 0;
  const LOCATION_CACHE_MS = 60_000;
  const nearbyRequest = /\b(?:gan\s+(?:toi|cho toi|day|vi tri hien tai|vi tri cua toi)|quanh\s+(?:day|toi)|xung quanh\s+(?:day|toi)|vi tri\s+(?:hien tai|cua toi)|near me|nearby|near here|near my location|around me|around here|my location|current location)\b/;

  function isNearbyRequest(message) {
    const normalized = String(message || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[đĐ]/g, 'd')
      .toLowerCase();
    return nearbyRequest.test(normalized);
  }

  function locationError(code, message) {
    const error = new Error(message);
    error.code = code;
    return error;
  }

  function getCurrentPosition(onStatus) {
    if (userPosition && Date.now() - positionAt < LOCATION_CACHE_MS) {
      return Promise.resolve(userPosition);
    }
    if (!navigator.geolocation) {
      return Promise.reject(locationError(
        'LOCATION_UNAVAILABLE',
        'Trình duyệt không hỗ trợ xác định vị trí. Hãy nhập tên khu vực bạn muốn tìm.'
      ));
    }

    if (onStatus) onStatus('Đang xin quyền truy cập vị trí của bạn…');
    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        position => {
          const latitude = position.coords.latitude;
          const longitude = position.coords.longitude;
          if (!Number.isFinite(latitude) || !Number.isFinite(longitude) ||
              latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
            reject(locationError(
              'LOCATION_INVALID',
              'Vị trí nhận được không hợp lệ. Hãy thử lại hoặc nhập khu vực bạn muốn tìm.'
            ));
            return;
          }
          userPosition = { latitude, longitude };
          positionAt = Date.now();
          resolve(userPosition);
        },
        error => {
          if (error.code === 1) {
            reject(locationError(
              'LOCATION_PERMISSION_DENIED',
              'Bạn chưa cấp quyền vị trí. Hãy bật quyền vị trí cho trang này hoặc nhập tên khu vực bạn muốn tìm.'
            ));
          } else if (error.code === 3) {
            reject(locationError(
              'LOCATION_TIMEOUT',
              'Chưa lấy được vị trí vì quá thời gian chờ. Hãy thử lại hoặc nhập tên khu vực bạn muốn tìm.'
            ));
          } else {
            reject(locationError(
              'LOCATION_UNAVAILABLE',
              'Thiết bị hiện không xác định được vị trí. Hãy thử lại hoặc nhập tên khu vực bạn muốn tìm.'
            ));
          }
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: LOCATION_CACHE_MS }
      );
    });
  }

  window.LOCAL_GUIDE_LOCATION = { isNearbyRequest, getCurrentPosition };

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

  function chatPayload(message, position) {
    const payload = { message, session_id: getSid() };
    if (position) Object.assign(payload, position);
    return payload;
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
    const position = isNearbyRequest(message) ? await getCurrentPosition() : null;
    const response = await post('/api/ai-guide/chat', chatPayload(message, position));
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
    const position = isNearbyRequest(message)
      ? await getCurrentPosition(text => {
        if (h.onStatus) h.onStatus({ type: 'status', text });
      })
      : null;
    const response = await post('/api/ai-guide/chat-stream', chatPayload(message, position));
    if (!response.ok || !response.body) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.error || result.detail || `Lỗi HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let resultReceived = false;

    async function dispatchFrame(frame) {
      const event = parseFrame(frame);
      if (!event) return;

      if (event.type === 'session' && event.session_id) setSid(event.session_id);
      else if (event.type === 'status' && h.onStatus) h.onStatus(event);
      else if (event.type === 'step' && h.onStep) {
        await h.onStep(event.text, { completed: event.completed === true });
      }
      else if (event.type === 'token' && h.onToken) {
        await revealText(event.text, h.onToken);
      }
      else if (event.type === 'result') {
        if (h.onResult) await h.onResult(event);
        resultReceived = true;
      } else if (event.type === 'error' && h.onError) h.onError(event.text);
      else if (event.type === 'done' && h.onDone) await h.onDone();
    }

    try {
      for (;;) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });

        let boundary;
        while ((boundary = frameBoundary.exec(buffer)) !== null) {
          await dispatchFrame(buffer.slice(0, boundary.index));
          buffer = buffer.slice(boundary.index + boundary[0].length);
        }
      }

      buffer += decoder.decode();
      if (buffer.trim()) await dispatchFrame(buffer.trim());
    } catch (error) {
      if (!resultReceived) throw error;
      console.warn('Chat stream closed after delivering its final result.', error);
    } finally {
      reader.releaseLock();
    }
  };
})();
