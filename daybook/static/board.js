// Native HTML5 drag-and-drop for the task board. No library needed: this
// is the whole interaction (drag a card, drop it on a column, tell the
// server). The move happens optimistically -- if the save fails, we just
// warn and let you refresh to see the real state.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".board-card").forEach((card) => {
    card.addEventListener("dragstart", (event) => {
      event.dataTransfer.setData("text/plain", card.dataset.taskId);
      card.classList.add("dragging");
    });
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
  });

  document.querySelectorAll(".board-column-list").forEach((column) => {
    column.addEventListener("dragover", (event) => event.preventDefault());
    column.addEventListener("drop", (event) => {
      event.preventDefault();
      const taskId = event.dataTransfer.getData("text/plain");
      const card = document.querySelector(`.board-card[data-task-id="${taskId}"]`);
      if (!card) return;

      column.appendChild(card);
      fetch(`/tasks/${taskId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `status=${encodeURIComponent(column.dataset.status)}`,
      }).catch(() => alert("Could not save that move — please refresh and try again."));
    });
  });
});
