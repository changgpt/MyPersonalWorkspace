import io
import json
import re
import zipfile
from datetime import date

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
)

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


@bp.route("/note-types/<int:note_type_id>/delete", methods=["POST"])
def note_type_delete_view(note_type_id):
    """Delete a note type, but only while nothing is filed under it.

    Every note has a type and there's no "untyped" to fall back to, so a
    type in use can't be deleted without taking its notes with it -- which
    is what Archive is for (it drops the type out of the picker and leaves
    the notes alone). Refusing with that as the suggestion is better than
    either a cascade nobody asked for or a bare FK error.
    """
    note_type = db.get_note_type(note_type_id)
    if note_type is None:
        abort(404)
    in_use = db.notes_using_note_type(note_type_id)
    if in_use:
        flash(
            f"\u201c{note_type['name']}\u201d is still on {in_use} "
            f"note{'s' if in_use != 1 else ''}. Archive it instead.",
            "error",
        )
        return redirect(url_for("settings.note_types_view"))
    db.delete_note_type(note_type_id)
    flash(f"Deleted \u201c{note_type['name']}\u201d.")
    return redirect(url_for("settings.note_types_view"))


def _slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "note"


def _note_to_markdown(note):
    lines = [
        f"# {note['title']}",
        "",
        f"- Type: {note['type_name']}",
        f"- Date: {note['event_date']}",
        f"- People: {', '.join(note['people']) or '—'}",
        f"- Projects: {', '.join(note['projects']) or '—'}",
        f"- Topics: {', '.join(note['topics']) or '—'}",
        "",
        "---",
        "",
        note["body_markdown"],
    ]
    return "\n".join(lines)


@bp.route("/export")
def export_view():
    data = db.export_all_data()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json.dumps(data, indent=2))
        for note in data["notes"]:
            filename = f"notes/{note['event_date']}-{_slugify(note['title'])}-{note['id']}.md"
            zf.writestr(filename, _note_to_markdown(note))
    buffer.seek(0)

    filename = f"daybook-export-{date.today().isoformat()}.zip"
    return send_file(buffer, mimetype="application/zip", as_attachment=True, download_name=filename)
