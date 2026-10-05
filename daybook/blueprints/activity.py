from flask import Blueprint, abort, redirect, render_template, request, url_for

from .. import db

bp = Blueprint("activity", __name__, url_prefix="/activity")


@bp.route("")
def list_view():
    project_id = request.args.get("project", type=int)
    date_from = request.args.get("from") or None
    date_to = request.args.get("to") or None
    return render_template(
        "activity/list.html",
        items=db.list_activity(date_from=date_from, date_to=date_to, project_id=project_id),
        projects=db.list_projects(),
        filters=dict(project_id=project_id, date_from=date_from, date_to=date_to),
    )


@bp.route("", methods=["POST"])
def create_view():
    form = request.form
    db.create_log_entry(
        entry_date=form["entry_date"],
        description=form["description"],
        project_id=form.get("project_id", type=int) or None,
        time_spent=form.get("time_spent") or None,
    )
    return redirect(url_for("activity.list_view"))


@bp.route("/<int:log_entry_id>/edit")
def log_entry_edit_view(log_entry_id):
    log_entry = db.get_log_entry(log_entry_id)
    if log_entry is None:
        abort(404)
    return render_template(
        "activity/log_entry_form.html",
        log_entry=log_entry,
        projects=db.list_projects(),
        evidence=db.evidence_for_entity("log_entry", log_entry_id),
        all_skills=db.list_skills(),
        entity_type="log_entry", entity_id=log_entry_id,
    )


@bp.route("/<int:log_entry_id>", methods=["POST"])
def log_entry_update_view(log_entry_id):
    if db.get_log_entry(log_entry_id) is None:
        abort(404)
    form = request.form
    db.update_log_entry(
        log_entry_id,
        entry_date=form["entry_date"],
        description=form["description"],
        project_id=form.get("project_id", type=int) or None,
        time_spent=form.get("time_spent") or None,
    )
    return redirect(url_for("activity.list_view"))


@bp.route("/<int:log_entry_id>/delete", methods=["POST"])
def log_entry_delete_view(log_entry_id):
    if db.get_log_entry(log_entry_id) is None:
        abort(404)
    db.delete_log_entry(log_entry_id)
    return redirect(url_for("activity.list_view"))
