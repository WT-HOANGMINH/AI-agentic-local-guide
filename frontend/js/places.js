document.addEventListener('DOMContentLoaded', async () => {
  const host = $('#places-grid');
  if (!host) return;

  const form = $('#search-form');
  const q = $('#query');
  const category = $('#category');
  const loadMore = $('#load-more');
  let currentPlaces = [];
  let loadedCount = 0;

  function renderNextPage(saved) {
    const nextPlaces = currentPlaces.slice(loadedCount, loadedCount + 100);
    host.insertAdjacentHTML(
      'beforeend',
      nextPlaces.map(p => `<div class="col-md-6 col-xl-4">${placeCard(p, saved.includes(p.id))}</div>`).join('')
    );
    loadedCount += nextPlaces.length;
    loadMore.hidden = loadedCount >= currentPlaces.length;
  }

  async function load() {
    host.innerHTML = '<div class="col-12 muted">Đang tải địa điểm…</div>';
    loadMore.hidden = true;
    try {
      const places = await API.places({
        q: q.value.trim(),
        category: category.value,
        allPages: true
      });
      places.sort((a, b) => Number(Boolean(getPlaceImage(b))) - Number(Boolean(getPlaceImage(a))));

      const saved = API.isLogged() ? await API.favorites() : [];
      currentPlaces = places;
      loadedCount = 0;
      host.innerHTML = '';
      if (places.length) {
        renderNextPage(saved);
      } else {
        host.innerHTML = '<div class="col-12 empty">Không tìm thấy địa điểm phù hợp.</div>';
      }
      $('#count').textContent = places.length + ' địa điểm';
      loadMore.onclick = () => renderNextPage(saved);
    } catch (e) {
      host.innerHTML = '';
      flash(e.message);
    }
  }

  form.addEventListener('submit', e => {
    e.preventDefault();
    load();
  });
  category.addEventListener('change', load);
  wirePlaceActions(host);
  await load();
});
