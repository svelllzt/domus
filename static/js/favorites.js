async function toggleFavorite(animalId, buttonElement) {
  try {
    const response = await fetch(`/api/favorites/${animalId}/toggle`, { method: "POST" });
    if (response.status === 401) {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/auth/login?next=${next}`;
      return;
    }
    if (!response.ok) return;

    const payload = await response.json();
    buttonElement.innerHTML = payload.is_favorite
      ? '<i class="fa-solid fa-heart"></i>'
      : '<i class="fa-regular fa-heart"></i>';
    buttonElement.classList.remove("is-pulse");
    void buttonElement.offsetWidth;
    buttonElement.classList.add("is-pulse");
  } catch (_error) {
  }
}

if (!window.__favoritesBound) {
  window.__favoritesBound = true;

  document.addEventListener(
    "animationend",
    (event) => {
      if (event.target.classList?.contains("fav-btn")) {
        event.target.classList.remove("is-pulse");
      }
    },
    true,
  );

  document.addEventListener("click", (event) => {
    const button = event.target.closest(".fav-btn");
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    const animalId = button.dataset.animalId;
    if (!animalId) return;
    toggleFavorite(animalId, button);
  });
}
