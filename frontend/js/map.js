
document.addEventListener('DOMContentLoaded', async () => {
  const el = document.querySelector('#map');

  if (!el) return;

  if (!window.L) {
    flash('Không thể tải Leaflet. Kiểm tra kết nối Internet.');
    return;
  }

  // Khoi tao ban do Da Nang
  const map = L.map('map').setView([16.0678, 108.2208], 12);

  L.tileLayer(
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19
    }
  ).addTo(map);

  const markers = L.layerGroup().addTo(map);
  const userLocationLayer = L.layerGroup().addTo(map);

  const sel = document.querySelector('#map-category');

  // Lay toa do, ho tro ca latitude/longitude va lat/lng
  function getCoordinates(place) {
    const rawLat = place.latitude ?? place.lat;
    const rawLng = place.longitude ?? place.lng;

    if (
      rawLat == null ||
      rawLng == null ||
      String(rawLat).trim() === '' ||
      String(rawLng).trim() === ''
    ) {
      return null;
    }

    const lat = Number(rawLat);
    const lng = Number(rawLng);

    if (
      !Number.isFinite(lat) ||
      !Number.isFinite(lng) ||
      lat < -90 ||
      lat > 90 ||
      lng < -180 ||
      lng > 180
    ) {
      return null;
    }

    return { lat, lng };
  }

  // Tao noi dung popup cho tung dia diem
  function createPopup(place, lat, lng) {
    const name = esc(place.name || 'Địa điểm du lịch');
    const category = esc(place.category || 'Địa điểm tham quan');
    const description = esc(
      place.description || 'Chưa có mô tả chi tiết.'
    );

    const detailUrl =
      'place.html?id=' + encodeURIComponent(String(place.id ?? ''));

    const googleMapsUrl =
      'https://www.google.com/maps/dir/?api=1' +
      '&destination=' + encodeURIComponent(`${lat},${lng}`);

    const osmUrl =
      'https://www.openstreetmap.org/?mlat=' + lat +
      '&mlon=' + lng +
      '#map=16/' + lat + '/' + lng;

    return `
      <div style="
        min-width:210px;
        max-width:280px;
        font-family:Arial,sans-serif;
      ">
        <h3 style="
          font-size:16px;
          font-weight:700;
          color:#176b60;
          margin:0 0 8px;
        ">
          ${name}
        </h3>

        <div style="
          font-size:12px;
          color:#71817b;
          margin-bottom:8px;
        ">
          ${category}
        </div>

        <p style="
          font-size:13px;
          line-height:1.6;
          margin:0 0 10px;
        ">
          ${description}
        </p>

        <p style="font-size:12px;margin:0 0 12px;">
          📍 ${lat.toFixed(5)}, ${lng.toFixed(5)}
        </p>

        <div style="
          display:flex;
          flex-wrap:wrap;
          gap:7px;
        ">
          <a
            href="${detailUrl}"
            style="
              display:inline-block;
              padding:8px 10px;
              background:#176b60;
              color:white;
              border-radius:6px;
              text-decoration:none;
              font-size:12px;
            "
          >
            Xem chi tiết
          </a>

          <a
            href="${googleMapsUrl}"
            target="_blank"
            rel="noopener noreferrer"
            style="
              display:inline-block;
              padding:8px 10px;
              border:1px solid #176b60;
              color:#176b60;
              border-radius:6px;
              text-decoration:none;
              font-size:12px;
            "
          >
            Chỉ đường ↗
          </a>

          <a
            href="${osmUrl}"
            target="_blank"
            rel="noopener noreferrer"
            style="
              display:inline-block;
              padding:8px 10px;
              border:1px solid #d6e2de;
              color:#176b60;
              border-radius:6px;
              text-decoration:none;
              font-size:12px;
            "
          >
            OpenStreetMap
          </a>
        </div>
      </div>
    `;
  }

  // Ve cac ghim dia diem
  async function draw() {
    try {
      const category = sel ? sel.value : '';
      const places = await API.places({ category });

      markers.clearLayers();

      places.forEach(place => {
        const coordinates = getCoordinates(place);

        // Khong tu gan toa do cho dia diem chua xac minh
        if (!coordinates) return;

        const { lat, lng } = coordinates;

        L.marker([lat, lng])
          .addTo(markers)
          .bindPopup(createPopup(place, lat, lng));
      });

      // Neu mo ban do voi ?place=ID thi zoom vao dia diem do
      const selectedId =
        new URLSearchParams(window.location.search).get('place');

      const selectedPlace = places.find(
        place => String(place.id) === selectedId
      );

      if (selectedPlace) {
        const coordinates = getCoordinates(selectedPlace);

        if (coordinates) {
          map.setView(
            [coordinates.lat, coordinates.lng],
            16
          );

          markers.eachLayer(marker => {
            const point = marker.getLatLng();

            if (
              Math.abs(point.lat - coordinates.lat) < 0.00001 &&
              Math.abs(point.lng - coordinates.lng) < 0.00001
            ) {
              marker.openPopup();
            }
          });
        } else {
          flash(
            'Địa điểm này chưa có tọa độ được xác minh.'
          );
        }
      } else if (markers.getLayers().length > 0) {
        const group = L.featureGroup(markers.getLayers());
        map.fitBounds(group.getBounds().pad(0.15));
      }

      // Cap nhat so luong dia diem co ghim
      const countElement = document.querySelector('#map-count');

      if (countElement) {
        countElement.textContent =
          markers.getLayers().length +
          '/' + places.length +
          ' địa điểm có ghim';
      }

      // Hien thi danh sach dia diem chua co toa do
      const missingPlaces = places.filter(
        place => !getCoordinates(place)
      );

      const missingList =
        document.querySelector('#unverified-places');

      if (missingList) {
        if (missingPlaces.length === 0) {
          missingList.innerHTML = '';
        } else {
          missingList.innerHTML = `
            <h2 class="h5 mt-4">
              Địa điểm đang chờ xác minh tọa độ
            </h2>

            <p class="small muted">
              Bạn có thể tìm địa điểm trên OpenStreetMap.
              Hãy xác minh vị trí trước khi di chuyển.
            </p>

            <div class="d-flex flex-wrap gap-2">
              ${missingPlaces.map(place => {
                const searchUrl =
                  'https://www.openstreetmap.org/search?query=' +
                  encodeURIComponent(
                    (place.name || '') + ', Đà Nẵng, Việt Nam'
                  );

                return `
                  <a
                    class="btn btn-sm btn-outline-secondary"
                    href="${searchUrl}"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    ${esc(place.name || 'Địa điểm')} ↗
                  </a>
                `;
              }).join('')}
            </div>
          `;
        }
      }
    } catch (error) {
      console.error('Lỗi tải bản đồ:', error);

      flash(
        error.message || 'Không thể tải danh sách địa điểm.'
      );
    }
  }

  // Loc dia diem theo danh muc
  if (sel) {
    sel.addEventListener('change', draw);
  }

  // Lay vi tri hien tai cua nguoi dung
  const locationButton = document.querySelector('#my-location');

  if (locationButton) {
    locationButton.addEventListener('click', () => {
      if (!navigator.geolocation) {
        flash('Trình duyệt không hỗ trợ định vị.');
        return;
      }

      locationButton.disabled = true;

      navigator.geolocation.getCurrentPosition(
        position => {
          locationButton.disabled = false;

          const lat = position.coords.latitude;
          const lng = position.coords.longitude;

          userLocationLayer.clearLayers();

          L.circleMarker([lat, lng], {
            radius: 9,
            color: '#087d7b',
            fillColor: '#087d7b',
            fillOpacity: 0.8
          })
            .addTo(userLocationLayer)
            .bindPopup('Vị trí hiện tại của bạn')
            .openPopup();

          map.setView([lat, lng], 15);
        },
        error => {
          locationButton.disabled = false;

          console.error('Lỗi định vị:', error);

          flash(
            'Không lấy được vị trí. Hãy cấp quyền định vị ' +
            'và dùng localhost hoặc HTTPS.'
          );
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000
        }
      );
    });
  }

  await draw();

  // Dam bao ban do hien thi dung kich thuoc
  setTimeout(() => {
    map.invalidateSize();
  }, 200);
});
