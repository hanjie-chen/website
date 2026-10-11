// Top-bar disclosures: an outside click, Escape or tabbing away closes them.
const dismissOnLeave = (container, isOpen, close, focusTarget) => {
  document.addEventListener("click", (event) => {
    if (isOpen() && !container.contains(event.target)) {
      close();
    }
  });

  // Listen on the document: a mouse click does not focus every control (Safari).
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isOpen()) {
      close();
      focusTarget.focus();
    }
  });

  // Tabbing past the last item closes the disclosure instead of leaving it open behind.
  container.addEventListener("focusout", (event) => {
    if (isOpen() && event.relatedTarget && !container.contains(event.relatedTarget)) {
      close();
    }
  });
};

document.addEventListener("DOMContentLoaded", () => {
  // Mobile navigation: the toggle shows or hides the page menu.
  const menu = document.querySelector("[data-site-nav-menu]");
  const toggle = menu?.querySelector("[aria-controls]");
  const panel = toggle && document.getElementById(toggle.getAttribute("aria-controls"));

  if (menu && toggle && panel) {
    const setOpen = (open) => {
      panel.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
    };

    toggle.addEventListener("click", () => {
      setOpen(panel.hidden);
    });
    dismissOnLeave(menu, () => !panel.hidden, () => setOpen(false), toggle);
  }

  // Settings: a native details element, so it also opens and closes without scripts.
  document.querySelectorAll("[data-site-settings]").forEach((settings) => {
    dismissOnLeave(
      settings,
      () => settings.open,
      () => {
        settings.open = false;
      },
      settings.querySelector("summary"),
    );
  });
});
