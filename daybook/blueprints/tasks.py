from urllib.parse import urlparse

from flask import Blueprint, abort, redirect, render_template, request, url_for

from .. import db

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


@bp.route("")
def today_view():
    return render_template(
        "tasks/today.html",
        buckets=BUCKETS,
        bucket_labels=BUCKET_LABELS,
        tasks_by_bucket={bucket: db.list_tasks_by_bucket(bucket) for bucket in BUCKETS},
    )


@bp.route("/board")
def board_view():
    project_id = request.args.get("project", type=int)
    priority = request.args.get("priority") or None
    tasks = db.list_tasks(project_id=project_id, priority=priority)
    columns = {column: [] for column in BOARD_COLUMNS}
    for task in tasks:
        columns["done" if task["status"] == "done" else task["bucket"]].append(task)
    return render_template(
        "tasks/board.html",
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
