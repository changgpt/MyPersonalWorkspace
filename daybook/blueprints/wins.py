from datetime import date

from flask import Blueprint, Response, abort, redirect, render_template, request, url_for

from .. import db
from ..tag_utils import tag_names_as_text, tag_names_to_ids

bp = Blueprint("wins", __name__, url_prefix="/wins")


@bp.route("")
def list_view():
    project_id = request.args.get("project", type=int)
    return render_template(
        "wins/list.html",
        wins=db.list_wins(project_id=project_id),
        projects=db.list_projects(),
        filters=dict(project_id=project_id),
    )


@bp.route("/new")
def new_view():
    source_task = None
    task_id = request.args.get("task_id", type=int)
    if task_id:
        source_task = db.get_task(task_id)
    return render_template(
        "wins/form.html",
        win=None,
        source_task=source_task,
        people_text="",
        existing_people=db.list_people(),
        projects=db.list_projects(),
        today=date.today().isoformat(),
    )


@bp.route("", methods=["POST"])
def create_view():
    form = request.form
    win_id = db.create_win(
        win_date=form["win_date"],
        title=form["title"],
        what_i_did=form.get("what_i_did", ""),
        impact_result=form.get("impact_result", ""),
        project_id=form.get("project_id", type=int) or None,
        source_task_id=form.get("source_task_id", type=int) or None,
        person_ids=tag_names_to_ids(form.get("people"), db.find_or_create_person),
    )
    return redirect(url_for("wins.detail_view", win_id=win_id))


@bp.route("/<int:win_id>")
def detail_view(win_id):
    win = db.get_win(win_id)
    if win is None:
        abort(404)
    return render_template(
        "wins/detail.html",
        win=win,
        people=db.people_for_win(win_id),
        evidence=db.evidence_for_entity("win", win_id),
        all_skills=db.list_skills(),
        entity_type="win",
        entity_id=win_id,
    )


@bp.route("/<int:win_id>/edit")
def edit_view(win_id):
    win = db.get_win(win_id)
    if win is None:
        abort(404)
    return render_template(
        "wins/form.html",
        win=win,
        source_task=None,
        people_text=tag_names_as_text(db.people_for_win(win_id)),
        existing_people=db.list_people(),
        projects=db.list_projects(),
        today=date.today().isoformat(),
    )


@bp.route("/<int:win_id>", methods=["POST"])
def update_view(win_id):
    if db.get_win(win_id) is None:
        abort(404)
    form = request.form
    db.update_win(
        win_id,
        win_date=form["win_date"],
        title=form["title"],
        what_i_did=form.get("what_i_did", ""),
        impact_result=form.get("impact_result", ""),
        project_id=form.get("project_id", type=int) or None,
        person_ids=tag_names_to_ids(form.get("people"), db.find_or_create_person),
    )
    return redirect(url_for("wins.detail_view", win_id=win_id))


@bp.route("/<int:win_id>/delete", methods=["POST"])
def delete_view(win_id):
    if db.get_win(win_id) is None:
        abort(404)
    db.delete_win(win_id)
    return redirect(url_for("wins.list_view"))


@bp.route("/export")
def export_view():
    lines = ["# Wins\n"]
    for win in db.list_wins():
        lines.append(f"## {win['title']} ({win['win_date']})\n")
        if win["what_i_did"]:
            lines.append(f"**What I did:** {win['what_i_did']}\n")
        if win["impact_result"]:
            lines.append(f"**Impact:** {win['impact_result']}\n")
        people = db.people_for_win(win["id"])
        if people:
            lines.append(f"**People:** {', '.join(p['name'] for p in people)}\n")
        lines.append("")
    markdown_text = "\n".join(lines)
    return Response(
        markdown_text,
        mimetype="text/markdown",
        headers={"Content-Disposition": "attachment; filename=wins.md"},
    )
