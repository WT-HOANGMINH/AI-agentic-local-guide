document.addEventListener('DOMContentLoaded', async () => {
  if (!protect()) return;
  const host = $('#recommend-grid');
  const sel = $('#recommend-category');

  async function load() {
    const isEn = window.getLang && window.getLang() === 'en';
    host.textContent = isEn ? 'Fetching recommendations…' : 'Đang lấy đề xuất…';
    try {
      const ps = await API.recommend(sel.value);
      const f = await API.favorites();
      host.innerHTML = ps.map(p => `<div class="col-md-6 col-xl-3">${placeCard(p, f.includes(p.id))}</div>`).join('') ||
        `<div class="empty">${isEn ? 'No recommendations available.' : 'Chưa có gợi ý.'}</div>`;
    } catch (err) {
      host.textContent = '';
      flash(err.message);
    }
  }

  sel.addEventListener('change', load);
  wirePlaceActions(host);

  window.addEventListener('languageChanged', () => {
    load();
  });

  load();
});

