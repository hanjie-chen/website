// Mobile navigation disclosure: the toggle shows or hides the page menu.
document.addEventListener("DOMContentLoaded", () => {
  const menu = document.querySelector("[data-site-nav-menu]");
  const toggle = menu?.querySelector("[aria-controls]");
  const panel = toggle && document.getElementById(toggle.getAttribute("aria-controls"));

  if (!menu || !toggle || !panel) {
    return;
  }

  const setOpen = (open) => {
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
  };

  toggle.addEventListener("click", () => {
    setOpen(panel.hidden);
  });

  document.addEventListener("click", (event) => {
    if (!panel.hidden && !menu.contains(event.target)) {
      setOpen(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) {
      setOpen(false);
      toggle.focus();
    }
  });

  // Tabbing past the last item closes the menu instead of leaving it open behind.
  menu.addEventListener("focusout", (event) => {
    if (!panel.hidden && event.relatedTarget && !menu.contains(event.relatedTarget)) {
      setOpen(false);
    }
  });
});

// Settings disclosure: like the mobile menu, an outside click, Escape or tabbing
// away closes it. Without scripts it still opens and closes natively.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-site-settings]").forEach((settings) => {
    const summary = settings.querySelector("summary");

    document.addEventListener("click", (event) => {
      if (settings.open && !settings.contains(event.target)) {
        settings.open = false;
      }
    });

    settings.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && settings.open) {
        settings.open = false;
        summary.focus();
      }
    });

    settings.addEventListener("focusout", (event) => {
      if (settings.open && event.relatedTarget && !settings.contains(event.relatedTarget)) {
        settings.open = false;
      }
    });
  });
});
