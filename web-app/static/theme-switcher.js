// Theme switcher: the page follows the system theme until the visitor picks one.
// The <head> script in base.html applies a saved choice before the first paint.
(() => {
  const root = document.documentElement;
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
  const systemTheme = () => (systemDark.matches ? "dark" : "light");
  const currentTheme = () => root.dataset.theme || systemTheme();

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

  // Mark the theme in effect, whether picked or inherited from the system.
  const render = () => {
    const theme = currentTheme();
    document.querySelectorAll("[data-theme-switcher]").forEach((group) => {
      group.hidden = false;
    });
    document.querySelectorAll("[data-theme-option]").forEach((option) => {
      option.setAttribute("aria-pressed", String(option.dataset.themeOption === theme));
    });
  };

  document.addEventListener("click", (event) => {
    const option = event.target.closest("[data-theme-option]");
    if (!option) {
      return;
    }
    const theme = option.dataset.themeOption;
    // Picking the system's own theme goes back to following the system.
    if (theme === systemTheme()) {
      delete root.dataset.theme;
      save(null);
    } else {
      root.dataset.theme = theme;
      save(theme);
    }
    render();
  });

  systemDark.addEventListener("change", render);
  render();
})();
