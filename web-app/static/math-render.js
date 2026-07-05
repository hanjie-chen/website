(function () {
  function renderArticleMath() {
    var articleBody = document.querySelector(".article-body");

    if (!articleBody || typeof renderMathInElement !== "function") {
      return;
    }

    renderMathInElement(articleBody, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false },
      ],
      throwOnError: false,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderArticleMath);
  } else {
    renderArticleMath();
  }
})();
