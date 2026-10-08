from flask import Blueprint, abort, flash, redirect, render_template, url_for

from .. import db

bp = Blueprint("projects", __name__, url_prefix="/projects")


@bp.route("")
def list_view():
    return render_template("projects/list.html", projects=db.list_projects())


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
