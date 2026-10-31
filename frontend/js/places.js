document.addEventListener('DOMContentLoaded', async () => {
  const host = $('#places-grid');
  const form = $('#search-form');
  const query = $('#query');
  const category = $('#category');
  const count = $('#count');
  const loadMore = $('#load-more');

  if (!host || !form || !query || !category || !loadMore) return;

  try {
    await API.getProfile();
  } catch (error) {
    console.warn('Không thể xác thực phiên người dùng.', error);
  }

  let currentPlaces = [];
  let savedIds = [];
  let loadedCount = 0;

  async function renderNextPage() {
    const start = loadedCount;
    const page = currentPlaces.slice(start, start + 100);

    host.insertAdjacentHTML(
      'beforeend',
      page.map((place, index) => `
        <div class="col-md-6 col-xl-4">
          ${placeCard(place, savedIds.includes(place.id), start + index < 8)}
        </div>
      `).join('')
    );

    loadedCount += page.length;
    loadMore.hidden = loadedCount >= currentPlaces.length;
    await syncItineraryButtons(host);
  }

  async function load() {
    host.innerHTML = '<div class="col-12 muted">Đang tải địa điểm…</div>';
    loadMore.hidden = true;

    try {
      currentPlaces = await API.places({
        q: query.value.trim(),
        category: category.value,
        allPages: true
      });
      currentPlaces.sort(
        (a, b) => Number(Boolean(getPlaceImage(b))) - Number(Boolean(getPlaceImage(a)))
      );
      savedIds = API.isLogged() ? await API.favorites() : [];
      loadedCount = 0;
      host.replaceChildren();

      if (currentPlaces.length) {
        await renderNextPage();
      } else {
        host.innerHTML = '<div class="col-12 empty">Không tìm thấy địa điểm phù hợp.</div>';
      }

      if (count) {
        count.textContent = currentPlaces.length + ' địa điểm';
      }
    } catch (error) {
      host.replaceChildren();
      flash(error.message || 'Không thể tải danh sách địa điểm.');
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    load();
  });
  category.addEventListener('change', load);
  loadMore.addEventListener('click', async () => {
    loadMore.disabled = true;
    try {
      await renderNextPage();
    } catch (error) {
      flash(error.message || 'Không thể tải thêm địa điểm.');
    } finally {
      loadMore.disabled = false;
    }
  });

  wirePlaceActions(host);
  await load();
});
