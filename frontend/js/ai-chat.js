/* DA NANG GUIDE - KET NOI CHAT AI THAT */

// Ghi de rieng API.chat(). Cac chuc nang demo khac van giu nguyen.
window.API = window.API || {};

window.API.chat = async function (message) {
  const cfg = window.LOCAL_GUIDE_CONFIG || {};

  // Backend dang ky route la /agent/chat (khong co /api) -> bo duoi /api
  const base = String(cfg.API_BASE || 'http://127.0.0.1:8000')
    .replace(/\/+$/, '')
    .replace(/\/api$/, '');

  const headers = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem(cfg.TOKEN_KEY || 'localguide_token');
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);

  let response;
  try {
    response = await fetch(`${base}/agent/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message }),
      signal: controller.signal
    });
  } catch (error) {
    throw new Error(
      error.name === 'AbortError'
        ? 'Hết thời gian chờ phản hồi từ máy chủ.'
        : 'Không kết nối được Chat AI. Hãy kiểm tra FastAPI ở cổng 8000.'
    );
  } finally {
    clearTimeout(timer);
  }

  const result = await response.json().catch(() => ({}));

  if (!response.ok) {
    // main.py tra loi theo dang {error: "..."} ; 422 co them details
    let detail = result.error || result.detail;
    if (Array.isArray(result.details) && result.details.length) {
      detail = result.details.map(d => d.message).join('; ');
    }
    throw new Error(
      typeof detail === 'string' && detail
        ? detail
        : `Lỗi HTTP ${response.status}`
    );
  }

  return result.reply || 'AI chưa trả về nội dung.';
};