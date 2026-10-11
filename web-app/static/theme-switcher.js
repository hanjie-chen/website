// Theme switcher: the page follows the system theme until the visitor picks one.
// The <head> script in base.html applies a saved choice before the first paint.
(() => {
  const root = document.documentElement;
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
  const systemTheme = () => (systemDark.matches ? "dark" : "light");
  const currentTheme = () => root.dataset.theme || systemTheme();

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

  // Mark the theme in effect, whether picked or inherited from the system.
  const render = () => {
    const theme = currentTheme();
    document.querySelectorAll("[data-theme-option]").forEach((option) => {
      option.setAttribute("aria-pressed", String(option.dataset.themeOption === theme));
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
    const theme = option.dataset.themeOption;
    // Picking the system's own theme goes back to following the system.
    const choice = theme === systemTheme() ? null : theme;
    apply(choice);
    save(choice);
    render();
  });

  systemDark.addEventListener("change", render);
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
