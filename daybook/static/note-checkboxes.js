// Makes the checkboxes in a rendered note body actually tickable.
//
// pymdownx.tasklist renders "- [ ] foo" as a *disabled* checkbox -- fine
// for a preview, but on the note page it meant the same action items had
// to be listed a second time underneath (as real task rows) just to have
// something clickable, showing every item twice. Instead the note's own
// checkboxes are wired up here, keyed by line text exactly the way
// db._sync_note_checkbox matches them server-side.
//
// Posts to /tasks/<id>/move (which returns 204 and reuses
// db.set_task_status, so ticking here also rewrites "- [ ]" to "- [x]" in
// the stored Markdown) rather than /tasks/<id>/toggle, whose response is
// an HTML row meant for an htmx swap we don't want here.
(function () {
  function init() {
    const body = document.querySelector(".note-body[data-note-tasks]");
    if (!body) return;

    let tasks;
    try {
      tasks = JSON.parse(body.dataset.noteTasks);
    } catch (err) {
      return;
    }

    body.querySelectorAll("li.task-list-item").forEach((item) => {
      const checkbox = item.querySelector('input[type="checkbox"]');
      if (!checkbox) return;
      const task = tasks[item.textContent.trim()];
      if (!task) return;

      checkbox.disabled = false;
      item.classList.toggle("note-task-done", task.done);

      checkbox.addEventListener("change", () => {
        const done = checkbox.checked;
        item.classList.toggle("note-task-done", done);
        fetch(`/tasks/${task.id}/move`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `status=${done ? "done" : "todo"}`,
        }).catch(() => {
          checkbox.checked = !done;
          item.classList.toggle("note-task-done", !done);
          if (window.showToast) {
            window.showToast("Could not save that — refresh and try again.", "error");
          }
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
