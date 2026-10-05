from datetime import date

from flask import Blueprint, abort, redirect, render_template, request, url_for

from .. import db
from ..docx_utils import docx_bytes_to_markdown
from ..tag_utils import tag_names_as_text as _tag_names_as_text
from ..tag_utils import tag_names_to_ids as _tag_names_to_ids

bp = Blueprint("notes", __name__, url_prefix="/notes")


def _body_from_form(form, files):
    upload = files.get("note_file")
    if upload and upload.filename:
        filename = upload.filename.lower()
        if filename.endswith(".docx"):
            return docx_bytes_to_markdown(upload.read())
        return upload.read().decode("utf-8", errors="replace")
    return form.get("body_markdown", "")


@bp.route("")
def list_view():
    filters = dict(
        note_type_id=request.args.get("type", type=int),
        person_id=request.args.get("person", type=int),
        project_id=request.args.get("project", type=int),
        topic_id=request.args.get("topic", type=int),
        date_from=request.args.get("from") or None,
        date_to=request.args.get("to") or None,
    )
    notes = db.list_notes(**filters)
    return render_template(
        "notes/list.html",
        notes=notes,
        note_types=db.list_note_types(),
        people=db.list_people(),
        projects=db.list_projects(),
        topics=db.list_topics(),
        filters=filters,
    )


@bp.route("/new")
def new_view():
    note_type_id = request.args.get("type", type=int)
    note_type = db.get_note_type(note_type_id) if note_type_id else None
    return render_template(
        "notes/form.html",
        note=None,
        note_type=note_type,
        note_types=db.list_note_types(),
        people_text="",
        projects_text="",
        topics_text="",
        existing_people=db.list_people(),
        existing_projects=db.list_projects(),
        existing_topics=db.list_topics(),
        today=date.today().isoformat(),
    )


@bp.route("", methods=["POST"])
def create_view():
    form = request.form
    body_markdown = _body_from_form(form, request.files)
    note_id = db.create_note(
        title=form["title"],
        note_type_id=int(form["note_type_id"]),
        event_date=form["event_date"],
        body_markdown=body_markdown,
        person_ids=_tag_names_to_ids(form.get("people"), db.find_or_create_person),
        project_ids=_tag_names_to_ids(form.get("projects"), db.find_or_create_project),
        topic_ids=_tag_names_to_ids(form.get("topics"), db.find_or_create_topic),
    )
    db.sync_tasks_from_note(note_id, body_markdown)
    return redirect(url_for("notes.detail_view", note_id=note_id))


@bp.route("/template")
def template_partial():
    note_type_id = request.args.get("note_type_id", type=int)
    note_type = db.get_note_type(note_type_id) if note_type_id else None
    if note_type is None:
        return ""
    return note_type["template_markdown"]


@bp.route("/<int:note_id>")
def detail_view(note_id):
    note = db.get_note(note_id)
    if note is None:
        abort(404)
    tags = db.get_note_tags(note_id)
    linked_tasks = db.tasks_for_note(note_id)
    return render_template(
        "notes/detail.html", note=note, tags=tags, linked_tasks=linked_tasks,
        evidence=db.evidence_for_entity("note", note_id),
        all_skills=db.list_skills(),
        entity_type="note", entity_id=note_id,
    )


@bp.route("/<int:note_id>/edit")
def edit_view(note_id):
    note = db.get_note(note_id)
    if note is None:
        abort(404)
    tags = db.get_note_tags(note_id)
    return render_template(
        "notes/form.html",
        note=note,
        note_type=None,
        note_types=db.list_note_types(include_archived=True),
        people_text=_tag_names_as_text(tags["people"]),
        projects_text=_tag_names_as_text(tags["projects"]),
        topics_text=_tag_names_as_text(tags["topics"]),
        existing_people=db.list_people(),
        existing_projects=db.list_projects(),
        existing_topics=db.list_topics(),
        today=date.today().isoformat(),
    )


@bp.route("/<int:note_id>", methods=["POST"])
def update_view(note_id):
    if db.get_note(note_id) is None:
        abort(404)
    form = request.form
    body_markdown = _body_from_form(form, request.files)
    db.update_note(
        note_id,
        title=form["title"],
        note_type_id=int(form["note_type_id"]),
        event_date=form["event_date"],
        body_markdown=body_markdown,
        person_ids=_tag_names_to_ids(form.get("people"), db.find_or_create_person),
        project_ids=_tag_names_to_ids(form.get("projects"), db.find_or_create_project),
        topic_ids=_tag_names_to_ids(form.get("topics"), db.find_or_create_topic),
    )
    db.sync_tasks_from_note(note_id, body_markdown)
    return redirect(url_for("notes.detail_view", note_id=note_id))


@bp.route("/<int:note_id>/delete", methods=["POST"])
def delete_view(note_id):
    if db.get_note(note_id) is None:
        abort(404)
    db.delete_note(note_id)
    return redirect(url_for("notes.list_view"))
