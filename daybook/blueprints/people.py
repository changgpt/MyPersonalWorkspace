from flask import Blueprint, abort, redirect, render_template, request, url_for

from .. import db

bp = Blueprint("people", __name__, url_prefix="/people")


@bp.route("")
def list_view():
    return render_template("people/list.html", people=db.list_people())


@bp.route("/new", methods=["POST"])
def create_view():
    """Add a person directly, from the People page.

    Until now people could *only* appear by being tagged on a note, which
    matched the tag-entity pattern but meant there was no way to note down
    someone you'd just met before you'd written anything about them. Goes
    through `find_or_create_person` rather than a plain INSERT, so typing a
    name that already exists opens that person instead of creating a
    duplicate -- the same case-insensitive match the note tag field uses.
    """
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("people.list_view"))
    person_id = db.find_or_create_person(name)
    # Straight to their page: the point of adding someone by hand is
    # usually to fill in the rest (role, team, how you met) next.
    return redirect(url_for("people.edit_view", person_id=person_id))


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
