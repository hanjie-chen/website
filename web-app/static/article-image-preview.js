document.addEventListener("DOMContentLoaded", () => {
  const articleBody = document.querySelector(".article-body");
  const modalElement = document.querySelector("[data-image-preview-modal]");
  const modalImage = modalElement?.querySelector("[data-image-preview-target]");
  const modalCaption = modalElement?.querySelector("[data-image-preview-caption]");

  if (
    !articleBody ||
    !modalElement ||
    !modalImage ||
    !modalCaption ||
    !window.bootstrap?.Modal
  ) {
    return;
  }

  const previewModal = window.bootstrap.Modal.getOrCreateInstance(modalElement);
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
    previewModal.show();
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

  modalElement.addEventListener("hidden.bs.modal", () => {
    modalImage.setAttribute("src", "");
    modalImage.setAttribute("alt", "");
    modalCaption.textContent = "";
    modalCaption.hidden = true;
  });
});
