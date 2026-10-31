
document.addEventListener('DOMContentLoaded', async () => {
  const host = document.querySelector('#place-detail');
  const status = document.querySelector('#detail-status');

  const id = new URLSearchParams(location.search).get('id');

  const escapeHTML = value =>
    String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[char]);

  if (!id) {
    status.textContent = 'Không tìm thấy mã địa điểm.';
    return;
  }

  try {
    const place = await API.place(id);

    if (!place) {
      throw new Error('Địa điểm không tồn tại trong dữ liệu.');
    }

    const hasCoordinates =
      place.latitude != null &&
      place.longitude != null &&
      Number.isFinite(Number(place.latitude)) &&
      Number.isFinite(Number(place.longitude));

    const lat = hasCoordinates ? Number(place.latitude) : null;
    const lng = hasCoordinates ? Number(place.longitude) : null;

    const name = escapeHTML(place.name);
    const image = typeof getPlaceImage === 'function'
      ? getPlaceImage(place)
      : (place.image || '');

    const destination = hasCoordinates
      ? `${lat},${lng}`
      : `${place.name}, Đà Nẵng, Việt Nam`;

    const googleMaps =
      `https://www.google.com/maps/dir/?api=1&destination=${
        encodeURIComponent(destination)
      }`;

    const mapUrl = hasCoordinates
      ? `map.html?place=${encodeURIComponent(place.id)}`
      : `https://www.openstreetmap.org/search?query=${
          encodeURIComponent(destination)
        }`;

    const activities = Array.isArray(place.activities)
      && place.activities.length
      ? place.activities.map(activity =>
          `<span class="badge text-bg-light border me-1 mb-1">${
            escapeHTML(activity)
          }</span>`
        ).join('')
      : 'Chưa có dữ liệu xác minh';

    host.innerHTML = `
      <div class="detail-grid">

        <div>
          ${
            image
              ? `<img id="place-photo"
                   class="detail-photo mb-3"
                   src="${escapeHTML(image)}"
                   alt="${name}">
                 <div id="place-photo-fallback"
                      class="detail-photo-fallback mb-3"
                      role="img"
                      aria-label="Ảnh minh họa địa điểm"
                      hidden>📍</div>`
              : `<div class="detail-panel">📍 ${name}</div>`
          }

          <div class="d-flex gap-2 flex-wrap mb-3">
            <a class="btn btn-primary"
               href="${mapUrl}"
               ${hasCoordinates
                 ? ''
                 : 'target="_blank" rel="noopener noreferrer"'}>
              Xem trên bản đồ
            </a>

            <a class="btn btn-outline-primary"
               href="${googleMaps}"
               target="_blank"
               rel="noopener noreferrer">
              Chỉ đường ↗
            </a>
          </div>

          <div class="detail-panel">
            <div class="detail-label">Mô tả địa điểm</div>
            <p>${escapeHTML(
              place.description || 'Chưa có mô tả chi tiết.'
            )}</p>

            <div class="detail-label">Hoạt động phù hợp</div>
            <div>${activities}</div>

            ${
              place.sourceUrl
                ? `<p class="mt-3 mb-0">
                     <a href="${escapeHTML(place.sourceUrl)}"
                        target="_blank"
                        rel="noopener noreferrer">
                       Tham khảo nguồn thông tin ↗
                     </a>
                   </p>`
                : ''
            }
          </div>
        </div>

        <div class="detail-panel">
          <span class="tag">${
            escapeHTML(place.category || 'Địa điểm')
          }</span>

          <h1 class="mt-2">${name}</h1>

          <p>📍 ${escapeHTML(
            place.district || place.area || 'Đà Nẵng'
          )}</p>

          <div class="detail-label">Đánh giá</div>
          <p>${
            place.rating == null
              ? 'Chưa có đánh giá xác minh'
              : `⭐ ${escapeHTML(place.rating)} / 5`
          }</p>

          <div class="detail-label">Tọa độ</div>
          <p>${
            hasCoordinates
              ? `${lat.toFixed(5)}, ${lng.toFixed(5)}`
              : 'Chưa xác minh tọa độ'
          }</p>

          <div class="detail-label">Khoảng cách tham khảo</div>
          <p>${escapeHTML(
            place.distanceNote || 'Chưa có dữ liệu xác minh'
          )}</p>

          <div class="detail-label">Địa chỉ đầy đủ</div>
          <p>${escapeHTML(place.address || "Chưa có thông tin địa chỉ.")}</p>

          <div class="detail-label">Giờ mở cửa</div>
          <p>${escapeHTML(place.opening_hours || "Chưa có thông tin giờ mở cửa.")}</p>


        <div class="detail-label">Giá vé</div>

    <p>
          ${escapeHTML(
          place.ticket_info || "Chưa cập nhật thông tin giá vé."
  )}
    </p>

          ${place.ticket_source_url &&
          place.ticket_source_url.startsWith("https://")
          ? `
       <a href="${escapeHTML(place.ticket_source_url)}"
          target="_blank"
          rel="noopener noreferrer"
          class="small">
         Xem nguồn tham khảo giá vé ↗
        </a>
  `
  : ""
}

        </div>
      </div>

      <div class="detail-panel mt-4">
        <h2 class="h4">Vị trí trên bản đồ</h2>
        <div id="detail-map"></div>
        <p class="small text-secondary mt-2">
          Bản đồ cần kết nối Internet. Địa điểm chưa có tọa độ
          xác minh sẽ không được tự gán ghim.
        </p>
      </div>
    `;

    const photo = document.querySelector('#place-photo');
    if (photo) {
      photo.addEventListener('error', () => {
        photo.style.display = 'none';
        const fallback = document.querySelector('#place-photo-fallback');
        if (fallback) fallback.hidden = false;
      });
    }

    host.hidden = false;
    status.remove();

    const mapElement = document.querySelector('#detail-map');

    if (!window.L) {
      mapElement.innerHTML =
        '<p class="p-3">Không tải được Leaflet. ' +
        'Bạn vẫn có thể mở bản đồ bằng nút phía trên.</p>';
      return;
    }

    const center = hasCoordinates
      ? [lat, lng]
      : [16.0678, 108.2208];

    const map = L.map(mapElement).setView(
      center,
      hasCoordinates ? 15 : 12
    );

    L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
      }
    ).addTo(map);

    if (hasCoordinates) {
      L.marker([lat, lng])
        .addTo(map)
        .bindPopup(name)
        .openPopup();
    }

    setTimeout(() => map.invalidateSize(), 200);

  } catch (error) {
    status.className = 'alert alert-danger';
    status.textContent =
      error.message || 'Không tải được thông tin địa điểm.';
  }
});
