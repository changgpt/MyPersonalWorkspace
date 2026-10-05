from flask import Blueprint, abort, render_template

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
