from urllib.parse import urlparse

from flask import Blueprint, abort, redirect, render_template, request, url_for

from .. import db, htmx

bp = Blueprint("tasks", __name__, url_prefix="/tasks")

STATUSES = ["todo", "in_progress", "blocked", "done"]
PRIORITIES = ["low", "medium", "high"]

# "Now / Next / Later", renamed to match the user's own words: a task is
# either on today's plate, a longer-horizon thing to get to, or parked where
# it won't demand attention. Shared by the Today checklists and the Board
# columns so the two views stay in sync with each other.
BUCKETS = ["today", "long_term", "background"]
BUCKET_LABELS = {"today": "Today", "long_term": "Long term", "background": "In the background"}
# Board keeps a 4th, bucket-less column for finished work.
BOARD_COLUMNS = BUCKETS + ["done"]
BOARD_COLUMN_LABELS = dict(BUCKET_LABELS, done="Done")


def _safe_next(default):
    """Where to go after this edit/delete. Reads `next` from either the
    query string or the form body (request.values covers both) -- a task
    can be edited from Today, Board, a note's or project's linked-tasks
    list, or the dashboard, so (unlike other edit pages in this app) there
    isn't one single sensible page to fall back to. Only accepts an
    internal path (starts with "/"), never an absolute URL."""
    next_url = request.values.get("next")
    if next_url and next_url.startswith("/"):
        return next_url
    return default


def _show_done():
    """Whether the Today page is showing completed tasks. Lives in the
    query string (`?done=1`) rather than a cookie or the `setting` table,
    so the toggle is shareable, reload-safe and back-button-correct for
    free -- the same reasoning as the filter bars' hx-push-url.

    Read from `request.values` rather than `request.args` so the quick-add
    form can carry it in its body too: that POST has no query string, and
    without this, adding a task would re-render the lists with the toggle
    silently reset."""
    return request.values.get("done") == "1"


def _render_checklists(template):
    show_done = _show_done()
    return render_template(
        template,
        buckets=BUCKETS,
        bucket_labels=BUCKET_LABELS,
        tasks_by_bucket={
            bucket: db.list_tasks_by_bucket(bucket, include_done=show_done)
            for bucket in BUCKETS
        },
        show_done=show_done,
    )


@bp.route("")
def today_view():
    return _render_checklists(htmx.template_for("tasks/today.html", "tasks/_checklists.html"))


@bp.route("/board")
def board_view():
    project_id = request.args.get("project", type=int)
    priority = request.args.get("priority") or None
    tasks = db.list_tasks(project_id=project_id, priority=priority)
    columns = {column: [] for column in BOARD_COLUMNS}
    for task in tasks:
        columns["done" if task["status"] == "done" else task["bucket"]].append(task)
    return render_template(
        htmx.template_for("tasks/board.html", "tasks/_board_columns.html"),
        columns=columns,
        board_columns=BOARD_COLUMNS,
        column_labels=BOARD_COLUMN_LABELS,
        projects=db.list_projects(),
        filters=dict(project_id=project_id, priority=priority),
    )


@bp.route("", methods=["POST"])
def quick_add_view():
    title = request.form.get("title", "").strip()
    if title:
        db.create_task(title=title, bucket="today")
    # htmx swaps the re-rendered checklists straight into the page; a plain
    # form post (no JS) still gets the redirect it expects.
    if htmx.is_htmx():
        return _render_checklists("tasks/_checklists.html")
    return redirect(url_for("tasks.today_view"))


@bp.route("/new")
def new_view():
    return render_template(
        "tasks/form.html", task=None, projects=db.list_projects(),
        priorities=PRIORITIES, buckets=BUCKETS, bucket_labels=BUCKET_LABELS,
        next=_safe_next(url_for("tasks.today_view")),
    )


