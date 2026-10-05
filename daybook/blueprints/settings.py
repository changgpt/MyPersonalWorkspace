from flask import Blueprint, abort, redirect, render_template, request, url_for

from .. import ai, db

bp = Blueprint("settings", __name__, url_prefix="/settings")

NOTE_TYPE_COLORS = ["clay", "sage", "ochre", "dustyblue", "plum", "slate", "moss", "rose"]


@bp.route("/note-types")
def note_types_view():
    return render_template(
        "settings/note_types.html",
        note_types=db.list_note_types(include_archived=True),
        ai_api_key_configured=ai.api_key_configured(),
        ai_enabled=ai.is_ai_enabled(),
    )


@bp.route("/ai-toggle", methods=["POST"])
def ai_toggle_view():
    db.set_setting("ai_features_enabled", "1" if request.form.get("enabled") else "0")
    return redirect(url_for("settings.note_types_view"))


@bp.route("/note-types/new")
def note_type_new_view():
    return render_template(
        "settings/note_type_form.html", note_type=None, colors=NOTE_TYPE_COLORS
    )


@bp.route("/note-types", methods=["POST"])
def note_type_create_view():
    form = request.form
    db.create_note_type(form["name"], form["color"], form.get("template_markdown", ""))
    return redirect(url_for("settings.note_types_view"))


@bp.route("/note-types/<int:note_type_id>/edit")
def note_type_edit_view(note_type_id):
    note_type = db.get_note_type(note_type_id)
    if note_type is None:
        abort(404)
    return render_template(
        "settings/note_type_form.html", note_type=note_type, colors=NOTE_TYPE_COLORS
    )


@bp.route("/note-types/<int:note_type_id>", methods=["POST"])
def note_type_update_view(note_type_id):
    if db.get_note_type(note_type_id) is None:
        abort(404)
    form = request.form
    db.update_note_type(
        note_type_id, form["name"], form["color"], form.get("template_markdown", "")
    )
    return redirect(url_for("settings.note_types_view"))


@bp.route("/note-types/<int:note_type_id>/archive", methods=["POST"])
def note_type_archive_view(note_type_id):
    if db.get_note_type(note_type_id) is None:
        abort(404)
    db.set_note_type_active(note_type_id, is_active=False)
    return redirect(url_for("settings.note_types_view"))


@bp.route("/note-types/<int:note_type_id>/activate", methods=["POST"])
def note_type_activate_view(note_type_id):
    if db.get_note_type(note_type_id) is None:
        abort(404)
    db.set_note_type_active(note_type_id, is_active=True)
    return redirect(url_for("settings.note_types_view"))
