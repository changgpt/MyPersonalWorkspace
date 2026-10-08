function focusSearch() {
  const search = document.getElementById("global-search");
  if (!search) return false;
  search.focus();
  search.select();
  return true;
}

// Ctrl/Cmd+K focuses the sidebar search -- the shortcut its own Ctrl K
// badge advertises. Handled in its own listener, *before* the modifier
// guard below, because this is the one shortcut that wants a modifier and
// the one that should still work while you're typing somewhere else
// (which is the whole point of a jump-to-search key).
//
// defaultPrevented is the one guard it needs: the note editor binds
// Ctrl+K to "insert link" on the editor itself, and that handler runs at
// the target before this one sees the event bubble up. Without the check,
// one keypress would open the link prompt *and* yank focus to search.
document.addEventListener("keydown", (event) => {
  if (event.defaultPrevented) return;
  if (event.key !== "k" && event.key !== "K") return;
  if (!(event.ctrlKey || event.metaKey) || event.altKey) return;
  if (focusSearch()) event.preventDefault();
});

// Global keyboard shortcuts: n = new note, t = tasks (Today view),
// / = focus search. Ignored while typing in a field, or with a modifier
// key held (so e.g. Ctrl+N isn't hijacked).
document.addEventListener("keydown", (event) => {
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  const tag = (event.target.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select" || event.target.isContentEditable) {
    return;
  }

  if (event.key === "n") {
    window.location.href = "/notes/new";
  } else if (event.key === "t") {
    window.location.href = "/tasks";
  } else if (event.key === "/") {
    if (focusSearch()) event.preventDefault();
  }
});

// Dark mode toggle, persisted in localStorage. The initial theme is applied
// synchronously by an inline script in <head> (see base.html) so there's no
// light-mode flash before this file loads.
function syncThemeSwitch() {
  const control = document.getElementById("theme-switch");
  if (control) {
    control.setAttribute(
      "aria-checked",
      document.documentElement.dataset.theme === "dark" ? "true" : "false"
    );
  }
}

function toggleDarkMode() {
  const isDark = document.documentElement.dataset.theme === "dark";
  const next = isDark ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("daybook-theme", next);
  syncThemeSwitch();
}

// The theme itself is applied before first paint by an inline script in
// base.html's <head> (so there's no light-mode flash), but the switch's
// aria-checked can only be set once its markup exists.
document.addEventListener("DOMContentLoaded", syncThemeSwitch);

// A .compose-area grows to fit what's in it, so the writing surface has no
// scrollbar and no resize handle (see style.css). The contenteditable note
// editor gets this for free by being a div; a textarea has to be told.
function growComposeArea(area) {
  area.style.height = "auto";
  area.style.height = `${area.scrollHeight}px`;
}

function initComposeAreas() {
  document.querySelectorAll(".compose-area").forEach((area) => {
    if (area.dataset.autoGrow) return;
    area.dataset.autoGrow = "1";
    area.addEventListener("input", () => growComposeArea(area));
    growComposeArea(area);
  });
}

function growAllComposeAreas() {
  document.querySelectorAll(".compose-area").forEach(growComposeArea);
}

document.addEventListener("DOMContentLoaded", initComposeAreas);
// The min-height floor is in vh and the measure is in vw, so both the
// floor and the wrap point move when the window does.
window.addEventListener("resize", growAllComposeAreas);
