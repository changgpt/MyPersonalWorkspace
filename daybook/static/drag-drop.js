// Generic HTML5 drag-and-drop for any page that lays out draggable
// `[data-task-id]` items inside `[data-drop-zone]` containers -- shared by
// the Today checklists (drag between the today/long_term/background
// buckets) and the Board (drag between those same bucket columns and
// Done). A drop zone's `data-bucket`/`data-status` attributes say what to
// POST to `/tasks/<id>/move`; a zone can set either, both, or neither (a
// zone with neither, if one ever exists, is a no-op drop target).
//
// Every listener is delegated to `document` -- including dragover/drop,
// which bubble -- rather than bound to the zones found at load time. That
// matters because htmx swaps whole checklists/columns in place (a filter
// change, a quick-add), and anything bound per-zone would silently stop
// working on the replacement markup.
(function () {
  const ZONE = "[data-drop-zone]";
  let activeZone = null;

  function setActive(zone) {
    if (activeZone === zone) return;
    if (activeZone) activeZone.classList.remove("drop-active");
    activeZone = zone;
    if (activeZone) activeZone.classList.add("drop-active");
  }

  document.addEventListener("dragstart", (event) => {
    const item = event.target.closest("[data-task-id]");
    if (!item) return;
    event.dataTransfer.setData("text/plain", item.dataset.taskId);
    event.dataTransfer.effectAllowed = "move";
    item.classList.add("dragging");
  });

  document.addEventListener("dragend", (event) => {
    const item = event.target.closest("[data-task-id]");
    if (item) item.classList.remove("dragging");
    setActive(null);
  });

  document.addEventListener("dragover", (event) => {
    const zone = event.target.closest(ZONE);
    if (!zone) return;
    // Both preventDefaults are required: without them the browser refuses
    // the drop and runs its own "navigate to the dragged data" fallback.
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    setActive(zone);
  });

  document.addEventListener("dragleave", (event) => {
    const zone = event.target.closest(ZONE);
    // Ignore leaving a child element inside the same zone; only clear when
    // the pointer has actually left the zone itself.
    if (zone && zone === activeZone && !zone.contains(event.relatedTarget)) {
      setActive(null);
    }
  });

  document.addEventListener("drop", (event) => {
    const zone = event.target.closest(ZONE);
    if (!zone) return;
    event.preventDefault();
    setActive(null);

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
    }).catch(() => {
      if (window.showToast) {
        window.showToast("Could not save that move — refresh and try again.", "error");
      }
    });
  });
})();
