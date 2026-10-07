// Toast notifications.
//
// Two ways in: base.html renders server-side flash()es into .toast-stack on
// page load, and window.showToast(text) fires one without a round trip (for
// in-place saves, where a full-page flash would need the reload we're
// avoiding). Both end up as the same element, dismissed the same way.
(function () {
  const LIFETIME_MS = 4000;

  function stack() {
    let el = document.querySelector(".toast-stack");
    if (!el) {
      el = document.createElement("div");
      el.className = "toast-stack";
      document.body.appendChild(el);
    }
    return el;
  }

  function dismiss(toast) {
    if (!toast.isConnected) return;
    toast.classList.add("toast-leaving");
    // Matches --t in style.css; removing it only after the fade means the
    // stack doesn't jump as the gap closes.
    setTimeout(() => toast.remove(), 160);
  }

  function wire(toast) {
    const close = toast.querySelector(".toast-close");
    if (close) close.addEventListener("click", () => dismiss(toast));
    setTimeout(() => dismiss(toast), LIFETIME_MS);
  }

  function showToast(text, category) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${category || "success"}`;
    const span = document.createElement("span");
    span.className = "toast-text";
    span.textContent = text;
    const button = document.createElement("button");
    button.className = "toast-close";
    button.type = "button";
    button.setAttribute("aria-label", "Dismiss");
    button.textContent = "×";
    toast.append(span, button);
    stack().appendChild(toast);
    wire(toast);
  }

  window.showToast = showToast;

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".toast-stack .toast").forEach(wire);
  });
})();
