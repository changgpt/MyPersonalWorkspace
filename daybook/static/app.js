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

// "+ New project" next to a project picker: creates one and selects it
// without leaving the form you're filling in. A prompt() rather than an
// inline field or a modal -- this is a one-field, single-user action, and
// the app already uses prompt() for the editor's link dialog.
//
// The new <option> has to be appended to the real <select> *and* the
// styled dropdown rebuilt, because select.js mirrors the options into its
// own panel once at enhance time (see static/select.js).
async function addProjectInline(button) {
  const select = document.getElementById(button.dataset.targetSelect);
  if (!select) return;
  const name = window.prompt("New project name:");
  if (!name || !name.trim()) return;

  const body = new FormData();
  body.append("name", name.trim());
  let project;
  try {
    const response = await fetch(button.dataset.addProject, {
      method: "POST",
      body,
      // What makes the route answer with JSON instead of its usual
      // redirect to the new project's page.
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(response.statusText);
    project = await response.json();
  } catch (err) {
    window.showToast("Could not add that project.");
    return;
  }

  // find-or-create on the server, so re-typing an existing name must
  // select the existing option rather than add a second one.
  let option = [...select.options].find((o) => o.value === String(project.id));
  if (!option) {
    option = new Option(project.name, String(project.id));
    select.add(option);
  }
  select.value = String(project.id);
  select.dispatchEvent(new Event("change", { bubbles: true }));
  if (window.reEnhanceSelect) window.reEnhanceSelect(select);
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-add-project]");
  if (button) addProjectInline(button);
});
