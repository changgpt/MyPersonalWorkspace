from flask import Blueprint, abort, redirect, render_template, request, url_for

from .. import db

bp = Blueprint("tasks", __name__, url_prefix="/tasks")

STATUSES = ["todo", "in_progress", "blocked", "done"]
PRIORITIES = ["low", "medium", "high"]


@bp.route("")
def today_view():
    return render_template("tasks/today.html", tasks=db.list_today_view_tasks())


@bp.route("/board")
def board_view():
    project_id = request.args.get("project", type=int)
    priority = request.args.get("priority") or None
    tasks = db.list_tasks(project_id=project_id, priority=priority)
    columns = {status: [] for status in STATUSES}
    for task in tasks:
        columns[task["status"]].append(task)
    return render_template(
        "tasks/board.html",
        columns=columns,
        statuses=STATUSES,
        projects=db.list_projects(),
        filters=dict(project_id=project_id, priority=priority),
    )


@bp.route("", methods=["POST"])
def quick_add_view():
    title = request.form.get("title", "").strip()
    if title:
        db.create_task(title=title, is_today=True)
    return redirect(url_for("tasks.today_view"))


@bp.route("/<int:task_id>/toggle", methods=["POST"])
def toggle_view(task_id):
    task = db.get_task(task_id)
    if task is None:
        abort(404)
    new_status = "todo" if task["status"] == "done" else "done"
    db.set_task_status(task_id, new_status)
    task = db.get_task(task_id)
    return render_template("tasks/_task_row.html", task=task)


@bp.route("/<int:task_id>/status", methods=["POST"])
def status_view(task_id):
    if db.get_task(task_id) is None:
        abort(404)
    status = request.form.get("status")
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
        priorities=PRIORITIES,
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
        is_today=bool(form.get("is_today")),
        project_id=form.get("project_id", type=int) or None,
    )
    return redirect(request.referrer or url_for("tasks.today_view"))


@bp.route("/<int:task_id>/delete", methods=["POST"])
def delete_view(task_id):
    if db.get_task(task_id) is None:
        abort(404)
    db.delete_task(task_id)
    return redirect(request.referrer or url_for("tasks.today_view"))
