document.addEventListener('DOMContentLoaded', async () => {
  if (!(await protect())) return;

  const host = $('#itinerary-list');
  const count = $('#itinerary-count');
  const summaryPlaces = $('#summary-places');
  const summaryDays = $('#summary-days');
  const summaryCost = $('#summary-cost');
  if (!host) return;

  function confirmDelete(title, isWholeItinerary = false) {
    return new Promise(resolve => {
      const dialog = document.createElement('dialog');
      dialog.className = 'dg-confirm-dialog';

      dialog.innerHTML = `
        <div class="dg-confirm-content">
          <div class="dg-confirm-icon">🗑️</div>
          <h2>${isWholeItinerary
            ? 'Xóa toàn bộ lịch trình?'
            : 'Xóa địa điểm?'}</h2>

          <p>
            Bạn có chắc muốn xóa
            <strong>${esc(title)}</strong>?
          </p>

          <p class="dg-confirm-note">
            ${isWholeItinerary
              ? 'Tất cả địa điểm trong lịch trình sẽ bị xóa.'
              : 'Các địa điểm khác sẽ được giữ nguyên.'}
          </p>

          <div class="dg-confirm-actions">
            <button type="button" class="dg-confirm-cancel">
              Hủy
            </button>
            <button type="button" class="dg-confirm-delete">
              Xác nhận xóa
            </button>
          </div>
        </div>
      `;

      document.body.appendChild(dialog);

      dialog.querySelector('.dg-confirm-cancel').onclick = () => {
        dialog.close('cancel');
      };

      dialog.querySelector('.dg-confirm-delete').onclick = () => {
        dialog.close('confirm');
      };

      dialog.addEventListener('cancel', event => {
        event.preventDefault();
        dialog.close('cancel');
      });

      dialog.addEventListener('close', () => {
        const confirmed = dialog.returnValue === 'confirm';
        dialog.remove();
        resolve(confirmed);
      }, { once: true });

      dialog.showModal();
    });
  }

  // Tim ban ghi Database tuong ung voi hoat dong AI
  function findLinkedItem(activity, dayNumber, dbItems, usedIds) {
    const activityOrder = Number(activity.order);

    if (!Number.isInteger(activityOrder)) return null;

    const match = dbItems.find(dbItem => {
      if (usedIds.has(dbItem.id)) return false;

      if (Number(dbItem.day_number) !== Number(dayNumber)) {
        return false;
      }

      if (Number(dbItem.order_index) !== activityOrder) {
        return false;
      }

      if (
        activity.place_id != null &&
        dbItem.place_id != null &&
        Number(activity.place_id) !== Number(dbItem.place_id)
      ) {
        return false;
      }

      return true;
    });

    if (match) usedIds.add(match.id);

    return match || null;
  }

  function renderActivity(item, index, itineraryId, linkedItem) {
    const title = item.title || item.place?.name || item.notes || 'Hoạt động';
    const address = item.address || item.place?.address || '';

    const time = item.start_time && item.end_time
      ? `${item.start_time} – ${item.end_time}`
      : item.time_slot || item.start_time || '';

    const cost = item.estimated_cost_vnd ?? item.estimated_cost;

    const details = [
      time,
      address,
      cost != null ? `${Number(cost).toLocaleString('vi-VN')} ₫` : ''
    ]
      .filter(Boolean)
      .map(value => `<span class="muted">${esc(value)}</span>`)
      .join(' · ');

    const query = encodeURIComponent(address || title);

    // Chi hien nut Xoa khi tim duoc ID ban ghi Database
    const deleteButton = linkedItem ? `
      <button
        type="button"
        class="btn btn-sm btn-outline-danger"
        data-delete-item="${esc(linkedItem.id)}"
        data-parent-itinerary="${esc(itineraryId)}"
        data-item-title="${esc(title)}"
      >
        Xóa địa điểm
      </button>
    ` : '';

    return `
      <li class="mb-3">
        <div>
          <b>${index + 1}. ${esc(title)}</b>
        </div>

        ${details ? `<div class="small">${details}</div>` : ''}

        <div class="d-flex align-items-center flex-wrap gap-2 mt-2">
          <a
            href="https://www.google.com/maps/search/?api=1&query=${query}"
            target="_blank"
            rel="noopener noreferrer"
          >
            Mở bản đồ
          </a>

          ${deleteButton}
        </div>
      </li>
    `;
  }

  function renderItinerary(itinerary) {
    const plan = itinerary.itinerary_data;
    const days = Array.isArray(plan?.days) ? plan.days : [];

    const dbItems = Array.isArray(itinerary.items)
      ? itinerary.items
      : [];

    const usedIds = new Set();

    const daySections = days.map((day, dayIndex) => {
      const activities = Array.isArray(day.items) ? day.items : [];
      const dayNumber = day.day_number ?? dayIndex + 1;

      const activityHtml = activities.map((activity, index) => {
        const linkedItem = findLinkedItem(
          activity,
          dayNumber,
          dbItems,
          usedIds
        );

        return renderActivity(
          activity,
          index,
          itinerary.id,
          linkedItem
        );
      }).join('');

      return `
        <section class="mt-3">
          <h3 class="h6">Ngày ${esc(dayNumber)}</h3>
          ${activities.length
            ? `<ol>${activityHtml}</ol>`
            : '<p class="muted">Chưa có hoạt động.</p>'}
        </section>
      `;
    });

    const legacyItems = Array.isArray(itinerary.items)
      ? [...itinerary.items].sort((a, b) =>
        (a.day_number - b.day_number) || (a.order_index - b.order_index))
      : [];

const totalDays = Math.max(
  1,
  Math.min(
    30,
    Number(itinerary.total_days || plan?.duration_days || 1)
  )
);

const manualDaySections = Array.from(
  { length: totalDays },
  (_, index) => {
    const dayNumber = index + 1;

    const dayItems = legacyItems.filter(
      item => Number(item.day_number) === dayNumber
    );

    const activityHtml = dayItems
      .map((item, itemIndex) =>
        renderActivity(
          item,
          itemIndex,
          itinerary.id,
          item
        )
      )
      .join('');

    return `
      <section class="mt-3">
        <h3 class="h6">Ngày ${esc(dayNumber)}</h3>

        ${dayItems.length
          ? `<ol>${activityHtml}</ol>`
          : '<p class="muted">Chưa có địa điểm.</p>'}
      </section>
    `;
  }
);

const content = days.length
  ? daySections.join('')
  : manualDaySections.join('');

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

        ${itinerary.description &&
          itinerary.description !== 'manual_places_v1'
          ? `<p>${esc(itinerary.description)}</p>`
        : ''}

        ${content}
      </article>
    `;
  }

  // =====================================
  // THONG KE TONG QUAN LICH TRINH
  // =====================================

  function getActivities(itinerary) {
    const plan = itinerary.itinerary_data || {};
    const days = Array.isArray(plan.days) ? plan.days : [];

    if (days.length) {
      return days.flatMap(day =>
        Array.isArray(day.items) ? day.items : []
      );
    }

    return Array.isArray(itinerary.items)
      ? itinerary.items
      : [];
  }

  function getActivityCost(item) {
    const raw = item.estimated_cost_vnd ?? item.estimated_cost;

    if (raw == null || raw === '') return 0;

    if (typeof raw === 'number') {
      return Number.isFinite(raw) ? raw : 0;
    }

    const value = Number(
      String(raw).replace(/[^\d-]/g, '')
    );

    return Number.isFinite(value) ? value : 0;
  }

  function updateSummary(itineraries) {
    let totalPlaces = 0;
    let totalDays = 0;
    let totalCost = 0;

    itineraries.forEach(itinerary => {
      const activities = getActivities(itinerary);
      const plan = itinerary.itinerary_data || {};
      const days = Array.isArray(plan.days) ? plan.days : [];

      totalPlaces += activities.length;

      const dayCount = Number(
        itinerary.total_days ||
        plan.duration_days ||
        days.length ||
        1
      );

      totalDays += Number.isFinite(dayCount) && dayCount > 0
        ? dayCount
        : 1;

      activities.forEach(item => {
        totalCost += getActivityCost(item);
      });
    });

    if (summaryPlaces) {
      summaryPlaces.textContent = `${totalPlaces} địa điểm`;
    }

    if (summaryDays) {
      summaryDays.textContent = `${totalDays} ngày`;
    }

    if (summaryCost) {
      summaryCost.textContent =
        `${totalCost.toLocaleString('vi-VN')} ₫`;
    }
  }
  async function load() {
    host.innerHTML = '<div class="muted">Đang tải lịch trình...</div>';
    try {
      const itineraries = await API.savedItineraries();
      updateSummary(itineraries);
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

    // Xu ly nut Xoa tung dia diem
    const itemButton = event.target.closest('[data-delete-item]');

    if (itemButton) {
      if (itemButton.disabled) return;

      const title = itemButton.dataset.itemTitle || 'địa điểm này';

      // Hien thi hop thoai xac nhan
      const confirmed = await confirmDelete(title, false);

      if (!confirmed) return;

      itemButton.disabled = true;

      try {
        // Goi API xoa dia diem trong Backend
        await API.deleteItineraryItem(
          itemButton.dataset.parentItinerary,
          itemButton.dataset.deleteItem
        );

        // Tai lai danh sach va thong ke
        await load();
      } catch (error) {
        itemButton.disabled = false;
        flash(error.message || 'Không thể xóa địa điểm.');
      }

      return;
    }
    const button = event.target.closest('[data-delete-itinerary]');
    if (!button || button.disabled) return;

    // Lay ten lich trinh de hien thi trong hop thoai
    const itineraryTitle =
      button.closest('[data-itinerary-id]')?.querySelector('h2')?.textContent?.trim()
      || 'lịch trình này';

    // Hien thi hop thoai xac nhan truoc khi xoa
    const confirmed = await confirmDelete(itineraryTitle, true);

    // Neu nguoi dung chon Huy, khong xoa du lieu
    if (!confirmed) return;

    button.disabled = true;

    try {
      await API.deleteSavedItinerary(
        button.dataset.deleteItinerary
      );

      await load();
    } catch (error) {
      button.disabled = false;
      flash(error.message || 'Không thể xóa lịch trình.');
    }
  });

  await load();
});
