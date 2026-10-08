// Turns a date input inside [data-date-chip] into a friendly chip: the
// label reads "Today" / "Tomorrow" / "12 Oct" instead of 10/08/2026, and
// clicking it hands over to the browser's own date control.
//
// The real <input type="date"> stays in the DOM, named, required and
// validated -- it is only visually swapped for the label, never replaced.
// A browser will not render a custom format in a date input (that's the
// platform's call, which is why dates are ISO there by convention), so a
// label is the only way to show "Today" without giving up native input.
(function () {
  // Deliberately only the cases that actually come up on this screen.
  // date_utils.human_date on the server is richer (it knows about the
  // surrounding week and the year); duplicating all of it here would be
  // two implementations to keep in step, so this covers the three
  // relative days and falls back to a plain "12 Oct" / "12 Oct 2027".
  function label(value) {
    if (!value) return "Pick a date";
    const parts = value.split("-").map(Number);
    if (parts.length !== 3 || parts.some(Number.isNaN)) return value;
    const [y, m, d] = parts;
    const date = new Date(y, m - 1, d);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const days = Math.round((date - today) / 86400000);
    if (days === 0) return "Today";
    if (days === 1) return "Tomorrow";
    if (days === -1) return "Yesterday";
    const month = date.toLocaleString("en-GB", { month: "short" });
    return y === today.getFullYear() ? `${d} ${month}` : `${d} ${month} ${y}`;
  }

  function open(chip, input) {
    chip.dataset.editing = "true";
    // Collapsed, the input is off-screen, so it carries tabindex="-1" in
    // the markup -- tabbing onto an invisible date field is worse than
    // not reaching it at all. While editing it's a real control again.
    input.removeAttribute("tabindex");
    input.focus();
    // showPicker throws without a user gesture; this only ever runs from a
    // click, and older browsers just get a focused input instead.
    try {
      input.showPicker();
    } catch (err) {
      /* no picker available -- the focused input is still usable */
    }
  }

  function close(chip, input, button) {
    delete chip.dataset.editing;
    input.setAttribute("tabindex", "-1");
    button.textContent = label(input.value);
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-date-chip]").forEach((chip) => {
      const input = chip.querySelector('input[type="date"]');
      const button = chip.querySelector("[data-date-chip-label]");
      if (!input || !button) return;

      button.textContent = label(input.value);
      button.addEventListener("click", () => open(chip, input));
      input.addEventListener("change", () => close(chip, input, button));
      // Tabbing or clicking away ends the edit too, so the chip can't be
      // left showing a bare date input.
      input.addEventListener("blur", () => close(chip, input, button));
      // Enter/Escape close the chip -- but note that while the native
      // picker is open those keys belong to the *picker* (Enter there
      // re-selects whatever it has highlighted, which is usually today),
      // and this handler never sees them. That's the platform's call and
      // not worth fighting; the `change` and `blur` listeners above are
      // what actually guarantee the chip closes with the right label.
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === "Escape") {
          event.preventDefault();
          close(chip, input, button);
          button.focus();
        }
      });
    });
  });
})();
