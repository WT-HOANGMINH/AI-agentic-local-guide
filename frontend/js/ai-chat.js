
/* DA NANG GUIDE - KET NOI CHAT AI THAT */

// Ghi de rieng API.chat()
// Cac chuc nang demo khac van giu nguyen

window.API.chat = async function (message) {

  const places = (window.DEMO_PLACES || []).map(p => ({
    name: p.name,
    category: p.category,
    district: p.district,
    description: p.description,
    area: p.area || null,
    activities: p.activities || [],
    distanceNote: p.distanceNote || null
  }));

  let response;

  try {
    response = await fetch(
      `${window.LOCAL_GUIDE_CONFIG.API_BASE}/agent/chat`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: message,
          places: places
        })
      }
    );
  } catch (error) {
    throw new Error(
      'Không kết nối được Chat AI. Hãy kiểm tra FastAPI ở cổng 8000.'
    );
  }

  const result = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      result.detail || `Lỗi HTTP ${response.status}`
    );
  }

  return result.reply || 'AI chưa trả về nội dung.';
};
