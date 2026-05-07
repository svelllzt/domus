const FILTER_LABELS = {
  species: {
    dog: "🐕 Собаки",
    cat: "🐈 Кошки",
  },
  sex: {
    male: "♂ Самец",
    female: "♀ Самка",
  },
  size: {
    small: "Маленький",
    medium: "Средний",
    large: "Крупный",
  },
  age: {
    "0-1": "📍 До 1 года",
    "1-3": "📍 1–3 года",
    "4-7": "📍 4–7 лет",
    "8+": "📍 От 8 лет",
  },
};

const state = {
  query: "",
  species: [],
  sex: [],
  size: [],
  age: [],
  city: [],
  status: "available",
};

let currentPage = 1;
let totalCount = 0;
let canFavorite = true;

function speciesRu(sp) {
  if (sp === "dog") return "Собака";
  if (sp === "cat") return "Кошка";
  return sp || "—";
}

function sizeRu(sz) {
  if (sz === "small") return "Маленький";
  if (sz === "large") return "Крупный";
  return "Средний";
}

function statusMeta(st) {
  if (st === "available") return { cls: "animal-card__status--available", label: "Доступен" };
  if (st === "processing") return { cls: "animal-card__status--processing", label: "В процессе" };
  return { cls: "animal-card__status--adopted", label: "Пристроен" };
}

function agePhrase(age) {
  if (age === null || age === undefined) return "—";
  const n = Number(age);
  if (Number.isNaN(n)) return "—";
  let word = "лет";
  if (n % 10 === 1 && n % 100 !== 11) word = "год";
  else if ([2, 3, 4].includes(n % 10) && (n % 100 < 10 || n % 100 > 20)) word = "года";
  return `${n} ${word}`;
}

function cardMarkup(animal, staggerIndex) {
  const photo = animal.main_photo || "placeholder.svg";
  const st = statusMeta(animal.status);
  const meta = `${speciesRu(animal.species)} · ${agePhrase(animal.age)} · ${sizeRu(animal.size)}`;
  const shelter = animal.shelter_name || "Приют";
  const name = String(animal.name || "").replace(/^\w/, (c) => c.toUpperCase());
  const favIcon = animal.is_favorite ? "fa-solid" : "fa-regular";
  const favoriteButton = canFavorite
    ? `
        <button type="button" class="fav-btn animal-card__fav" data-animal-id="${animal.id}" aria-label="В избранное">
          <i class="${favIcon} fa-heart"></i>
        </button>
      `
    : "";
  return `
    <article class="animal-card" style="--stagger:${staggerIndex}">
      <div class="animal-card__media">
        <a class="animal-card__media-link" href="/animals/${animal.id}" aria-label="Открыть анкету ${name}"></a>
        <span class="animal-card__status ${st.cls}">${st.label}</span>
        ${favoriteButton}
        <div class="animal-card__photo">
          <img src="/static/uploads/${photo}" alt="" loading="lazy" width="300" height="400">
        </div>
      </div>
      <div class="animal-card__body">
        <a class="animal-card__title" href="/animals/${animal.id}">${name}</a>
        <p class="animal-card__meta">${meta}</p>
        <span class="animal-card__pill">${shelter}</span>
      </div>
    </article>
  `;
}

function buildParams(page) {
  const params = new URLSearchParams();
  if (state.query.trim()) params.set("query", state.query.trim());
  if (state.species.length) params.set("species", state.species.join(","));
  if (state.sex.length) params.set("sex", state.sex.join(","));
  if (state.size.length) params.set("size", state.size.join(","));
  if (state.age.length) params.set("age", state.age.join(","));
  if (state.city.length) params.set("city", state.city.join(","));
  if (state.status) params.set("status", state.status);
  params.set("page", String(page));
  return params;
}

async function loadAnimals(append) {
  const grid = document.getElementById("animal-grid");
  const loadMore = document.getElementById("load-more");
  if (!grid || !loadMore) return;

  const params = buildParams(currentPage);
  const response = await fetch(`/api/animals/filter?${params.toString()}`);
  const payload = await response.json();
  totalCount = payload.total;

  const existing = append ? grid.querySelectorAll(".animal-card").length : 0;
  if (!append) {
    grid.innerHTML = "";
  }
  payload.animals.forEach((animal, index) => {
    grid.insertAdjacentHTML("beforeend", cardMarkup(animal, existing + index));
  });

  const shown = grid.querySelectorAll(".animal-card").length;
  loadMore.style.display = shown < totalCount ? "inline-flex" : "none";
}

function syncCheckboxesFromState() {
  document.querySelectorAll("[data-filter-key]").forEach((input) => {
    const key = input.dataset.filterKey;
    const value = input.value;
    const list = state[key];
    input.checked = Array.isArray(list) && list.includes(value);
  });
}

function renderChips() {
  const wrap = document.getElementById("filter-chips");
  if (!wrap) return;
  wrap.innerHTML = "";
  const entries = [];

  state.species.forEach((v) => entries.push({ key: "species", value: v, label: FILTER_LABELS.species[v] || v }));
  state.sex.forEach((v) => entries.push({ key: "sex", value: v, label: FILTER_LABELS.sex[v] || v }));
  state.size.forEach((v) => entries.push({ key: "size", value: v, label: FILTER_LABELS.size[v] || v }));
  state.age.forEach((v) => entries.push({ key: "age", value: v, label: FILTER_LABELS.age[v] || v }));
  state.city.forEach((v) => entries.push({ key: "city", value: v, label: `📍 ${v}` }));

  entries.forEach((item) => {
    const chip = document.createElement("span");
    chip.className = "filter-chip";
    chip.appendChild(document.createTextNode(`${item.label} `));
    const btn = document.createElement("button");
    btn.type = "button";
    btn.setAttribute("aria-label", "Снять фильтр");
    btn.dataset.chipKey = item.key;
    btn.dataset.chipValue = item.value;
    btn.textContent = "✕";
    chip.appendChild(btn);
    wrap.appendChild(chip);
  });
}