@bp.route("/new", methods=["POST"])
def create_view():
    form = request.form
    title = form.get("title", "").strip()
    if not title:
        abort(400)
    db.create_task(
        title=title,
        description=form.get("description", ""),
        priority=form.get("priority", "medium"),
        due_date=form.get("due_date") or None,
        bucket=form.get("bucket") or "today",
        project_id=form.get("project_id", type=int) or None,
    )
    return redirect(_safe_next(url_for("tasks.today_view")))


@bp.route("/<int:task_id>/toggle", methods=["POST"])
def toggle_view(task_id):
    task = db.get_task(task_id)
    if task is None:
        abort(404)
    new_status = "todo" if task["status"] == "done" else "done"
    db.set_task_status(task_id, new_status)
    task = db.get_task(task_id)
    # This re-renders the row standalone for htmx's swap, so request.full_path
    # would otherwise resolve to this AJAX endpoint itself, not the page the
    # checklist is actually on -- read the real page from the header htmx
    # sends with every request instead.
    current_url = request.headers.get("HX-Current-URL", "")
    parsed = urlparse(current_url)
    next_url = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    next_url = next_url or url_for("tasks.today_view")
    # Only the Today checklist's rows are drag-and-drop; the swapped-in row
    # needs to match whatever the rest of that page's rows look like, or a
    # checked-off task loses its draggable handle until the next reload.
    draggable = next_url == url_for("tasks.today_view")
    return render_template(
        "tasks/_task_row.html", task=task, next_url=next_url, draggable=draggable,
    )


@bp.route("/<int:task_id>/move", methods=["POST"])
def move_view(task_id):
    """One consolidated endpoint for every drag-and-drop move: dragging
    between Today's 3 checklists or Board's bucket columns sends `bucket`;
    dragging a Board card into/out of the Done column sends `status`. A
    single drop can send either or both (there's no case that needs both
    today, but a future one shouldn't need a second endpoint)."""
    if db.get_task(task_id) is None:
        abort(404)
    bucket = request.form.get("bucket")
    status = request.form.get("status")
    if bucket is not None:
        if bucket not in BUCKETS:
            abort(400)
        db.set_task_bucket(task_id, bucket)
    if status is not None:
        if status not in STATUSES:
            abort(400)
        db.set_task_status(task_id, status)
    # `order` is the destination list's ids, in their new order, sent by a
    # drag *within* a list (and alongside `bucket` when one drag does
    # both). Applied last so it wins over the end-of-list position
    # set_task_bucket just assigned.
    order = request.form.get("order")
    if order:
        ids = [int(part) for part in order.split(",") if part.strip().isdigit()]
        # Only ids that really exist, so a hand-crafted list can't renumber
        # arbitrary rows; the task being moved must be among them.
        known = db.existing_task_ids(ids)
        ids = [i for i in ids if i in known]
        if task_id in ids:
            db.set_bucket_order(ids)
    return ("", 204)


@bp.route("/<int:task_id>/edit")
def edit_view(task_id):
    task = db.get_task(task_id)
    if task is None:
        abort(404)
    return render_template(
        "tasks/form.html", task=task, projects=db.list_projects(),
        priorities=PRIORITIES, buckets=BUCKETS, bucket_labels=BUCKET_LABELS,
        evidence=db.evidence_for_entity("task", task_id),
        all_skills=db.list_skills(),
        entity_type="task", entity_id=task_id,
        next=_safe_next(url_for("tasks.today_view")),
    )


@bp.route("/<int:task_id>", methods=["POST"])
def update_view(task_id):
    if db.get_task(task_id) is None:
        abort(404)
    form = request.form
    db.update_task(
        task_id,
        title=form["title"],
        description=form.get("description", ""),
        priority=form["priority"],
        due_date=form.get("due_date") or None,
        bucket=form.get("bucket") or "today",
        project_id=form.get("project_id", type=int) or None,
    )
    return redirect(_safe_next(url_for("tasks.today_view")))


@bp.route("/<int:task_id>/delete", methods=["POST"])
def delete_view(task_id):
    if db.get_task(task_id) is None:
        abort(404)
    db.delete_task(task_id)
    return redirect(_safe_next(url_for("tasks.today_view")))
