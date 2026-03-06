function getCodeText(codeBlock) {
  const codeElement =
    codeBlock.querySelector("td.code code") ||
    codeBlock.querySelector("pre code") ||
    codeBlock.querySelector("pre");

  if (!codeElement) {
    return "";
  }

  return codeElement.innerText.replace(/\n$/, "");
}

function fallbackCopyText(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "");
  textArea.style.position = "fixed";
  textArea.style.opacity = "0";
  document.body.appendChild(textArea);
  textArea.select();
  document.execCommand("copy");
  document.body.removeChild(textArea);
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  fallbackCopyText(text);
}

function setButtonState(button, copied) {
  button.textContent = copied ? "Copied" : "Copy";
  button.classList.toggle("is-copied", copied);
  button.setAttribute("aria-label", copied ? "Code copied" : "Copy code");
}

function enhanceCodeBlock(codeBlock) {
  if (codeBlock.dataset.copyEnhanced === "true") {
    return;
  }

  const codeText = getCodeText(codeBlock);
  if (!codeText) {
    return;
  }

  const button = document.createElement("button");
  button.type = "button";
  button.className = "code-copy-btn";
  button.setAttribute("aria-label", "Copy code");
  button.textContent = "Copy";

  let resetTimerId = null;

  button.addEventListener("click", async () => {
    try {
      await copyText(codeText);
      setButtonState(button, true);
      window.clearTimeout(resetTimerId);
      resetTimerId = window.setTimeout(() => {
        setButtonState(button, false);
      }, 1800);
    } catch (_error) {
      setButtonState(button, false);
    }
  });

  codeBlock.appendChild(button);
  codeBlock.dataset.copyEnhanced = "true";
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".codehilite").forEach(enhanceCodeBlock);
});
