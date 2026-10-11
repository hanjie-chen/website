// Theme switcher: Light and Dark pin a theme; Auto follows the system.
// The <head> script in base.html applies a saved choice before the first paint.
(() => {
  const root = document.documentElement;

  const saved = () => {
    try {
      const theme = localStorage.getItem("theme");
      return theme === "light" || theme === "dark" ? theme : null;
    } catch {
      return null;
    }
  };

  const save = (theme) => {
    try {
      if (theme) {
        localStorage.setItem("theme", theme);
      } else {
        localStorage.removeItem("theme");
      }
    } catch {
      // Without storage the choice lasts for this page only.
    }
  };

  const apply = (theme) => {
    if (theme) {
      root.dataset.theme = theme;
    } else {
      delete root.dataset.theme;
    }
  };

  // Mark the visitor's choice; without a pinned theme that is Auto.
  const render = () => {
    const choice = root.dataset.theme || "system";
    document.querySelectorAll("[data-theme-option]").forEach((option) => {
      option.setAttribute("aria-pressed", String(option.dataset.themeOption === choice));
    });
  };

  // Pick up a choice made elsewhere: in another tab, or after this page was
  // restored from the back/forward cache.
  const sync = () => {
    apply(saved());
    render();
  };

  document.addEventListener("click", (event) => {
    const option = event.target.closest("[data-theme-option]");
    if (!option) {
      return;
    }
    const theme = option.dataset.themeOption === "system" ? null : option.dataset.themeOption;
    apply(theme);
    save(theme);
    render();
  });

  window.addEventListener("storage", (event) => {
    if (event.key === "theme" || event.key === null) {
      sync();
    }
  });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      sync();
    }
  });

  document.querySelectorAll("[data-theme-switcher]").forEach((row) => {
    row.hidden = false;
  });
  render();
})();