function toggleDropdown(dropdownEl, open) {
  document.querySelectorAll(".filter-dropdown.is-open").forEach((el) => {
    if (el !== dropdownEl) el.classList.remove("is-open");
  });
  if (open) dropdownEl.classList.add("is-open");
  else dropdownEl.classList.remove("is-open");
}

function closeAllDropdowns() {
  document.querySelectorAll(".filter-dropdown.is-open").forEach((el) => el.classList.remove("is-open"));
}

function setMobileOpen(open) {
  const mount = document.getElementById("search-root");
  const btn = document.getElementById("filter-mobile-open");
  const backdrop = document.getElementById("filter-mobile-backdrop");
  if (!mount || !btn || !backdrop) return;
  mount.classList.toggle("is-open", open);
  btn.setAttribute("aria-expanded", open ? "true" : "false");
  backdrop.hidden = !open;
  document.body.style.overflow = open ? "hidden" : "";
}

function applyCheckboxChange(input) {
  const key = input.dataset.filterKey;
  const value = input.value;
  if (!key || !Array.isArray(state[key])) return;
  if (input.checked) {
    if (!state[key].includes(value)) state[key].push(value);
  } else {
    state[key] = state[key].filter((v) => v !== value);
  }
}

function initCityPanel(root) {
  const panel = document.getElementById("filter-city-panel");
  if (!panel) return;
  let cities = [];
  try {
    cities = JSON.parse(root.dataset.cities || "[]");
  } catch {
    cities = [];
  }
  panel.textContent = "";
  cities.forEach((city) => {
    const label = document.createElement("label");
    label.className = "filter-check";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = city;
    input.dataset.filterKey = "city";
    const box = document.createElement("span");
    box.className = "filter-check__box";
    box.setAttribute("aria-hidden", "true");
    label.appendChild(input);
    label.appendChild(box);
    label.appendChild(document.createTextNode(` ${city}`));
    panel.appendChild(label);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("search-root");
  const grid = document.getElementById("animal-grid");
  const loadMore = document.getElementById("load-more");
  const queryInput = document.getElementById("search-query-input");

  if (!root || !grid || !loadMore) return;
  canFavorite = root.dataset.canFavorite !== "false";

  initCityPanel(root);

  root.addEventListener("change", async (event) => {
    const input = event.target.closest("[data-filter-key]");
    if (!input || !root.contains(input)) return;
    applyCheckboxChange(input);
    currentPage = 1;
    await loadAnimals(false);
    renderChips();
  });

  if (queryInput) {
    state.query = queryInput.value || "";
    let debounceTimer;
    queryInput.addEventListener("input", () => {
      state.query = queryInput.value;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(async () => {
        currentPage = 1;
        await loadAnimals(false);
        renderChips();
      }, 220);
    });
  }

  document.getElementById("filter-chips-row")?.addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-chip-key]");
    if (!btn) return;
    const key = btn.dataset.chipKey;
    const value = btn.dataset.chipValue;
    if (!key) return;
    state[key] = state[key].filter((v) => v !== value);
    syncCheckboxesFromState();
    currentPage = 1;
    await loadAnimals(false);
    renderChips();
  });

  document.getElementById("filter-reset-all")?.addEventListener("click", async () => {
    state.query = "";
    state.species = [];
    state.sex = [];
    state.size = [];
    state.age = [];
    state.city = [];
    if (queryInput) queryInput.value = "";
    syncCheckboxesFromState();
    currentPage = 1;
    await loadAnimals(false);
    renderChips();
  });

  loadMore.addEventListener("click", async () => {
    currentPage += 1;
    await loadAnimals(true);
  });

  document.querySelectorAll(".filter-dropdown").forEach((dropdown) => {
    const trigger = dropdown.querySelector(".filter-dropdown__trigger");
    trigger?.addEventListener("click", (event) => {
      event.stopPropagation();
      const isOpen = dropdown.classList.contains("is-open");
      toggleDropdown(dropdown, !isOpen);
    });
  });

  document.addEventListener("click", () => closeAllDropdowns());

  document.getElementById("filter-dropdowns")?.addEventListener("click", (event) => {
    event.stopPropagation();
  });

  const openBtn = document.getElementById("filter-mobile-open");
  const closeBtn = document.getElementById("filter-mobile-close");
  const backdrop = document.getElementById("filter-mobile-backdrop");
  const doneBtn = document.getElementById("filter-mobile-done");

  openBtn?.addEventListener("click", () => setMobileOpen(true));
  closeBtn?.addEventListener("click", () => setMobileOpen(false));
  backdrop?.addEventListener("click", () => setMobileOpen(false));
  doneBtn?.addEventListener("click", () => setMobileOpen(false));

  (async () => {
    currentPage = 1;
    await loadAnimals(false);
    renderChips();
  })();
});
