// Generic HTML5 drag-and-drop for any page that lays out draggable
// `[data-task-id]` items inside `[data-drop-zone]` containers -- shared by
// the Today checklists (drag between the today/long_term/background
// buckets) and the Board (drag between those same bucket columns and
// Done). A drop zone's `data-bucket`/`data-status` attributes say what to
// POST to `/tasks/<id>/move`; a zone can set either, both, or neither (a
// zone with neither, if one ever exists, is a no-op drop target).
//
// A zone marked `data-reorder` additionally supports dragging *within*
// it: the row follows the pointer live, and the drop sends the zone's
// whole id list as `order` for the server to renumber. Only the Today
// lists set it -- the Board's columns have no manual order, so letting
// cards be shuffled there would promise something the server won't keep.
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

  // Which item the dragged one should land *before*, given the pointer's
  // y position: the first item whose vertical midpoint is below the
  // pointer. Null means "past the last item", i.e. append. Midpoints
  // rather than edges, so the insertion flips as the pointer passes the
  // middle of a row -- which is where it feels like it should.
  function itemToInsertBefore(zone, y) {
    const others = [...zone.querySelectorAll("[data-task-id]")].filter(
      (el) => !el.classList.contains("dragging")
    );
    return others.find((el) => {
      const box = el.getBoundingClientRect();
      return y < box.top + box.height / 2;
    }) || null;
  }

  document.addEventListener("dragover", (event) => {
    const zone = event.target.closest(ZONE);
    if (!zone) return;
    // Both preventDefaults are required: without them the browser refuses
    // the drop and runs its own "navigate to the dragged data" fallback.
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    setActive(zone);

    // Move the dragged row live so the gap opens where it will land --
    // without this, reordering within a list gives no feedback at all
    // until the drop.
    const item = document.querySelector(".dragging");
    if (!item || zone.dataset.reorder === undefined) return;
    const before = itemToInsertBefore(zone, event.clientY);
    if (before !== item.nextElementSibling || item.parentElement !== zone) {
      zone.insertBefore(item, before);
    }
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
    if (!item) return;

    if (zone.dataset.reorder !== undefined) {
      // dragover has already put the row in place; just honour it.
      zone.insertBefore(item, itemToInsertBefore(zone, event.clientY));
      // The whole zone's ids in their new order. Sending the list rather
      // than one index lets the server renumber 1..n, which sidesteps
      // every gap/collision problem a sparse index would bring.
      const order = [...zone.querySelectorAll("[data-task-id]")]
        .map((el) => el.dataset.taskId)
        .join(",");
      if (order) body.set("order", order);
    } else {
      zone.appendChild(item);
    }
    if (!body.toString()) return;

    // An empty list's placeholder row has to go once something lands in
    // it, or it sits there contradicting the list it's inside.
    const placeholder = zone.querySelector(".today-list-empty");
    if (placeholder) placeholder.remove();
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
