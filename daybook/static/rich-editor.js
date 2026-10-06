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

const TASK_LIST_ITEM_HTML =
  '<ul class="task-list"><li class="task-list-item">' +
  '<label class="task-list-control"><input type="checkbox" disabled>' +
  '<span class="task-list-indicator"></span></label> New checklist item</li></ul>';

const ACTIONS = {
  bold: (editor) => document.execCommand("bold"),
  italic: (editor) => document.execCommand("italic"),
  heading: (editor) => document.execCommand("formatBlock", false, "h2"),
  bullet: (editor) => document.execCommand("insertUnorderedList"),
  numbered: (editor) => document.execCommand("insertOrderedList"),
  checkbox: (editor) => document.execCommand("insertHTML", false, TASK_LIST_ITEM_HTML),
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
      });
    });

    editor.addEventListener("keydown", (event) => {
      if (event.key !== "Tab") return;
      event.preventDefault();
      document.execCommand(event.shiftKey ? "outdent" : "indent");
    });
  });
});

})();
