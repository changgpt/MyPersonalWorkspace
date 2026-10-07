from flask import Blueprint, abort, redirect, render_template, request, url_for

from .. import db

bp = Blueprint("people", __name__, url_prefix="/people")


@bp.route("")
def list_view():
    return render_template("people/list.html", people=db.list_people())


@bp.route("/<int:person_id>")
def detail_view(person_id):
    person = db.get_person(person_id)
    if person is None:
        abort(404)
    notes = db.notes_for_person(person_id)
    return render_template("people/detail.html", person=person, notes=notes)


@bp.route("/<int:person_id>/edit")
def edit_view(person_id):
    person = db.get_person(person_id)
    if person is None:
        abort(404)
    return render_template("people/form.html", person=person)


@bp.route("/<int:person_id>", methods=["POST"])
def update_view(person_id):
    if db.get_person(person_id) is None:
        abort(404)
    form = request.form
    db.update_person(
        person_id,
        name=form["name"].strip(),
        role=form.get("role", "").strip(),
        team=form.get("team", "").strip(),
        how_met=form.get("how_met", "").strip(),
        context=form.get("context", "").strip(),
        last_contacted_date=form.get("last_contacted_date") or None,
        follow_up=form.get("follow_up", "").strip(),
    )
    return redirect(url_for("people.detail_view", person_id=person_id))
