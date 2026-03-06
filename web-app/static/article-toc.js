document.addEventListener("DOMContentLoaded", () => {
  const toc = document.querySelector("[data-article-toc]");
  if (!toc) {
    return;
  }

  const links = Array.from(toc.querySelectorAll(".article-toc-link"));
  const sections = links
    .map((link) => {
      const id = link.getAttribute("href")?.slice(1);
      const section = id ? document.getElementById(id) : null;
      return section ? { id, link, section } : null;
    })
    .filter(Boolean);

  if (sections.length === 0) {
    return;
  }

  let activeId = null;

  const setActive = (activeId) => {
    sections.forEach(({ id, link }) => {
      link.classList.toggle("is-active", id === activeId);
    });

    const activeEntry = sections.find(({ id }) => id === activeId);
    if (activeEntry) {
      activeEntry.link.scrollIntoView({
        block: "nearest",
        inline: "nearest",
      });
    }
  };

  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);

      if (visible.length > 0) {
        const nextActiveId = visible[0].target.id;
        if (nextActiveId !== activeId) {
          activeId = nextActiveId;
          setActive(activeId);
        }
      }
    },
    {
      rootMargin: "-18% 0px -65% 0px",
      threshold: [0, 1],
    }
  );

  sections.forEach(({ section }) => observer.observe(section));
  activeId = sections[0].id;
  setActive(activeId);
});
