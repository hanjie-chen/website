document.addEventListener("DOMContentLoaded", () => {
  const toc = document.querySelector("[data-article-toc]");
  if (!toc) {
    return;
  }

  const nodes = Array.from(toc.querySelectorAll("[data-toc-node]"));
  const sections = nodes
    .map((node) => {
      const link = node.querySelector("[data-toc-link]");
      const id = link.getAttribute("href")?.slice(1);
      const section = id ? document.getElementById(id) : null;
      return section ? { id, link, node, section } : null;
    })
    .filter(Boolean);

  if (sections.length === 0) {
    return;
  }

  let activeId = null;

  const expandSubtree = (node) => {
    if (!node) {
      return;
    }

    node.classList.add("is-expanded");
    node
      .querySelectorAll("[data-toc-node]")
      .forEach((childNode) => childNode.classList.add("is-expanded"));
  };

  const findScopeRoot = (node) => {
    const rootAncestor = node.parentElement?.closest(
      '[data-toc-node][data-toc-level="1"]'
    );
    return rootAncestor || node;
  };

  const setActive = (nextActiveId) => {
    sections.forEach(({ id, link, node }) => {
      link.classList.toggle("is-active", id === nextActiveId);
      node.classList.remove("is-expanded", "is-current-branch");
    });

    const activeEntry = sections.find(({ id }) => id === nextActiveId);
    if (activeEntry) {
      // Keep the current reading branch highlighted for orientation.
      activeEntry.link.classList.add("is-active");

      let currentNode = activeEntry.node;
      while (currentNode?.matches("[data-toc-node]")) {
        currentNode.classList.add("is-current-branch");
        currentNode = currentNode.parentElement?.closest("[data-toc-node]");
      }

      // Once the reader is inside an h1 section, expose that whole subtree.
      expandSubtree(findScopeRoot(activeEntry.node));

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
          setActive(nextActiveId);
        }
      }
    },
    {
      rootMargin: "-18% 0px -65% 0px",
      threshold: [0, 1],
    }
  );

  const activeFromHash = window.location.hash
    ? decodeURIComponent(window.location.hash.slice(1))
    : null;

  const initialActiveId = sections.some(({ id }) => id === activeFromHash)
    ? activeFromHash
    : sections[0].id;

  toc.addEventListener("click", (event) => {
    const link = event.target.closest("[data-toc-link]");
    if (!link) {
      return;
    }

    const nextActiveId = link.getAttribute("href")?.slice(1);
    if (!nextActiveId) {
      return;
    }

    activeId = nextActiveId;
    setActive(nextActiveId);
  });

  sections.forEach(({ section }) => observer.observe(section));
  activeId = initialActiveId;
  setActive(initialActiveId);
});
