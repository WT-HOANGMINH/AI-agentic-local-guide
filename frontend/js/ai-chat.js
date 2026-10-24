/* DA NANG GUIDE - CHAT AI THAT (backend /agent/chat) */

let userPos = {};
if (navigator.geolocation) {
  navigator.geolocation.getCurrentPosition(
    p => { userPos = { latitude: p.coords.latitude, longitude: p.coords.longitude }; },
    () => {},
    { timeout: 8000 }
  );
}

window.API.chat = async function (message) {
  let response;
  try {
    response = await fetch(`${window.LOCAL_GUIDE_CONFIG.API_BASE}/agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, ...userPos })
    });
  } catch (error) {
    throw new Error('Không kết nối được Chat AI. Hãy kiểm tra FastAPI ở cổng 8000.');
  }

  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(result.error || result.detail || `Lỗi HTTP ${response.status}`);
  }
  return result.reply || 'AI chưa trả về nội dung.';
};