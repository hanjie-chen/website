// A local hint that a dated brief was opened, not that it was read to completion.
(() => {
  const key = "daily-brief-opened-v1";
  const isDate = (value) =>
    typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
  const read = () => {
    try {
      const saved = JSON.parse(localStorage.getItem(key) || "[]");
      return Array.isArray(saved) ? saved.filter(isDate) : [];
    } catch {
      return [];
    }
  };

  const detail = document.querySelector("[data-brief-opened-date]");
  const refresh = () => {
    const opened = new Set(read());
    if (detail && isDate(detail.dataset.briefOpenedDate)) {
      opened.add(detail.dataset.briefOpenedDate);
      try {
        // Bound storage; ISO dates sort in calendar order. Shared across languages.
        localStorage.setItem(key, JSON.stringify([...opened].sort().slice(-14)));
      } catch {
        // Storage may be disabled; ordinary navigation must still work.
      }
    }
    document.querySelectorAll("[data-brief-archive-date]").forEach((row) => {
      row.classList.toggle("is-opened", opened.has(row.dataset.briefArchiveDate));
    });
  };

  refresh();
  window.addEventListener("pageshow", refresh);
  window.addEventListener("focus", refresh);
  window.addEventListener("storage", (event) => {
    if (event.key === key || event.key === null) refresh();
  });
})();
