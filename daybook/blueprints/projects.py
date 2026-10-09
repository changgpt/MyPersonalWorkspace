from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .. import db

bp = Blueprint("projects", __name__, url_prefix="/projects")


@bp.route("")
def list_view():
    return render_template("projects/list.html", projects=db.list_projects())


@bp.route("/new", methods=["POST"])
def create_view():
    """Add a project directly, the same way People works.

    Projects could only appear by being tagged on a note, which left no
    way to file a task under one before you'd written anything about it --
    and the task form's Project picker had nothing to pick. Goes through
    `find_or_create_project`, so a name that already exists opens that
    project instead of duplicating it. The optional `next` is what lets
    the task form create one without navigating away.
    """
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("projects.list_view"))
    project_id = db.find_or_create_project(name)
    if request.accept_mimetypes.best == "application/json":
        return {"id": project_id, "name": db.get_project(project_id)["name"]}
    return redirect(url_for("projects.detail_view", project_id=project_id))


@bp.route("/<int:project_id>")
def detail_view(project_id):
    project = db.get_project(project_id)
    if project is None:
        abort(404)
    notes = db.notes_for_project(project_id)
    tasks = db.tasks_for_project(project_id)
    return render_template("projects/detail.html", project=project, notes=notes, tasks=tasks)


@bp.route("/<int:project_id>/delete", methods=["POST"])
def delete_view(project_id):
    project = db.get_project(project_id)
    if project is None:
        abort(404)
    db.delete_project(project_id)
    flash(f"Deleted {project['name']}.")
    return redirect(url_for("projects.list_view"))
