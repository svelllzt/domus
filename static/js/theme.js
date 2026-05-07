const THEME_KEY = "pets-theme";

function getSystemDark() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyTheme(theme) {
  const darkCss = document.getElementById("theme-dark");
  const root = document.documentElement;
  const body = document.body;
  const systemDark = getSystemDark();

  root.classList.remove("dark-theme");
  body.classList.remove("dark-theme");
  if (darkCss) darkCss.disabled = true;

  const effectiveDark = theme === "dark" || (theme === "system" && systemDark);
  if (effectiveDark) {
    root.classList.add("dark-theme");
    body.classList.add("dark-theme");
    if (darkCss) darkCss.disabled = false;
  }

  body.dataset.theme = theme;

  document.querySelectorAll(".theme-btn").forEach((btn) => {
    const t = btn.dataset.theme;
    btn.classList.toggle("is-active", t === theme);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const saved = localStorage.getItem(THEME_KEY) || "light";
  applyTheme(saved);

  document.querySelectorAll(".theme-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const selected = button.dataset.theme;
      localStorage.setItem(THEME_KEY, selected);
      applyTheme(selected);
    });
  });

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    const current = localStorage.getItem(THEME_KEY) || "light";
    if (current === "system") {
      applyTheme("system");
    }
  });
});
