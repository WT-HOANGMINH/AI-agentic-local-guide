
document.addEventListener("DOMContentLoaded", async () => {
  const host = document.querySelector("#featured");
  if (!host) return;

  try {
    const places = await API.places({});

    host.innerHTML = places.slice(0, 5).map(p => `
      <div class="col-12 col-sm-6 col-lg">
        ${placeCard(p)}
      </div>
    `).join("");

    if (typeof wirePlaceActions === "function") {
      wirePlaceActions(host);
    }
  } catch (error) {
    flash(error.message);
  }
});
