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

  // The section being read is the last one whose heading has passed the
  // reading line, so jumps, reloads and fast scrolls all land on the same
  // answer. A short last section never reaches the line, so the end of the
  // page selects it.
  const atPageEnd = () =>
    window.scrollY > 0 &&
    window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;

  const sectionInView = () => {
    if (atPageEnd()) {
      return sections[sections.length - 1].id;
    }

    const readingLine = window.innerHeight * 0.25;
    let currentId = sections[0].id;
    for (const { id, section } of sections) {
      if (section.getBoundingClientRect().top > readingLine) {
        break;
      }
      currentId = id;
    }
    return currentId;
  };

  let frame = 0;
  const update = () => {
    frame = 0;
    const nextActiveId = sectionInView();
    if (nextActiveId !== activeId) {
      activeId = nextActiveId;
      setActive(nextActiveId);
    }
  };
  const scheduleUpdate = () => {
    if (!frame) {
      frame = window.requestAnimationFrame(update);
    }
  };

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

  window.addEventListener("scroll", scheduleUpdate, { passive: true });
  window.addEventListener("resize", scheduleUpdate);
  update();
});
