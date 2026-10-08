// WYSIWYG editing for the note body: a contenteditable div (".rich-editor")
// styled/formatted live via document.execCommand, converted to Markdown
// with Turndown (vendor/turndown.js) right before the form submits. The
// server never sees HTML -- it still stores and renders plain Markdown
// exactly as before, so search, task extraction, and exports are
// unaffected. See CLAUDE.md for why.

(function () {

function buildTurndownService() {
  const turndownService = new TurndownService({
    headingStyle: "atx",
    bulletListMarker: "-",
    codeBlockStyle: "fenced",
    emDelimiter: "*",
  });

  // Turndown core has no strikethrough rule (it's in the GFM plugin we
  // don't vendor), so <del> would otherwise lose its tag and come back as
  // plain text. "~~" is what pymdownx.tilde renders back to <del>.
  turndownService.addRule("strikethrough", {
    filter: ["del", "s", "strike"],
    replacement: (content) => (content.trim() ? `~~${content}~~` : content),
  });

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

// The exact control pymdownx.tasklist renders (markdown_utils.py). Built
// from scratch rather than copied from existing markup, so it's also how a
// pasted checkbox gets rebuilt without carrying the source's attributes.
// Text typed into a *wholly empty* editor (a new note whose type has no
// template) lands as a bare text node with no block wrapper, because
// defaultParagraphSeparator only governs what Enter creates, not the first
// line. execCommand then has no block to operate on: insertUnorderedList
// rebuilds the node and drops the selection back to the editor's start, so
// the next Enter inserts *above* the line you just typed -- which cascaded
// into the whole note being scrambled into one garbled item on save.
// Promoting that bare run to a <p> fixes it at the source. formatBlock
// (rather than DOM surgery) is used because it preserves the caret; the
// check is deliberately narrow -- only when the caret itself sits in a
// direct text child of the editor -- so it can never reformat a list item
// or heading. The editor is left genuinely empty until something is typed,
// which is what keeps the `.rich-editor:empty::before` placeholder working.
function ensureTopLevelBlock(editor) {
  const selection = window.getSelection();
  if (!selection.rangeCount) return;
  const node = selection.getRangeAt(0).startContainer;
  if (node.nodeType === Node.TEXT_NODE && node.parentElement === editor) {
    document.execCommand("formatBlock", false, "p");
  }
}

function buildChecklistControl(checked) {
  const label = document.createElement("label");
  label.className = "task-list-control";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.disabled = true;
  checkbox.checked = Boolean(checked);
  if (checked) checkbox.setAttribute("checked", "");
  const indicator = document.createElement("span");
  indicator.className = "task-list-indicator";
  label.append(checkbox, indicator);
  return label;
}

function buildChecklistListElement() {
  const list = document.createElement("ul");
  list.className = "task-list";
  const item = document.createElement("li");
  item.className = "task-list-item";
  item.append(buildChecklistControl(false), document.createTextNode(" New checklist item"));
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

// Pasted HTML is the main source of junk markup in a note: Word, Google
// Docs and most web pages carry <span style="font-family:...">, <font>,
// MsoNormal classes, nested divs and inline colours, none of which survive
// the trip to Markdown -- they just make Turndown emit odd output, or
// silently vanish while the editor shows formatting the saved note won't
// have. So a paste is rebuilt from an allowlist: the tags that have a
// Markdown equivalent, no attributes except a link's href.
const PASTE_ALLOWED = new Set([
  "P", "BR", "STRONG", "B", "EM", "I", "DEL", "S", "STRIKE", "CODE", "PRE",
  "H1", "H2", "H3", "H4", "H5", "H6", "UL", "OL", "LI", "BLOCKQUOTE", "A", "HR",
]);

// Dropped whole, contents and all. Everything else not on the allowlist is
// unwrapped (the wrapper is noise, the words inside are the point) -- but
// for these the "words inside" are a stylesheet, a script, or a form
// control's label, which is how copying from a web page used to dump CSS
// into the middle of a note.
const PASTE_DROPPED = new Set([
  "SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "TITLE", "META", "LINK", "BASE",
  "IFRAME", "OBJECT", "EMBED", "SVG", "CANVAS", "VIDEO", "AUDIO",
  "BUTTON", "SELECT", "OPTION", "TEXTAREA", "FORM",
]);

// Block-level containers with no Markdown tag of their own still mark a
// paragraph break, so they become <p> instead of being flattened into the
// surrounding text: Google Docs and most web pages lay paragraphs out in
// <div>s, and unwrapping those ran a whole page together into one block.
// (A <p> that ends up holding a list or another <p> is invalid, but
// unwrapBlockChildrenFromParagraphs already runs right after every paste
// and splits exactly that apart.)
const PASTE_AS_PARAGRAPH = new Set([
  "DIV", "SECTION", "ARTICLE", "HEADER", "FOOTER", "MAIN", "ASIDE",
  "FIGURE", "FIGCAPTION", "ADDRESS", "DL", "DD", "DT", "TR", "CAPTION",
]);

function sanitizePastedHtml(html) {
  const source = new DOMParser().parseFromString(html, "text/html").body;
  const out = document.createDocumentFragment();

  function convert(node, target) {
    node.childNodes.forEach((child) => {
      if (child.nodeType === Node.TEXT_NODE) {
        target.appendChild(document.createTextNode(child.nodeValue));
        return;
      }
      if (child.nodeType !== Node.ELEMENT_NODE) return; // drops comments

      if (PASTE_DROPPED.has(child.nodeName)) return;

      // A checklist copied from inside the app (or from a rendered note):
      // rebuild the control from clean nodes so it keeps working, without
      // carrying the source element's attributes.
      if (child.nodeName === "INPUT") {
        if (child.getAttribute("type") === "checkbox") {
          target.appendChild(buildChecklistControl(child.hasAttribute("checked") || child.checked));
        }
        return;
      }

      if (!PASTE_ALLOWED.has(child.nodeName)) {
        // Unwrap rather than discard: a <span>/<label>/<font> wrapper is
        // noise, but the words inside it are the point. Block-level
        // wrappers keep their break by becoming a paragraph; table cells
        // get a space so "cell a" and "cell b" don't run together.
        if (PASTE_AS_PARAGRAPH.has(child.nodeName)) {
          const para = document.createElement("p");
          convert(child, para);
          if (para.childNodes.length) target.appendChild(para);
          return;
        }
        convert(child, target);
        if (child.nodeName === "TD" || child.nodeName === "TH") {
          target.appendChild(document.createTextNode(" "));
        }
        return;
      }
      const clean = document.createElement(child.nodeName.toLowerCase());
      if (child.nodeName === "A" && child.getAttribute("href")) {
        clean.setAttribute("href", child.getAttribute("href"));
      }
      convert(child, clean);
      target.appendChild(clean);
    });
  }

  convert(source, out);
  const wrapper = document.createElement("div");
  wrapper.appendChild(out);
  return wrapper.innerHTML;
}

function handlePaste(event, editor) {
  const clipboard = event.clipboardData;
  if (!clipboard) return;
  const html = clipboard.getData("text/html");
  const text = clipboard.getData("text/plain");
  if (!html && !text) return;

  event.preventDefault();
  // insertHTML (rather than DOM surgery) keeps the paste on the browser's
  // own undo stack, so Ctrl+Z after a paste behaves normally.
  if (html) {
    document.execCommand("insertHTML", false, sanitizePastedHtml(html));
  } else {
    document.execCommand("insertText", false, text);
  }
  unwrapBlockChildrenFromParagraphs(editor);
}

// Wraps the selection in <code>. There's no execCommand for it, and
// insertHTML would drop the selected text, so this moves the range's
// contents into the element.
function wrapInlineCode() {
  const selection = window.getSelection();
  if (!selection.rangeCount) return;
  const range = selection.getRangeAt(0);
  if (range.collapsed) return;
  const code = document.createElement("code");
  code.appendChild(range.extractContents());
  range.insertNode(code);
  selection.removeAllRanges();
  const after = document.createRange();
  after.selectNodeContents(code);
  selection.addRange(after);
}

function promptForLink() {
  const url = window.prompt("Link URL:", "https://");
  if (url) document.execCommand("createLink", false, url);
}

const ACTIONS = {
  bold: () => document.execCommand("bold"),
  italic: () => document.execCommand("italic"),
  strike: () => document.execCommand("strikeThrough"),
  // "Size" in a Markdown note means heading level -- there's no arbitrary
  // font size to store, and inventing one would mean saving HTML/CSS that
  // search, export and the .docx import all ignore.
  paragraph: () => document.execCommand("formatBlock", false, "p"),
  h1: () => document.execCommand("formatBlock", false, "h1"),
  h2: () => document.execCommand("formatBlock", false, "h2"),
  h3: () => document.execCommand("formatBlock", false, "h3"),
  quote: () => document.execCommand("formatBlock", false, "blockquote"),
  code: () => wrapInlineCode(),
  bullet: () => document.execCommand("insertUnorderedList"),
  numbered: () => document.execCommand("insertOrderedList"),
  checkbox: (editor) => insertChecklistItem(editor),
  link: () => promptForLink(),
  clear: () => {
    document.execCommand("removeFormat");
    document.execCommand("formatBlock", false, "p");
  },
  indent: () => document.execCommand("indent"),
  outdent: () => document.execCommand("outdent"),
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

// Reading size: scales the editor and the rendered note body together, so
// a note is the same size while writing it and while reading it back. It's
// a *display* preference (localStorage, like the theme), never part of the
// note -- the Markdown is identical whichever size is chosen, so changing
// it can't alter what's exported or searched.
const SIZE_KEY = "filofax-note-size";
const SIZES = ["s", "m", "l", "xl"];

function storedSize() {
  const saved = localStorage.getItem(SIZE_KEY);
  return SIZES.includes(saved) ? saved : "m";
}

function applySize(size) {
  document.querySelectorAll(".rich-editor, .note-body").forEach((el) => {
    SIZES.forEach((s) => el.classList.toggle(`note-size-${s}`, s === size));
  });
}

function stepSize(direction) {
  const next = SIZES[Math.min(SIZES.length - 1, Math.max(0, SIZES.indexOf(storedSize()) + direction))];
  localStorage.setItem(SIZE_KEY, next);
  applySize(next);
}

function updateWordCount(editor) {
  const target = document.querySelector(`[data-word-count-for="${editor.id}"]`);
  if (!target) return;
  const words = editor.textContent.trim().split(/\s+/).filter(Boolean).length;
  target.textContent = `${words} ${words === 1 ? "word" : "words"}`;
}

document.addEventListener("DOMContentLoaded", () => {
  document.execCommand("defaultParagraphSeparator", false, "p");
  applySize(storedSize());

  document.querySelectorAll("[data-note-size]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      stepSize(Number(button.dataset.noteSize));
    });
  });

  document.querySelectorAll(".md-toolbar").forEach((toolbar) => {
    const editor = document.getElementById(toolbar.dataset.target);
    if (!editor || !editor.isContentEditable) return;

    toolbar.querySelectorAll("[data-md-action]").forEach((button) => {
      // mousedown (not click) + preventDefault keeps the editor's current
      // selection intact -- otherwise focus would move to the button
      // before the action runs, losing whatever text was selected.
      button.addEventListener("mousedown", (event) => {
        event.preventDefault();
        ensureTopLevelBlock(editor);
        const action = ACTIONS[button.dataset.mdAction];
        if (action) action(editor);
        unwrapBlockChildrenFromParagraphs(editor);
        updateWordCount(editor);
      });
    });

    editor.addEventListener("keydown", (event) => {
      if (event.key === "Tab") {
        event.preventDefault();
        ensureTopLevelBlock(editor);
        document.execCommand(event.shiftKey ? "outdent" : "indent");
        unwrapBlockChildrenFromParagraphs(editor);
        return;
      }
      if (!(event.metaKey || event.ctrlKey)) return;
      const key = event.key.toLowerCase();
      if (key === "k") {
        event.preventDefault();
        promptForLink();
      } else if (key === "u") {
        // Ctrl+U would insert <u>, which has no Markdown equivalent: it
        // would vanish on save while the editor showed it as underlined.
        // Better to do nothing than to show formatting that won't persist.
        event.preventDefault();
      }
    });

    editor.addEventListener("paste", (event) => handlePaste(event, editor));

    // General safety net: typing/Enter can trigger the same browser list-
    // nesting quirk without ever touching the toolbar.
    editor.addEventListener("input", () => {
      ensureTopLevelBlock(editor);
      unwrapBlockChildrenFromParagraphs(editor);
      updateWordCount(editor);
    });

    updateWordCount(editor);
  });
});

})();
