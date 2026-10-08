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
    const search = document.getElementById("global-search");
    if (search) {
      event.preventDefault();
      search.focus();
    }
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
