// Theme toggle: the page follows the system theme until the visitor picks one.
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

  // Each button shows and names the theme a click switches to.
  const render = () => {
    const target = currentTheme() === "dark" ? "light" : "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      const label = target === "light" ? button.dataset.labelLight : button.dataset.labelDark;
      button.dataset.target = target;
      button.setAttribute("aria-label", label);
      button.title = label;
      button.hidden = false;
    });
  };

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-theme-toggle]")) {
      return;
    }
    const next = currentTheme() === "dark" ? "light" : "dark";
    // Picking the system's own theme goes back to following the system.
    if (next === systemTheme()) {
      delete root.dataset.theme;
      save(null);
    } else {
      root.dataset.theme = next;
      save(next);
    }
    render();
  });

  systemDark.addEventListener("change", render);
  render();
})();
