// Replaces every <select> with a styled dropdown that opens on hover.
//
// Neither half of that is possible with a native select: its popup is
// drawn by the OS (so border-radius, colours and the dark theme don't
// reach it), and it can only be opened by a real user gesture --
// HTMLSelectElement.showPicker() throws without one, and hovering doesn't
// count. So the native element stays in the DOM as the value holder and
// this draws the visible control on top.
//
// Keeping the real <select> (rather than a hidden input) is what means
// nothing else had to change: form serialization, the `change` event that
// the filter bars' hx-trigger listens for, and constraint validation all
// still see an ordinary select.
(function () {
  const OPEN_DELAY_MS = 110;
  // Longer than the open delay so moving diagonally from the button onto
  // the panel doesn't close it under the pointer.
  const CLOSE_DELAY_MS = 180;

  function labelTextFor(select) {
    if (select.id) {
      const label = document.querySelector(`label[for="${select.id}"]`);
      if (label) return label.textContent.trim();
    }
    return "";
  }

  function enhance(select) {
    if (select.dataset.enhanced || select.multiple) return;
    select.dataset.enhanced = "true";

    const wrap = document.createElement("div");
    wrap.className = "select";
    wrap.dataset.open = "false";
    select.parentNode.insertBefore(wrap, select);

    select.classList.add("select-native");
    select.setAttribute("tabindex", "-1");
    select.setAttribute("aria-hidden", "true");

    const button = document.createElement("button");
    button.type = "button";
    button.className = "select-button";
    button.setAttribute("aria-haspopup", "listbox");
    button.setAttribute("aria-expanded", "false");
    const fieldName = labelTextFor(select);
    if (fieldName) button.setAttribute("aria-label", fieldName);

    const label = document.createElement("span");
    label.className = "select-label";
    const caret = document.createElement("span");
    caret.className = "select-caret";
    caret.setAttribute("aria-hidden", "true");
    button.append(label, caret);

    const panel = document.createElement("ul");
    panel.className = "select-panel";
    panel.setAttribute("role", "listbox");

    const options = Array.from(select.options).map((option, index) => {
      const item = document.createElement("li");
      item.className = "select-option";
      item.setAttribute("role", "option");
      item.dataset.index = String(index);
      item.textContent = option.textContent;
      panel.appendChild(item);
      return item;
    });

    wrap.append(button, panel, select);

    let openTimer = null;
    let closeTimer = null;
    let activeIndex = select.selectedIndex;

    function clearTimers() {
      clearTimeout(openTimer);
      clearTimeout(closeTimer);
    }

    function sync() {
      const selected = select.options[select.selectedIndex];
      label.textContent = selected ? selected.textContent : "";
      options.forEach((item, index) => {
        item.setAttribute("aria-selected", index === select.selectedIndex ? "true" : "false");
      });
    }

    function setActive(index) {
      activeIndex = Math.max(0, Math.min(index, options.length - 1));
      options.forEach((item, i) => item.classList.toggle("is-active", i === activeIndex));
      const active = options[activeIndex];
      if (active && wrap.dataset.open === "true") {
        active.scrollIntoView({ block: "nearest" });
      }
    }

    function open() {
      clearTimers();
      if (wrap.dataset.open === "true") return;
      wrap.dataset.open = "true";
      button.setAttribute("aria-expanded", "true");
      setActive(select.selectedIndex < 0 ? 0 : select.selectedIndex);
    }

    function close() {
      clearTimers();
      wrap.dataset.open = "false";
      button.setAttribute("aria-expanded", "false");
    }

    function choose(index) {
      if (index !== select.selectedIndex) {
        select.selectedIndex = index;
        // What the filter bars' hx-trigger="change" (and any other
        // listener) is waiting for -- setting .value fires nothing.
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      sync();
      close();
      button.focus();
    }

    wrap.addEventListener("mouseenter", () => {
      clearTimers();
      openTimer = setTimeout(open, OPEN_DELAY_MS);
    });
    wrap.addEventListener("mouseleave", () => {
      clearTimers();
      closeTimer = setTimeout(close, CLOSE_DELAY_MS);
    });

    button.addEventListener("click", () => {
      if (wrap.dataset.open === "true") close();
      else open();
    });

    options.forEach((item, index) => {
      item.addEventListener("click", () => choose(index));
      item.addEventListener("mousemove", () => setActive(index));
    });

    wrap.addEventListener("keydown", (event) => {
      const isOpen = wrap.dataset.open === "true";
      if (event.key === "Escape") {
        if (isOpen) {
          event.preventDefault();
          close();
        }
        return;
      }
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (!isOpen) {
          open();
          return;
        }
        setActive(activeIndex + (event.key === "ArrowDown" ? 1 : -1));
        return;
      }
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (isOpen) choose(activeIndex);
        else open();
      }
    });

    button.addEventListener("blur", () => {
      // Only close on a blur that leaves the control entirely; clicking an
      // option moves focus within it.
      setTimeout(() => {
        if (!wrap.contains(document.activeElement)) close();
      }, 0);
    });

    // Anything that changes the value behind our back (form.reset(), other
    // scripts) should still be reflected in the label.
    select.addEventListener("change", sync);
    if (select.form) select.form.addEventListener("reset", () => setTimeout(sync, 0));

    sync();
  }

  function enhanceAll(root) {
    (root || document).querySelectorAll("select:not([data-enhanced])").forEach(enhance);
  }

  document.addEventListener("click", (event) => {
    document.querySelectorAll('.select[data-open="true"]').forEach((wrap) => {
      if (!wrap.contains(event.target)) {
        wrap.dataset.open = "false";
        const button = wrap.querySelector(".select-button");
        if (button) button.setAttribute("aria-expanded", "false");
      }
    });
  });

  document.addEventListener("DOMContentLoaded", () => enhanceAll());
  // htmx can swap in markup containing selects (and will in future even
  // where it doesn't today), so re-scan after every settle.
  document.addEventListener("htmx:afterSettle", (event) => enhanceAll(event.target));
})();
