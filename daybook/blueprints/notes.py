from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .. import ai, db, htmx, task_extraction
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
    # Type-grouped by default: a flat reverse-chronological wall of cards
    # has no structure to scan, whereas "all the 1:1s, then all the
    # meetings" does. Newest-first is still one click away.
    sort = request.args.get("sort") or "type"
    notes = db.list_notes(sort=sort, **filters)
    return render_template(
        htmx.template_for("notes/list.html", "notes/_grid.html"),
        notes=notes,
        note_groups=_group_by_type(notes) if sort == "type" else None,
        note_types=db.list_note_types(),
        people=db.list_people(),
        projects=db.list_projects(),
        topics=db.list_topics(),
        filters=filters,
        sort=sort,
    )


def _group_by_type(notes):
    """Notes as `[(type_name, type_color, [note, ...]), ...]`.

    Grouped in Python off an already type-ordered query rather than with a
    GROUP BY: the template needs the whole row for each card anyway, so one
    pass over the result set is simpler than a second query per type (the
    same reasoning as `db.list_activity`'s Python-side merge).
    """
    groups = []
    for note in notes:
        if not groups or groups[-1][0] != note["type_name"]:
            groups.append((note["type_name"], note["type_color"], []))
        groups[-1][2].append(note)
    return groups


@bp.route("/new")
def new_view():
    note_type_id = request.args.get("type", type=int)
    note_type = db.get_note_type(note_type_id) if note_type_id else None
    # Prefill, used by the Dashboard's "Coming up" card so "Take notes" on
    # a meeting opens a note already about it (see calendar_utils.
    # note_prefill). Nothing is created until the form is submitted, so
    # these are only ever defaults in the fields -- a stray query param
    # can't write anything.
    return render_template(
        "notes/form.html",
        note=None,
        note_type=note_type,
        note_types=db.list_note_types(),
        prefill_title=request.args.get("title", ""),
        people_text=request.args.get("people", ""),
        projects_text=request.args.get("projects", ""),
        topics_text="",
        existing_people=db.list_people(),
        existing_projects=db.list_projects(),
        existing_topics=db.list_topics(),
        today=_safe_iso_date(request.args.get("date")),
    )


def _safe_iso_date(value):
    """A prefilled date has to be valid ISO or the browser's date input
    silently renders blank; fall back to today rather than trusting it."""
    try:
        return date.fromisoformat(value).isoformat() if value else date.today().isoformat()
    except ValueError:
        return date.today().isoformat()


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




@bp.route("/<int:note_id>")
def detail_view(note_id):
    note = db.get_note(note_id)
    if note is None:
        abort(404)
    tags = db.get_note_tags(note_id)
    # A task extracted from a "- [ ]" line is already on screen as a
    # checkbox in the rendered body, so listing it again under "Linked
    # tasks" showed the same item twice. Those checkboxes are made live by
    # static/note-checkboxes.js (keyed on this map); only tasks with no
    # checkbox of their own ("TODO:" lines, AI-suggested ones) still need
    # a row below the note.
    checkbox_texts = set(task_extraction.checkbox_line_texts(note["body_markdown"]))
    body_tasks, linked_tasks = {}, []
    for task in db.tasks_for_note(note_id):
        if task["source_line_text"] in checkbox_texts:
            body_tasks[task["source_line_text"]] = {
                "id": task["id"],
                "done": task["status"] == "done",
            }
        else:
            linked_tasks.append(task)
    return render_template(
        "notes/detail.html", note=note, tags=tags, linked_tasks=linked_tasks,
        body_tasks=body_tasks,
        evidence=db.evidence_for_entity("note", note_id),
        all_skills=db.list_skills(),
        entity_type="note", entity_id=note_id,
        ai_enabled=ai.is_ai_enabled(),
    )


@bp.route("/<int:note_id>/ai-summary", methods=["POST"])
def ai_summarize_view(note_id):
    note = db.get_note(note_id)
    if note is None:
        abort(404)
    try:
        summary = ai.summarize_note(note["body_markdown"])
        db.save_note_ai_summary(note_id, summary)
    except ai.AIError as exc:
        flash(str(exc))
    return redirect(url_for("notes.detail_view", note_id=note_id))


@bp.route("/<int:note_id>/ai-suggest-tasks")
def ai_suggest_tasks_view(note_id):
    note = db.get_note(note_id)
    if note is None:
        abort(404)
    try:
        items = ai.suggest_action_items(note["body_markdown"])
    except ai.AIError as exc:
        flash(str(exc))
        return redirect(url_for("notes.detail_view", note_id=note_id))
    return render_template("notes/ai_suggest_tasks.html", note=note, items=items)


@bp.route("/<int:note_id>/ai-suggest-tasks", methods=["POST"])
def ai_suggest_tasks_apply_view(note_id):
    if db.get_note(note_id) is None:
        abort(404)
    for title in request.form.getlist("items"):
        db.create_task(title=title, source_note_id=note_id)
    return redirect(url_for("notes.detail_view", note_id=note_id))


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
