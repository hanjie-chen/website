document.addEventListener("DOMContentLoaded", () => {
  const articleBody = document.querySelector(".article-body");
  const modalElement = document.querySelector("[data-image-preview-modal]");
  const modalImage = modalElement?.querySelector("[data-image-preview-target]");
  const modalCaption = modalElement?.querySelector("[data-image-preview-caption]");
  const closeButton = modalElement?.querySelector("[data-image-preview-close]");

  if (
    !articleBody ||
    !modalElement ||
    !modalImage ||
    !modalCaption ||
    !closeButton ||
    typeof modalElement.showModal !== "function"
  ) {
    return;
  }

  const previewableImages = Array.from(articleBody.querySelectorAll("img"));

  if (previewableImages.length === 0) {
    return;
  }

  const openPreview = (image) => {
    const imageSource = image.currentSrc || image.getAttribute("src");
    if (!imageSource) {
      return;
    }

    const altText = (image.getAttribute("alt") || "").trim();

    modalImage.setAttribute("src", imageSource);
    modalImage.setAttribute("alt", altText);
    modalCaption.textContent = altText;
    modalCaption.hidden = altText.length === 0;
    modalElement.showModal();
  };

  previewableImages.forEach((image) => {
    image.classList.add("is-previewable");

    if (!image.closest("a")) {
      image.setAttribute("role", "button");
      image.setAttribute("tabindex", "0");
    }

    image.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      event.preventDefault();
      openPreview(image);
    });

    image.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return;
      }

      event.preventDefault();
      openPreview(image);
    });
  });

  closeButton.addEventListener("click", () => {
    modalElement.close();
  });

  // The dialog fills the viewport; a click outside the content lands on it directly.
  modalElement.addEventListener("click", (event) => {
    if (event.target === modalElement) {
      modalElement.close();
    }
  });

  modalElement.addEventListener("close", () => {
    modalImage.setAttribute("src", "");
    modalImage.setAttribute("alt", "");
    modalCaption.textContent = "";
    modalCaption.hidden = true;
  });
});
