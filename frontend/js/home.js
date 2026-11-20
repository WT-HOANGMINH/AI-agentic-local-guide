
document.addEventListener("DOMContentLoaded", async () => {
  const host = document.querySelector("#featured");
  if (!host) return;

  try {
    const places = await API.places({
      category: "tourist_attraction",
      limit: 100
    });
    const featuredPlaces = places
      .filter(place => getPlaceImage(place))
      .slice(0, 5);

    host.innerHTML = featuredPlaces.map(p => `
      <div class="col-12 col-sm-6 col-lg">
        ${placeCard(p, false, true)}
      </div>
    `).join("") || `
      <div class="col-12 empty">
        Chưa có địa điểm nổi bật với ảnh đã xác minh.
      </div>
    `;

    if (typeof wirePlaceActions === "function") {
      wirePlaceActions(host);
    }
  } catch (error) {
    flash(error.message);
  }
});
