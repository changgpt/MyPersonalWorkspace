// Dismissal and keyboard handling for the search typeahead.
//
// Fetching and rendering is htmx's job (see the hx-get on #global-search):
// this only covers what htmx has no opinion about -- closing the dropdown,
// and walking the results with the arrow keys so the whole thing is usable
// without the mouse.
//
// "Closed" isn't a state kept anywhere: the panel is hidden by a :empty CSS
// rule, so emptying it is what closes it.
(function () {
  let activeIndex = -1;

  const input = () => document.getElementById("global-search");
  const panel = () => document.getElementById("search-suggestions");
  const items = () =>
    Array.from(document.querySelectorAll("#search-suggestions .search-suggestion"));

  function markActive() {
    items().forEach((item, i) => item.classList.toggle("is-active", i === activeIndex));
    const active = items()[activeIndex];
    if (active) active.scrollIntoView({ block: "nearest" });
  }

  function close() {
    const box = panel();
    if (box) box.innerHTML = "";
    activeIndex = -1;
    const field = input();
    if (field) field.setAttribute("aria-expanded", "false");
  }

  function move(step) {
    const count = items().length;
    if (!count) return;
    activeIndex = (activeIndex + step + count) % count;
    markActive();
  }

  document.addEventListener("keydown", (event) => {
    const field = input();
    if (!field || event.target !== field) return;

    if (event.key === "Escape") {
      close();
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!items().length) return;
      event.preventDefault();
      move(event.key === "ArrowDown" ? 1 : -1);
      return;
    }
    if (event.key === "Enter" && activeIndex >= 0) {
      // Only hijack Enter when something is actually highlighted --
      // otherwise let the form submit through to the full results page.
      const active = items()[activeIndex];
      if (active) {
        event.preventDefault();
        window.location.href = active.href;
      }
    }
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".search-box")) close();
  });

  // Each swap is a fresh list, so the highlight starts over rather than
  // pointing at whatever row happened to be in that position before.
  document.addEventListener("htmx:afterSwap", (event) => {
    if (event.target.id !== "search-suggestions") return;
    activeIndex = -1;
    const field = input();
    if (field) {
      field.setAttribute("aria-expanded", items().length ? "true" : "false");
    }
  });
})();
