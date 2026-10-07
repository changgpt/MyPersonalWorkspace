// Generic HTML5 drag-and-drop for any page that lays out draggable
// `[data-task-id]` items inside `[data-drop-zone]` containers -- shared by
// the Today checklists (drag between the today/long_term/background
// buckets) and the Board (drag between those same bucket columns and
// Done). A drop zone's `data-bucket`/`data-status` attributes say what to
// POST to `/tasks/<id>/move`; a zone can set either, both, or neither (a
// zone with neither, if one ever exists, is a no-op drop target).
//
// Listeners are delegated to `document`/each zone rather than bound per
// card, so a card that htmx swaps back in (e.g. the Today checklist's
// checkbox toggle re-renders its own <li>) stays draggable without this
// script needing to re-scan the DOM.
document.addEventListener("DOMContentLoaded", () => {
  const zones = document.querySelectorAll("[data-drop-zone]");
  if (!zones.length) return;

  document.addEventListener("dragstart", (event) => {
    const item = event.target.closest("[data-task-id]");
    if (!item) return;
    event.dataTransfer.setData("text/plain", item.dataset.taskId);
    item.classList.add("dragging");
  });

  document.addEventListener("dragend", (event) => {
    const item = event.target.closest("[data-task-id]");
    if (item) item.classList.remove("dragging");
  });

  zones.forEach((zone) => {
    zone.addEventListener("dragover", (event) => event.preventDefault());
    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      const taskId = event.dataTransfer.getData("text/plain");
      const item = document.querySelector(`[data-task-id="${taskId}"]`);
      const body = new URLSearchParams();
      if (zone.dataset.bucket) body.set("bucket", zone.dataset.bucket);
      if (zone.dataset.status) body.set("status", zone.dataset.status);
      if (!item || !body.toString()) return;

      zone.appendChild(item);
      fetch(`/tasks/${taskId}/move`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      }).catch(() => alert("Could not save that move — please refresh and try again."));
    });
  });
});
