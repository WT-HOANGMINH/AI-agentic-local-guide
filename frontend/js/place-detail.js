async function loadPlaceDetail() {
  const host = document.querySelector('#place-detail');
  const status = document.querySelector('#detail-status');
  const breadcrumbName = document.querySelector('#breadcrumb-place-name');

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
    status.className = 'alert alert-warning';
    status.textContent = 'Không tìm thấy mã địa điểm. Vui lòng quay lại danh sách địa điểm.';
    return;
  }

  try {
    // 1. Lấy thông tin chi tiết địa điểm
    let place = null;
    try {
      place = await API.place(id);
    } catch (err) {
      console.warn('API.place(id) error:', err);
    }

    if (!place) {
      const places = await API.places({}).catch(() => []);
      place = places.find(item => String(item.id) === String(id));
    }

    if (!place && window.DEMO_PLACES) {
      const demo = window.DEMO_PLACES.find(item => String(item.id) === String(id));
      if (demo) place = typeof mapPlace === 'function' ? mapPlace(demo) : demo;
    }

    if (!place) {
      throw new Error('Địa điểm không tồn tại hoặc đã bị ẩn.');
    }

    const isEn = window.getLang && window.getLang() === 'en';
    const locPlace = typeof getLocalizedPlace === 'function' ? getLocalizedPlace(place) : place;

    if (breadcrumbName) {
      breadcrumbName.textContent = locPlace.name;
    }
    document.title = `${locPlace.name} | DaNang Guide`;

    // 2. Tọa độ và liên kết bản đồ
    const hasCoordinates =
      place.latitude != null &&
      place.longitude != null &&
      Number.isFinite(Number(place.latitude)) &&
      Number.isFinite(Number(place.longitude));

    const lat = hasCoordinates ? Number(place.latitude) : null;
    const lng = hasCoordinates ? Number(place.longitude) : null;

    const name = escapeHTML(locPlace.name);
    const description = escapeHTML(locPlace.description || place.description || '');
    const image = typeof getPlaceImage === 'function'
      ? getPlaceImage(place)
      : (place.image || '');

    const destination = hasCoordinates
      ? `${lat},${lng}`
      : `${place.name}, Đà Nẵng, Việt Nam`;

    const googleMaps =
      `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}`;

    const mapUrl = hasCoordinates
      ? `map.html?place=${encodeURIComponent(place.id)}`
      : `https://www.openstreetmap.org/search?query=${encodeURIComponent(destination)}`;

    // 3. Trạng thái yêu thích
    let isFavorite = false;
    try {
      const favs = await API.favorites();
      isFavorite = Array.isArray(favs) && favs.some(f => String(f) === String(place.id));
    } catch {
      isFavorite = false;
    }

    // 4. Format các trường hiển thị phong phú
    const address = escapeHTML(
      place.address || (locPlace.district ? `${locPlace.district}, ${isEn ? 'Da Nang' : 'Đà Nẵng'}` : (isEn ? 'Da Nang, Vietnam' : 'Đà Nẵng, Việt Nam'))
    );

    const openingHours = escapeHTML(
      place.opening_hours || place.openingHours || (isEn ? 'Open daily (check ahead)' : 'Mở cửa hằng ngày (kiểm tra trước khi đi)')
    );

    const ticketPrice = escapeHTML(
      place.ticket_price || (
        place.price_level === 1 ? (isEn ? 'Free admission' : 'Miễn phí tham quan') :
        place.price_level === 2 ? (isEn ? 'Budget (~50k – 150k VND)' : 'Bình dân (~50.000 – 150.000 VNĐ)') :
        place.price_level === 3 ? (isEn ? 'Moderate (~200k – 600k VND)' : 'Trung cấp (~200.000 – 600.000 VNĐ)') :
        place.price_level === 4 ? (isEn ? 'Premium (~700k – 1.5M VND)' : 'Cao cấp (~700.000 – 1.500.000 VNĐ)') :
        (isEn ? 'Check with venue' : 'Vui lòng xác nhận trước khi đi')
      )
    );

    let ratingDisplay = isEn ? 'No verified reviews yet' : 'Chưa có đánh giá xác minh';
    if (place.rating != null && !isNaN(Number(place.rating))) {
      const r = Number(place.rating).toFixed(1);
      const remark = r >= 4.7
        ? (isEn ? 'Superb' : 'Xuất sắc')
        : r >= 4.5
        ? (isEn ? 'Very Good' : 'Rất tốt')
        : r >= 4.0
        ? (isEn ? 'Good' : 'Tốt')
        : (isEn ? 'Popular' : 'Được yêu thích');
      ratingDisplay = `⭐ <strong>${r}</strong> / 5.0 <span class="badge text-bg-success ms-1">${remark}</span>`;
    }

    const distance = escapeHTML(
      place.distanceNote || (locPlace.district ? `${isEn ? 'District' : 'Khu vực'} ${locPlace.district}` : (isEn ? 'Da Nang' : 'Đà Nẵng'))
    );

    let categoryDisplay = place.category || 'Địa điểm';
    if (isEn) {
      if (categoryDisplay === 'tourist_attraction' || categoryDisplay.includes('tham quan')) categoryDisplay = 'Attraction';
      else if (categoryDisplay === 'restaurant' || categoryDisplay.includes('thực') || categoryDisplay.includes('Nhà hàng')) categoryDisplay = 'Dining';
      else if (categoryDisplay === 'cafe' || categoryDisplay.includes('cà phê')) categoryDisplay = 'Cafe';
      else if (categoryDisplay === 'shopping' || categoryDisplay.includes('sắm')) categoryDisplay = 'Shopping';
    }

    const activities = Array.isArray(place.activities) && place.activities.length
      ? place.activities.map(activity =>
          `<span class="badge text-bg-light border me-1 mb-1 px-2 py-1">${escapeHTML(activity)}</span>`
        ).join('')
      : `<span class="text-secondary small">${isEn ? 'Sightseeing, exploring & leisure' : 'Tham quan, khám phá và trải nghiệm'}</span>`;

    // 5. Render toàn bộ giao diện chi tiết
    host.innerHTML = `
      <div class="detail-grid">

        <!-- CỘT TRÁI: HÌNH ẢNH, HÀNH ĐỘNG, MÔ TẢ & ĐIỂM NỔI BẬT -->
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
                      hidden>${place.emoji || '📍'}</div>`
              : `<div class="detail-photo-fallback mb-3">${place.emoji || '📍'}</div>`
          }

          <!-- NÚT HÀNH ĐỘNG -->
          <div class="d-flex gap-2 flex-wrap mb-4">
            <button id="btn-toggle-fav"
                    class="btn ${isFavorite ? 'btn-danger active' : 'btn-outline-danger'} btn-fav d-flex align-items-center gap-1">
              <span>${isFavorite ? '❤️' : '🤍'}</span>
              <span id="fav-text">${isFavorite ? (isEn ? 'Saved to favorites' : 'Đã lưu yêu thích') : (isEn ? 'Save favorite' : 'Lưu yêu thích')}</span>
            </button>

            <button id="btn-add-itinerary"
                    class="btn btn-outline-success d-flex align-items-center gap-1">
              <span>📅</span> ${isEn ? 'Add to itinerary' : 'Thêm vào lịch trình'}
            </button>

            <a class="btn btn-primary d-flex align-items-center gap-1"
               href="${mapUrl}"
               ${hasCoordinates ? '' : 'target="_blank" rel="noopener noreferrer"'}>
              <span>🗺️</span> ${isEn ? 'View on map' : 'Xem trên bản đồ'}
            </a>

            <a class="btn btn-outline-primary d-flex align-items-center gap-1"
               href="${googleMaps}"
               target="_blank"
               rel="noopener noreferrer">
              <span>↗️</span> ${isEn ? 'Directions' : 'Chỉ đường'}
            </a>
          </div>

          <!-- MÔ TẢ ĐỊA ĐIỂM -->
          <div class="detail-panel">
            <h2 class="h5 fw-bold text-dark mb-3">${isEn ? 'About this destination' : 'Giới thiệu địa điểm'}</h2>
            <p class="text-secondary mb-0" style="line-height: 1.7; font-size: 15px;">
              ${description || (isEn ? 'No detailed description available.' : 'Chưa có mô tả chi tiết.')}
            </p>

            ${
              place.highlights
                ? `<div class="info-card highlight-panel mt-3">
                     <div class="info-card-label text-teal fw-bold">${isEn ? '✨ Highlights & Experiences' : '✨ Điểm nổi bật & Trải nghiệm'}</div>
                     <p class="mb-0 text-dark" style="font-size: 14.5px; line-height: 1.6;">${escapeHTML(place.highlights)}</p>
                   </div>`
                : ''
            }

            <div class="detail-label mt-4">${isEn ? '🎯 Suggested Activities' : '🎯 Hoạt động phù hợp'}</div>
            <div class="d-flex flex-wrap gap-1 mt-1">${activities}</div>

            ${
              place.best_time
                ? `<div class="info-card mt-3">
                     <div class="info-card-label">${isEn ? '🌤️ Best Time to Visit' : '🌤️ Thời điểm lý tưởng'}</div>
                     <p class="mb-0 text-dark" style="font-size: 14px;">${escapeHTML(place.best_time)}</p>
                   </div>`
                : ''
            }

            ${
              place.tips
                ? `<div class="tips-panel">
                     <div class="fw-bold text-amber mb-1 d-flex align-items-center gap-1">
                       <span>💡</span> ${isEn ? 'Tips & Travel Notes' : 'Lưu ý & Lời khuyên khi tham quan'}
                     </div>
                     <p class="mb-0 text-dark small" style="line-height: 1.6;">${escapeHTML(place.tips)}</p>
                   </div>`
                : ''
            }

            ${
              place.sourceUrl
                ? `<div class="mt-4 pt-3 border-top">
                     <a class="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1"
                        href="${escapeHTML(place.sourceUrl)}"
                        target="_blank"
                        rel="noopener noreferrer">
                       <span>🌐</span> ${isEn ? 'Official Website / Source ↗' : 'Truy cập website / Nguồn chính thức ↗'}
                     </a>
                   </div>`
                : ''
            }
          </div>
        </div>

        <!-- CỘT PHẢI: BẢNG THÔNG TIN THIẾT YẾU -->
        <div>
          <div class="detail-panel">
            <div class="d-flex align-items-center justify-content-between mb-2">
              <span class="badge text-bg-primary px-3 py-2 fs-6">
                ${place.emoji || '📍'} ${escapeHTML(categoryDisplay)}
              </span>
              <span class="text-secondary small fw-medium">
                ${escapeHTML(locPlace.district || place.district || (isEn ? 'Da Nang' : 'Đà Nẵng'))}
              </span>
            </div>

            <h1 class="h3 fw-bold mt-2 text-dark">${name}</h1>

            <p class="text-secondary d-flex align-items-center gap-1 mt-1 mb-3">
              <span>📍</span> <span>${address}</span>
            </p>

            <hr class="my-3 text-muted">

            <h2 class="h6 fw-bold text-uppercase text-secondary mb-3" style="letter-spacing: 0.5px;">
              ${isEn ? 'TRIP INFORMATION' : 'THÔNG TIN CHUYẾN ĐI'}
            </h2>

            <!-- Đánh giá -->
            <div class="info-card">
              <div class="info-card-label">${isEn ? '⭐ Visitor Rating' : '⭐ Đánh giá trải nghiệm'}</div>
              <div class="info-card-value">${ratingDisplay}</div>
            </div>

            <!-- Giờ mở cửa -->
            <div class="info-card">
              <div class="info-card-label">${isEn ? '⏰ Opening Hours' : '⏰ Giờ hoạt động'}</div>
              <div class="info-card-value">${openingHours}</div>
            </div>

            <!-- Giá vé / Mức giá -->
            <div class="info-card">
              <div class="info-card-label">${isEn ? '🎟️ Ticket & Price' : '🎟️ Giá vé / Mức giá'}</div>
              <div class="info-card-value text-success">${ticketPrice}</div>
            </div>

            <!-- Tọa độ -->
            <div class="info-card">
              <div class="info-card-label">${isEn ? '🧭 GPS Coordinates' : '🧭 Tọa độ GPS'}</div>
              <div class="info-card-value font-monospace" style="font-size: 14px;">
                ${hasCoordinates ? `${lat.toFixed(5)}, ${lng.toFixed(5)}` : (isEn ? 'Coordinates not verified' : 'Chưa xác minh tọa độ')}
              </div>
              <div class="info-card-sub">
                ${hasCoordinates ? (isEn ? '✅ Verified on satellite navigation system' : '✅ Đã xác minh trên hệ thống bản đồ vệ tinh') : (isEn ? '⚠️ Check location before departing' : '⚠️ Kiểm tra định vị trước khi di chuyển')}
              </div>
            </div>

            <!-- Khoảng cách tham khảo -->
            <div class="info-card">
              <div class="info-card-label">${isEn ? '🚗 Distance & Transit' : '🚗 Khoảng cách & Di chuyển'}</div>
              <div class="info-card-value">${distance}</div>
              <div class="info-card-sub">
                ${isEn ? 'Convenient by taxi, private car, or scooter' : 'Thuận tiện di chuyển bằng taxi, ô tô du lịch hoặc xe máy'}
              </div>
            </div>

          </div>
        </div>

      </div>

      <!-- BẢN ĐỒ VỊ TRÍ CHI TIẾT -->
      <div class="detail-panel mt-2">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <div>
            <h2 class="h5 fw-bold mb-1">${isEn ? 'Location on Interactive Map' : 'Vị trí trên bản đồ tương tác'}</h2>
            <p class="text-secondary small mb-0">
              ${hasCoordinates ? (isEn ? 'Precise coordinate pin for navigation.' : 'Bản đồ định vị chính xác vị trí thực tế của địa điểm.') : (isEn ? 'Approximate regional area shown.' : 'Địa điểm chưa có tọa độ ghim sẽ hiển thị trung tâm khu vực.')}
            </p>
          </div>
          <a class="btn btn-sm btn-outline-primary" href="${mapUrl}" ${hasCoordinates ? '' : 'target="_blank" rel="noopener noreferrer"'}>
            ${isEn ? 'Open Fullscreen ↗' : 'Mở toàn màn hình ↗'}
          </a>
        </div>

        <div id="detail-map"></div>
      </div>

      <!-- ĐỊA ĐIỂM GỢI Ý CÙNG KHU VỰC / DANH MỤC -->
      <div id="related-section" class="detail-panel mt-2" hidden>
        <h2 class="h5 fw-bold mb-3">${isEn ? 'Explore More Nearby' : 'Khám phá thêm gần đây'}</h2>
        <div id="related-grid" class="row row-cols-1 row-cols-md-3 g-3"></div>
      </div>
    `;

    // 6. Xử lý lỗi load ảnh
    const photo = document.querySelector('#place-photo');
    if (photo) {
      photo.addEventListener('error', () => {
        photo.style.display = 'none';
        const fallback = document.querySelector('#place-photo-fallback');
        if (fallback) fallback.hidden = false;
      });
    }

    // 7. Xử lý nút Yêu thích
    const favBtn = document.querySelector('#btn-toggle-fav');
    const favText = document.querySelector('#fav-text');
    if (favBtn) {
      favBtn.addEventListener('click', async () => {
        favBtn.disabled = true;
        try {
          const updatedFavs = await API.toggleFavorite(place.id);
          isFavorite = Array.isArray(updatedFavs) && updatedFavs.some(f => String(f) === String(place.id));
          favBtn.className = `btn ${isFavorite ? 'btn-danger active' : 'btn-outline-danger'} btn-fav d-flex align-items-center gap-1`;
          favBtn.querySelector('span:first-child').textContent = isFavorite ? '❤️' : '🤍';
          if (favText) favText.textContent = isFavorite ? 'Đã lưu yêu thích' : 'Lưu yêu thích';
          if (typeof flash === 'function') {
            flash(isFavorite ? `Đã thêm "${place.name}" vào danh sách yêu thích.` : `Đã xóa "${place.name}" khỏi danh sách yêu thích.`, 'success');
          }
        } catch (err) {
          if (typeof flash === 'function') {
            flash(err.message || 'Không thể cập nhật yêu thích', 'danger');
          }
        } finally {
          favBtn.disabled = false;
        }
      });
    }

    // 8. Xử lý nút Thêm vào lịch trình
    const itineraryBtn = document.querySelector('#btn-add-itinerary');
    if (itineraryBtn) {
      itineraryBtn.addEventListener('click', async () => {
        itineraryBtn.disabled = true;
        try {
          const cur = await API.itinerary();
          const list = Array.isArray(cur) ? [...cur] : [];
          if (!list.some(item => String(item) === String(place.id))) {
            list.push(place.id);
            await API.saveItinerary(list);
            if (typeof flash === 'function') {
              flash(`Đã thêm "${place.name}" vào lịch trình tham quan!`, 'success');
            }
            itineraryBtn.innerHTML = '<span>✅</span> Đã thêm vào lịch trình';
            itineraryBtn.className = 'btn btn-success d-flex align-items-center gap-1';
          } else {
            if (typeof flash === 'function') {
              flash(`"${place.name}" đã có trong lịch trình của bạn.`, 'info');
            }
          }
        } catch (err) {
          if (typeof flash === 'function') {
            flash(err.message || 'Không thể lưu lịch trình', 'danger');
          }
        } finally {
          itineraryBtn.disabled = false;
        }
      });
    }

    // 9. Khởi tạo bản đồ Leaflet
    host.hidden = false;
    status.remove();

    const mapElement = document.querySelector('#detail-map');
    if (mapElement && window.L) {
      if (window._detailMapInstance) {
        try { window._detailMapInstance.remove(); } catch {}
        window._detailMapInstance = null;
      }
      const center = hasCoordinates ? [lat, lng] : [16.0678, 108.2208];
      const map = L.map(mapElement).setView(center, hasCoordinates ? 15 : 12);
      window._detailMapInstance = map;

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);

      if (hasCoordinates) {
        L.marker([lat, lng])
          .addTo(map)
          .bindPopup(`<strong>${name}</strong><br>${address}<br><a href="${googleMaps}" target="_blank">Chỉ đường Google Maps ↗</a>`)
          .openPopup();
      }

      setTimeout(() => map.invalidateSize(), 300);
    }

    // 10. Tải danh sách địa điểm liên quan
    try {
      const allPlaces = await API.places({}).catch(() => window.DEMO_PLACES || []);
      const related = allPlaces
        .filter(p => String(p.id) !== String(place.id) && (p.category === place.category || p.district === place.district))
        .slice(0, 3);

      if (related.length) {
        const relatedSection = document.querySelector('#related-section');
        const relatedGrid = document.querySelector('#related-grid');
        if (relatedSection && relatedGrid) {
          relatedGrid.innerHTML = related.map(p => {
            const relImg = typeof getPlaceImage === 'function' ? getPlaceImage(p) : (p.image || '');
            const relRating = p.rating ? `⭐ ${Number(p.rating).toFixed(1)}` : 'Địa điểm nổi bật';
            return `
              <div class="col">
                <a href="place.html?id=${encodeURIComponent(p.id)}" class="related-card h-100">
                  ${
                    relImg
                      ? `<img class="related-img" src="${escapeHTML(relImg)}" alt="${escapeHTML(p.name)}" onerror="this.style.display='none'">`
                      : `<div class="related-img d-grid place-items-center bg-light fs-2">${p.emoji || '📍'}</div>`
                  }
                  <div class="p-3">
                    <span class="badge text-bg-light border mb-1">${escapeHTML(p.category || 'Địa điểm')}</span>
                    <h3 class="h6 fw-bold mb-1 text-dark">${escapeHTML(p.name)}</h3>
                    <p class="text-secondary small mb-2">📍 ${escapeHTML(p.district || 'Đà Nẵng')}</p>
                    <div class="text-success small fw-semibold">${relRating}</div>
                  </div>
                </a>
              </div>
            `;
          }).join('');
          relatedSection.hidden = false;
        }
      }
    } catch (relErr) {
      console.warn('Lỗi tải địa điểm liên quan:', relErr);
    }

  } catch (error) {
    if (status) {
      status.className = 'alert alert-danger';
      status.textContent = error.message || 'Không tải được thông tin chi tiết địa điểm.';
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadPlaceDetail();
  window.addEventListener('languageChanged', () => {
    loadPlaceDetail();
  });
});
