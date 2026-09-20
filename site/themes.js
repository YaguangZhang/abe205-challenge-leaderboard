/* Runs before the stylesheets so the first paint uses the chosen theme.
   Theme state lives only in this document: no storage, cookies, or URL state. */
(() => {
  "use strict";

  const colors = Object.freeze({
    arcade: "#201034",
    festival: "#fff7eb",
    glass: "#edf2ff",
    minimal: "#fafbfa",
    neon: "#080b17",
    purdue: "#101110",
    retro: "#efe5ce",
    sports: "#e9eef5",
  });
  const themes = Object.keys(colors);
  const root = document.documentElement;

  function applyTheme(theme, announce = false) {
    if (!Object.prototype.hasOwnProperty.call(colors, theme)) return;
    root.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", colors[theme]);
    const selector = document.getElementById("theme-select");
    if (selector) selector.value = theme;
    const status = document.getElementById("theme-status");
    if (announce && status && selector) {
      status.textContent = `${selector.selectedOptions[0].textContent} theme selected.`;
    }
  }

  function chooseRandomTheme() {
    applyTheme(themes[Math.floor(Math.random() * themes.length)]);
  }

  chooseRandomTheme();

  document.addEventListener("DOMContentLoaded", () => {
    const selector = document.getElementById("theme-select");
    if (!selector) return;
    selector.value = root.dataset.theme;
    selector.disabled = false;
    selector.addEventListener("change", () => applyTheme(selector.value, true));
  }, { once: true });

  // Back/forward navigation can restore a live document without loading scripts.
  // That is a new visit, too. Ordinary pageshow and tab switches keep the theme.
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      chooseRandomTheme();
      const status = document.getElementById("theme-status");
      if (status) status.textContent = "";
    } else {
      // Some browsers restore form values after DOMContentLoaded on reload.
      // Keep the control synchronized with this document's fresh selection.
      applyTheme(root.dataset.theme);
    }
  });
})();
