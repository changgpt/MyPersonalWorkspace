// A small formatting toolbar for Markdown textareas (note body, note type
// templates). Each `.md-toolbar` points at a textarea via `data-target`
// (its id); buttons inside it carry a `data-md-action` that this file
// knows how to apply to the current selection.

function wrapSelection(textarea, prefix, suffix, placeholder) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const value = textarea.value;
  const selected = value.slice(start, end) || placeholder;

  textarea.value = value.slice(0, start) + prefix + selected + suffix + value.slice(end);
  const selectionStart = start + prefix.length;
  textarea.focus();
  textarea.setSelectionRange(selectionStart, selectionStart + selected.length);
}

function prefixLines(textarea, linePrefix) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const value = textarea.value;

  const lineStart = value.lastIndexOf("\n", start - 1) + 1;
  const lineEnd = value.indexOf("\n", end) === -1 ? value.length : value.indexOf("\n", end);

  const block = value.slice(lineStart, lineEnd);
  const newBlock = block.split("\n").map((line) => linePrefix + line).join("\n");

  textarea.value = value.slice(0, lineStart) + newBlock + value.slice(lineEnd);
  textarea.focus();
  textarea.setSelectionRange(lineStart, lineStart + newBlock.length);
}

function insertLink(textarea) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const value = textarea.value;
  const linkText = value.slice(start, end) || "link text";

  textarea.value = value.slice(0, start) + `[${linkText}](url)` + value.slice(end);
  const urlStart = start + linkText.length + 3; // "[linkText](".length
  textarea.focus();
  textarea.setSelectionRange(urlStart, urlStart + 3); // selects the placeholder "url"
}

const ACTIONS = {
  bold: (textarea) => wrapSelection(textarea, "**", "**", "bold text"),
  italic: (textarea) => wrapSelection(textarea, "*", "*", "italic text"),
  heading: (textarea) => prefixLines(textarea, "## "),
  bullet: (textarea) => prefixLines(textarea, "- "),
  numbered: (textarea) => prefixLines(textarea, "1. "),
  checkbox: (textarea) => prefixLines(textarea, "- [ ] "),
  link: (textarea) => insertLink(textarea),
};

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".md-toolbar").forEach((toolbar) => {
    const textarea = document.getElementById(toolbar.dataset.target);
    if (!textarea) return;

    toolbar.querySelectorAll("[data-md-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = ACTIONS[button.dataset.mdAction];
        if (action) action(textarea);
      });
    });
  });
});
