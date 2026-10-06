// WYSIWYG editing for the note body: a contenteditable div (".rich-editor")
// styled/formatted live via document.execCommand, converted to Markdown
// with Turndown (vendor/turndown.js) right before the form submits. The
// server never sees HTML -- it still stores and renders plain Markdown
// exactly as before, so search, task extraction, and exports are
// unaffected. See CLAUDE.md for why.

(function () {

function buildTurndownService() {
  const turndownService = new TurndownService({ headingStyle: "atx", bulletListMarker: "-" });

  // Matches the exact HTML pymdownx.tasklist renders server-side (see
  // markdown_utils.py), so a checklist item round-trips to "- [ ] "/
  // "- [x] " whether it came from the server or was typed in the editor.
  turndownService.addRule("taskListItems", {
    filter: (node) => node.nodeName === "LI" && node.querySelector('input[type="checkbox"]'),
    replacement: (_content, node) => {
      const checkbox = node.querySelector('input[type="checkbox"]');
      const checked = checkbox.checked || checkbox.hasAttribute("checked");
      const text = node.textContent.trim();
      return `- [${checked ? "x" : " "}] ${text}\n`;
    },
  });

  return turndownService;
}

const turndownService = buildTurndownService();

// Chrome's execCommand('indent') nests a sub-list as a *sibling* of the
// preceding <li> (`<ul><li>A</li><ul><li>B</li></ul></ul>`), which renders
// fine but isn't valid HTML -- a <ul> can only contain <li> children.
// Turndown (reasonably) only recognizes nesting when the sub-list is
// *inside* the <li>, so without this fix-up every indented item silently
// flattens back to the top level on save. Moves each such list into the
// <li> that precedes it.
function normalizeNestedLists(root) {
  root.querySelectorAll("ul, ol").forEach((list) => {
    const prev = list.previousElementSibling;
    if (prev && prev.tagName === "LI" && list.parentElement === prev.parentElement) {
      prev.appendChild(list);
    }
  });
}

// Chrome's own execCommand('insertUnorderedList'/'insertOrderedList'), when
// run with the cursor in an empty paragraph that follows a paragraph with
// inline formatting, sometimes nests the new <ul>/<ol> *inside* that <p>
// instead of replacing it -- a <p> can't legally contain a <ul>. Browsers
// render that leniently, but it reliably confuses the <ul> styling that
// depends on it being a direct child of the editor (hence a stray bullet
// showing even though .task-list { list-style: none } is applied), and it's
// invalid input for Turndown. Splits each such <p> around its block-level
// children so lists end up as proper siblings instead.
function unwrapBlockChildrenFromParagraphs(root) {
  root.querySelectorAll("p").forEach((p) => {
    const hasBlockChild = Array.from(p.children).some((el) => ["UL", "OL", "P", "DIV"].includes(el.tagName));
    if (!hasBlockChild) return;

    const parent = p.parentElement;
    let inlineRun = document.createElement("p");

    Array.from(p.childNodes).forEach((node) => {
      const isBlock = node.nodeType === Node.ELEMENT_NODE && ["UL", "OL", "P", "DIV"].includes(node.tagName);
      if (isBlock) {
        if (inlineRun.childNodes.length) {
          parent.insertBefore(inlineRun, p);
          inlineRun = document.createElement("p");
        }
        parent.insertBefore(node, p);
      } else {
        inlineRun.appendChild(node);
      }
    });

    if (inlineRun.childNodes.length) parent.insertBefore(inlineRun, p);
    p.remove();
  });
}

function buildChecklistListElement() {
  const list = document.createElement("ul");
  list.className = "task-list";
  const item = document.createElement("li");
  item.className = "task-list-item";
  const label = document.createElement("label");
  label.className = "task-list-control";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.disabled = true;
  const indicator = document.createElement("span");
  indicator.className = "task-list-indicator";
  label.append(checkbox, indicator);
  item.append(label, document.createTextNode(" New checklist item"));
  list.appendChild(item);
  return list;
}

// Builds the checklist item as real DOM nodes rather than an HTML string.
// execCommand('insertHTML', ...) was tried first, but a <ul> can't legally
// live inside a <p> -- when the cursor sat in the empty <p> Chrome leaves
// behind after exiting a list (two Enters), the browser's own paragraph-
// splitting logic for that case produced corrupted markup (a <li> stranded
// outside any <ul>). Inserting nodes directly, and replacing rather than
// inserting-into an empty block, avoids that invalid nesting entirely.
function insertChecklistItem(editor) {
  const selection = window.getSelection();
  if (!selection.rangeCount) return;
  const range = selection.getRangeAt(0);
  range.deleteContents();

  const list = buildChecklistListElement();

  let block = range.startContainer;
  block = block.nodeType === Node.ELEMENT_NODE ? block : block.parentElement;
  while (block && block !== editor && !["P", "DIV", "LI"].includes(block.tagName)) {
    block = block.parentElement;
  }
  const isEmptyBlock = block && block !== editor && block.textContent.trim() === "";

  if (isEmptyBlock && (block.tagName === "P" || block.tagName === "DIV")) {
    block.replaceWith(list);
  } else if (isEmptyBlock && block.tagName === "LI") {
    // The cursor is on an empty line that's still nested inside a list --
    // e.g. pressing Enter after an indented item only backs out one
    // nesting level (another <li>), it doesn't fully exit to a plain
    // paragraph. Grafting a <ul> into that <li>'s position would nest a
    // <ul> directly inside another <ul>, which is invalid and previously
    // corrupted the saved Markdown (see git history). Insert after the
    // outermost list instead, and drop the now-pointless empty line.
    let outerList = block.parentElement;
    for (let node = outerList; node && node !== editor; node = node.parentElement) {
      if (node.tagName === "UL" || node.tagName === "OL") outerList = node;
    }
    outerList.insertAdjacentElement("afterend", list);
    const emptyLiParent = block.parentElement;
    block.remove();
    if (emptyLiParent.children.length === 0) emptyLiParent.remove();
  } else {
    range.insertNode(list);
  }

  // Select the placeholder text so typing immediately replaces it, same
  // convention as the other toolbar actions (bold/italic/link).
  const insertedItem = list.querySelector("li");
  const newRange = document.createRange();
  newRange.selectNodeContents(insertedItem.lastChild);
  selection.removeAllRanges();
  selection.addRange(newRange);
}

const ACTIONS = {
  bold: (editor) => document.execCommand("bold"),
  italic: (editor) => document.execCommand("italic"),
  heading: (editor) => document.execCommand("formatBlock", false, "h2"),
  bullet: (editor) => document.execCommand("insertUnorderedList"),
  numbered: (editor) => document.execCommand("insertOrderedList"),
  checkbox: (editor) => insertChecklistItem(editor),
  link: (editor) => {
    const url = window.prompt("Link URL:", "https://");
    if (url) document.execCommand("createLink", false, url);
  },
  indent: (editor) => document.execCommand("indent"),
  outdent: (editor) => document.execCommand("outdent"),
};

// Converts one editor's current HTML into Markdown and writes it into its
// hidden <textarea data-source="<editor id>">, which is the field that
// actually gets submitted. Called from the form's onsubmit="" attribute,
// so it's attached to window explicitly (everything else in this file is
// scoped to the enclosing IIFE).
function syncRichEditors(form) {
  form.querySelectorAll(".rich-editor").forEach((editor) => {
    const target = document.querySelector(`textarea[data-source="${editor.id}"]`);
    if (!target) return;

    const clone = document.createElement("div");
    clone.innerHTML = editor.innerHTML;
    normalizeNestedLists(clone);
    target.value = turndownService.turndown(clone.innerHTML);
  });
}
window.syncRichEditors = syncRichEditors;

document.addEventListener("DOMContentLoaded", () => {
  document.execCommand("defaultParagraphSeparator", false, "p");

  document.querySelectorAll(".md-toolbar").forEach((toolbar) => {
    const editor = document.getElementById(toolbar.dataset.target);
    if (!editor || !editor.isContentEditable) return;

    toolbar.querySelectorAll("[data-md-action]").forEach((button) => {
      // mousedown (not click) + preventDefault keeps the editor's current
      // selection intact -- otherwise focus would move to the button
      // before the action runs, losing whatever text was selected.
      button.addEventListener("mousedown", (event) => {
        event.preventDefault();
        const action = ACTIONS[button.dataset.mdAction];
        if (action) action(editor);
        unwrapBlockChildrenFromParagraphs(editor);
      });
    });

    editor.addEventListener("keydown", (event) => {
      if (event.key !== "Tab") return;
      event.preventDefault();
      document.execCommand(event.shiftKey ? "outdent" : "indent");
      unwrapBlockChildrenFromParagraphs(editor);
    });

    // General safety net: typing/Enter can trigger the same browser list-
    // nesting quirk without ever touching the toolbar.
    editor.addEventListener("input", () => unwrapBlockChildrenFromParagraphs(editor));
  });
});

})();
