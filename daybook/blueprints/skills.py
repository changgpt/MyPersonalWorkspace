from flask import Blueprint, abort, redirect, render_template, request, url_for

from .. import db

bp = Blueprint("skills", __name__, url_prefix="/skills")

CATEGORIES = ["technical", "financial", "communication", "domain"]


@bp.route("")
def list_view():
    return render_template("skills/list.html", skills=db.list_skills())


@bp.route("/new")
def new_view():
    return render_template("skills/form.html", skill=None, categories=CATEGORIES)


@bp.route("", methods=["POST"])
def create_view():
    form = request.form
    skill_id = db.create_skill(
        name=form["name"], category=form["category"],
        level=int(form["level"]), notes=form.get("notes", ""),
    )
    return redirect(url_for("skills.detail_view", skill_id=skill_id))


@bp.route("/<int:skill_id>")
def detail_view(skill_id):
    skill = db.get_skill(skill_id)
    if skill is None:
        abort(404)
    return render_template(
        "skills/detail.html",
        skill=skill,
        evidence=db.evidence_for_skill(skill_id),
        level_history=db.skill_level_history(skill_id),
    )


@bp.route("/<int:skill_id>/edit")
def edit_view(skill_id):
    skill = db.get_skill(skill_id)
    if skill is None:
        abort(404)
    return render_template("skills/form.html", skill=skill, categories=CATEGORIES)


@bp.route("/<int:skill_id>", methods=["POST"])
def update_view(skill_id):
    if db.get_skill(skill_id) is None:
        abort(404)
    form = request.form
    db.update_skill(
        skill_id, name=form["name"], category=form["category"],
        notes=form.get("notes", ""), level=int(form["level"]),
    )
    return redirect(url_for("skills.detail_view", skill_id=skill_id))


@bp.route("/evidence", methods=["POST"])
def add_evidence_view():
    """Generic "tag skill used/learned" endpoint, posted to from a note,
    task, log entry, or win page (see templates/skills/_tagger.html)."""
    form = request.form
    skill_name = form.get("skill_name", "").strip()
    if skill_name:
        db.add_skill_evidence(
            skill_name=skill_name,
            entity_type=form["entity_type"],
            entity_id=int(form["entity_id"]),
            comment=form.get("comment", ""),
        )
    return redirect(request.referrer or url_for("skills.list_view"))
