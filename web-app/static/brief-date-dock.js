// Dock the brief date into the top bar once the hero date scrolls under it.
(() => {
  const hero = document.querySelector("[data-brief-hero-date]");
  const navbar = document.querySelector(".navbar-custom");
  if (!hero || !navbar) {
    return;
  }

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  // Compare positions directly: IntersectionObserver reports no root bounds and
  // ignores rootMargin inside cross-origin frames, such as embedded previews.
  let pending = false;
  const update = () => {
    pending = false;
    const docked =
      hero.getBoundingClientRect().bottom <= navbar.getBoundingClientRect().bottom;
    navbar.classList.toggle("is-brief-docked", docked);
  };
  const scheduleUpdate = () => {
    if (!pending) {
      pending = true;
      window.requestAnimationFrame(update);
    }
  };
  window.addEventListener("scroll", scheduleUpdate, { passive: true });
  window.addEventListener("resize", scheduleUpdate);
  update();

  const backToTop = navbar.querySelector("[data-brief-back-to-top]");
  if (backToTop) {
    backToTop.addEventListener("click", (event) => {
      event.preventDefault();
      window.scrollTo({ top: 0, behavior: reduceMotion.matches ? "auto" : "smooth" });
      // The dock hides at the top, so keep keyboard focus on the page date.
      hero.querySelector("h1")?.focus({ preventScroll: true });
    });
  }
})();
