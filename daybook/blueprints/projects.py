from flask import Blueprint, abort, render_template

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
    return render_template("projects/detail.html", project=project, notes=notes)
