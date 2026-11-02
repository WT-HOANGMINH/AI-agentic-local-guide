
document.addEventListener("DOMContentLoaded", async () => {
  const host = document.querySelector("#featured");
  if (!host) return;

  try {
    try {
      await API.getProfile();
    } catch {}

    const places = await API.places({
      category: "tourist_attraction",
      limit: 100
    });
    const featuredPlaces = places
      .filter(place => getPlaceImage(place))
      .slice(0, 5);

    const favorites = API.isLogged() ? await API.favorites() : [];

    host.innerHTML = featuredPlaces.map(p => `
      <div class="col-12 col-sm-6 col-lg">
        ${placeCard(p, favorites.includes(p.id), true)}
      </div>
    `).join("") || `
      <div class="col-12 empty">
        Chưa có địa điểm nổi bật với ảnh đã xác minh.
      </div>
    `;

    if (typeof wirePlaceActions === "function") {
      wirePlaceActions(host);
    }
    await syncItineraryButtons(host);
  } catch (error) {
    flash(error.message);
  }
});
