document.addEventListener('DOMContentLoaded', async () => {
  if (!(await protect())) return;

  const host = $('#itinerary-list');
  const count = $('#itinerary-count');
  if (!host) return;

  function renderActivity(item, index) {
    const title = item.title || item.place?.name || item.notes || 'Hoạt động';
    const address = item.address || item.place?.address || '';
    const time = item.start_time && item.end_time
      ? `${item.start_time} – ${item.end_time}`
      : item.time_slot || item.start_time || '';
    const cost = item.estimated_cost_vnd ?? item.estimated_cost;
    const details = [time, address, cost != null ? `${Number(cost).toLocaleString('vi-VN')} ₫` : '']
      .filter(Boolean)
      .map(value => `<span class="muted">${esc(value)}</span>`)
      .join(' · ');
    const query = encodeURIComponent(address || title);

    return `
      <li class="mb-3">
        <div><b>${index + 1}. ${esc(title)}</b></div>
        ${details ? `<div class="small">${details}</div>` : ''}
        <a href="https://www.google.com/maps/search/?api=1&query=${query}"
           target="_blank" rel="noopener noreferrer">Mở bản đồ</a>
      </li>
    `;
  }

  function renderItinerary(itinerary) {
    const plan = itinerary.itinerary_data;
    const days = Array.isArray(plan?.days) ? plan.days : [];
    const daySections = days.map(day => {
      const activities = Array.isArray(day.items) ? day.items : [];
      return `
        <section class="mt-3">
          <h3 class="h6">Ngày ${esc(day.day_number)}</h3>
          ${activities.length
            ? `<ol>${activities.map(renderActivity).join('')}</ol>`
            : '<p class="muted">Chưa có hoạt động.</p>'}
        </section>
      `;
    });

    const legacyItems = Array.isArray(itinerary.items)
      ? [...itinerary.items].sort((a, b) =>
        (a.day_number - b.day_number) || (a.order_index - b.order_index))
      : [];
    const content = days.length
      ? daySections.join('')
      : legacyItems.length
        ? `<ol>${legacyItems.map(renderActivity).join('')}</ol>`
        : '<p class="muted mb-0">Lịch trình chưa có hoạt động.</p>';
    const dayCount = itinerary.total_days || plan?.duration_days || days.length || 1;
    const date = itinerary.start_date || plan?.travel_date;

    return `
      <article class="card-soft p-3 mb-3" data-itinerary-id="${esc(itinerary.id)}">
        <div class="d-flex justify-content-between align-items-start gap-3">
          <div>
            <h2 class="h5 mb-1">${esc(itinerary.title || plan?.title || 'Lịch trình')}</h2>
            <div class="muted small">
              ${esc(dayCount)} ngày${date ? ` · ${esc(date)}` : ''}
            </div>
          </div>
          <button type="button" class="btn btn-sm btn-outline-danger"
                  data-delete-itinerary="${esc(itinerary.id)}">
            Xóa
          </button>
        </div>
        ${itinerary.description || plan?.description
          ? `<p class="mt-2 mb-0">${esc(itinerary.description || plan.description)}</p>`
          : ''}
        ${content}
      </article>
    `;
  }

  async function load() {
    host.innerHTML = '<div class="muted">Đang tải lịch trình...</div>';
    try {
      const itineraries = await API.savedItineraries();
      if (count) count.textContent = `${itineraries.length} lịch trình`;
      host.innerHTML = itineraries.length
        ? itineraries.map(renderItinerary).join('')
        : `<div class="empty">
             Chưa có lịch trình đã lưu. Hãy trò chuyện với AI để lên kế hoạch,
             sau đó chọn “Lưu lịch trình này”.
           </div>`;
      const requestedId = new URLSearchParams(window.location.search).get('id');
      if (requestedId) {
        const selected = [...host.querySelectorAll('[data-itinerary-id]')]
          .find(item => item.dataset.itineraryId === requestedId);
        if (selected) {
          selected.tabIndex = -1;
          selected.focus({ preventScroll: true });
          selected.scrollIntoView({ behavior: 'smooth', block: 'center' });
          selected.style.outline = '3px solid #176b60';
          selected.style.outlineOffset = '3px';
        }
      }
    } catch (error) {
      host.replaceChildren();
      flash(error.message || 'Không thể tải lịch trình.');
    }
  }

  host.addEventListener('click', async event => {
    const button = event.target.closest('[data-delete-itinerary]');
    if (!button) return;

    button.disabled = true;
    try {
      await API.deleteSavedItinerary(button.dataset.deleteItinerary);
      await load();
    } catch (error) {
      button.disabled = false;
      flash(error.message || 'Không thể xóa lịch trình.');
    }
  });

  await load();
});
