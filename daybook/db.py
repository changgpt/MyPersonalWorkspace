"""Thin data-access layer over plain sqlite3.

No ORM: every query here is plain SQL. For a single-user local app this
keeps it obvious what each page actually asks the database for, and makes
the FTS5 search queries (which ORMs handle awkwardly) straightforward.
"""
import sqlite3
from datetime import date, datetime, timedelta, timezone

import click
from flask import current_app, g

from . import config
from .task_extraction import extract_action_items


def get_db():
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db_path = current_app.config["DATABASE_PATH"]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    schema_path = config.BASE_DIR / "daybook" / "schema.sql"
    with open(schema_path, "r") as f:
        db.executescript(f.read())
    db.commit()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command("init-db")
def init_db_command():
    """Create tables if they don't exist yet, then seed default note types."""
    from . import seed

    init_db()
    seed.seed_note_types(get_db())
    click.echo("Database initialised.")


# --- Note types --------------------------------------------------------

def list_note_types(include_archived=False):
    db = get_db()
    query = "SELECT * FROM note_type"
    if not include_archived:
        query += " WHERE is_active = 1"
    query += " ORDER BY name"
    return db.execute(query).fetchall()


def get_note_type(note_type_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM note_type WHERE id = ?", (note_type_id,)
    ).fetchone()


def create_note_type(name, color, template_markdown):
    db = get_db()
    cur = db.execute(
        "INSERT INTO note_type (name, color, template_markdown) VALUES (?, ?, ?)",
        (name, color, template_markdown),
    )
    db.commit()
    return cur.lastrowid


def update_note_type(note_type_id, name, color, template_markdown):
    db = get_db()
    db.execute(
        "UPDATE note_type SET name = ?, color = ?, template_markdown = ? WHERE id = ?",
        (name, color, template_markdown, note_type_id),
    )
    db.commit()


def set_note_type_active(note_type_id, is_active):
    db = get_db()
    db.execute(
        "UPDATE note_type SET is_active = ? WHERE id = ?",
        (1 if is_active else 0, note_type_id),
    )
    db.commit()


# --- Tag-like entities: person / project / topic -----------------------
# These three share the same shape (id, name, ...) and the same
# find-or-create-by-name behaviour used when tagging a note.

def _find_or_create_by_name(table, name):
    db = get_db()
    name = name.strip()
    row = db.execute(
        f"SELECT id FROM {table} WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    if row:
        return row["id"]
    cur = db.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
    db.commit()
    return cur.lastrowid


def find_or_create_person(name):
    return _find_or_create_by_name("person", name)


def find_or_create_project(name):
    return _find_or_create_by_name("project", name)


def find_or_create_topic(name):
    return _find_or_create_by_name("topic", name)


def list_people():
    db = get_db()
    return db.execute("SELECT * FROM person ORDER BY name").fetchall()


def get_person(person_id):
    db = get_db()
    return db.execute("SELECT * FROM person WHERE id = ?", (person_id,)).fetchone()


def list_projects():
    db = get_db()
    return db.execute("SELECT * FROM project ORDER BY name").fetchall()


def get_project(project_id):
    db = get_db()
    return db.execute("SELECT * FROM project WHERE id = ?", (project_id,)).fetchone()


def list_topics():
    db = get_db()
    return db.execute("SELECT * FROM topic ORDER BY name").fetchall()


def get_topic(topic_id):
    db = get_db()
    return db.execute("SELECT * FROM topic WHERE id = ?", (topic_id,)).fetchone()


# --- Notes ---------------------------------------------------------------

def _set_note_tags(note_id, table, column, tag_ids):
    db = get_db()
    db.execute(f"DELETE FROM {table} WHERE note_id = ?", (note_id,))
    db.executemany(
        f"INSERT INTO {table} (note_id, {column}) VALUES (?, ?)",
        [(note_id, tag_id) for tag_id in tag_ids],
    )


def create_note(title, note_type_id, event_date, body_markdown,
                 person_ids=None, project_ids=None, topic_ids=None):
    db = get_db()
    ts = now_iso()
    cur = db.execute(
        """INSERT INTO note (title, note_type_id, event_date, body_markdown,
                              created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (title, note_type_id, event_date, body_markdown, ts, ts),
    )
    note_id = cur.lastrowid
    _set_note_tags(note_id, "note_person", "person_id", person_ids or [])
    _set_note_tags(note_id, "note_project", "project_id", project_ids or [])
    _set_note_tags(note_id, "note_topic", "topic_id", topic_ids or [])
    db.commit()
    return note_id


def update_note(note_id, title, note_type_id, event_date, body_markdown,
                 person_ids=None, project_ids=None, topic_ids=None):
    db = get_db()
    db.execute(
        """UPDATE note SET title = ?, note_type_id = ?, event_date = ?,
                            body_markdown = ?, updated_at = ?
           WHERE id = ?""",
        (title, note_type_id, event_date, body_markdown, now_iso(), note_id),
    )
    _set_note_tags(note_id, "note_person", "person_id", person_ids or [])
    _set_note_tags(note_id, "note_project", "project_id", project_ids or [])
    _set_note_tags(note_id, "note_topic", "topic_id", topic_ids or [])
    db.commit()


def delete_note(note_id):
    db = get_db()
    db.execute("DELETE FROM note WHERE id = ?", (note_id,))
    db.commit()


def get_note(note_id):
    db = get_db()
    return db.execute(
        """SELECT note.*, note_type.name AS type_name, note_type.color AS type_color
           FROM note JOIN note_type ON note_type.id = note.note_type_id
           WHERE note.id = ?""",
        (note_id,),
    ).fetchone()


def get_note_tags(note_id):
    db = get_db()
    people = db.execute(
        """SELECT person.* FROM person
           JOIN note_person ON note_person.person_id = person.id
           WHERE note_person.note_id = ? ORDER BY person.name""",
        (note_id,),
    ).fetchall()
    projects = db.execute(
        """SELECT project.* FROM project
           JOIN note_project ON note_project.project_id = project.id
           WHERE note_project.note_id = ? ORDER BY project.name""",
        (note_id,),
    ).fetchall()
    topics = db.execute(
        """SELECT topic.* FROM topic
           JOIN note_topic ON note_topic.topic_id = topic.id
           WHERE note_topic.note_id = ? ORDER BY topic.name""",
        (note_id,),
    ).fetchall()
    return {"people": people, "projects": projects, "topics": topics}


def list_notes(note_type_id=None, person_id=None, project_id=None,
                topic_id=None, date_from=None, date_to=None):
    db = get_db()
    query = """
        SELECT DISTINCT note.*, note_type.name AS type_name, note_type.color AS type_color
        FROM note
        JOIN note_type ON note_type.id = note.note_type_id
        LEFT JOIN note_person ON note_person.note_id = note.id
        LEFT JOIN note_project ON note_project.note_id = note.id
        LEFT JOIN note_topic ON note_topic.note_id = note.id
        WHERE 1 = 1
    """
    params = []
    if note_type_id:
        query += " AND note.note_type_id = ?"
        params.append(note_type_id)
    if person_id:
        query += " AND note_person.person_id = ?"
        params.append(person_id)
    if project_id:
        query += " AND note_project.project_id = ?"
        params.append(project_id)
    if topic_id:
        query += " AND note_topic.topic_id = ?"
        params.append(topic_id)
    if date_from:
        query += " AND note.event_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND note.event_date <= ?"
        params.append(date_to)
    query += " ORDER BY note.event_date DESC, note.id DESC"
    return db.execute(query, params).fetchall()


def notes_for_person(person_id):
    return list_notes(person_id=person_id)


def notes_for_project(project_id):
    return list_notes(project_id=project_id)


def notes_for_topic(topic_id):
    return list_notes(topic_id=topic_id)


# --- Search ----------------------------------------------------------------

def search_notes(query_text):
    db = get_db()
    if not query_text or not query_text.strip():
        return []
    # FTS5 query syntax treats punctuation specially; wrap each term so a
    # search like "user's" or "api-key" doesn't raise a syntax error.
    terms = query_text.strip().split()
    fts_query = " ".join(f'"{t}"*' for t in terms)
    rows = db.execute(
        """
        SELECT note.id, note.event_date,
               highlight(note_fts, 0, '<mark>', '</mark>') AS title_html,
               snippet(note_fts, 1, '<mark>', '</mark>', '…', 10) AS snippet_html,
               note_type.name AS type_name, note_type.color AS type_color
        FROM note_fts
        JOIN note ON note.id = note_fts.rowid
        JOIN note_type ON note_type.id = note.note_type_id
        WHERE note_fts MATCH ?
        ORDER BY rank
        """,
        (fts_query,),
    ).fetchall()
    return rows


# --- Tasks -----------------------------------------------------------------

def create_task(title, description="", priority="medium", due_date=None,
                 is_today=False, project_id=None, source_note_id=None,
                 source_line_text=None):
    db = get_db()
    cur = db.execute(
        """INSERT INTO task (title, description, priority, due_date, is_today,
                              project_id, source_note_id, source_line_text, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, description, priority, due_date, 1 if is_today else 0,
         project_id, source_note_id, source_line_text, now_iso()),
    )
    db.commit()
    return cur.lastrowid


def update_task(task_id, title, description, priority, due_date, is_today, project_id):
    db = get_db()
    db.execute(
        """UPDATE task SET title = ?, description = ?, priority = ?, due_date = ?,
                            is_today = ?, project_id = ?
           WHERE id = ?""",
        (title, description, priority, due_date, 1 if is_today else 0, project_id, task_id),
    )
    db.commit()


def get_task(task_id):
    db = get_db()
    return db.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()


def delete_task(task_id):
    db = get_db()
    db.execute("DELETE FROM task WHERE id = ?", (task_id,))
    db.commit()


def _sync_note_checkbox(note_id, line_text, checked):
    """Flip "- [ ] <line_text>" to "- [x] <line_text>" (or back) in a note's
    body. No-ops if the line isn't found (e.g. it came from a "TODO:" line,
    which has no checkbox, or was edited/removed since)."""
    db = get_db()
    note = db.execute("SELECT body_markdown FROM note WHERE id = ?", (note_id,)).fetchone()
    if note is None:
        return
    unchecked_line = f"- [ ] {line_text}"
    checked_line = f"- [x] {line_text}"
    old, new = (unchecked_line, checked_line) if checked else (checked_line, unchecked_line)
    if old not in note["body_markdown"]:
        return
    updated_body = note["body_markdown"].replace(old, new, 1)
    db.execute(
        "UPDATE note SET body_markdown = ?, updated_at = ? WHERE id = ?",
        (updated_body, now_iso(), note_id),
    )
    db.commit()


def set_task_status(task_id, status):
    db = get_db()
    task = get_task(task_id)
    completed_at = now_iso() if status == "done" else None
    db.execute(
        "UPDATE task SET status = ?, completed_at = ? WHERE id = ?",
        (status, completed_at, task_id),
    )
    db.commit()
    if task is not None and task["source_note_id"] and task["source_line_text"]:
        _sync_note_checkbox(task["source_note_id"], task["source_line_text"],
                             checked=(status == "done"))


def sync_tasks_from_note(note_id, body_markdown):
    """Create a task for each new action-item line in a note. Safe to call
    on every save: lines already linked to a task (matched by exact text)
    are skipped, so re-saving never creates duplicates."""
    db = get_db()
    existing_texts = {
        row["source_line_text"]
        for row in db.execute(
            "SELECT source_line_text FROM task WHERE source_note_id = ?", (note_id,)
        ).fetchall()
    }
    for text in extract_action_items(body_markdown):
        if text in existing_texts:
            continue
        create_task(title=text, source_note_id=note_id, source_line_text=text)
        existing_texts.add(text)


def tasks_for_note(note_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM task WHERE source_note_id = ? ORDER BY created_at", (note_id,)
    ).fetchall()


def tasks_for_project(project_id):
    db = get_db()
    return db.execute(
        """SELECT * FROM task WHERE project_id = ?
           ORDER BY (status = 'done'), due_date IS NULL, due_date, id""",
        (project_id,),
    ).fetchall()


def list_tasks(status=None, project_id=None, priority=None):
    db = get_db()
    query = "SELECT * FROM task WHERE 1 = 1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    query += " ORDER BY (status = 'done'), due_date IS NULL, due_date, id"
    return db.execute(query, params).fetchall()


def list_today_flagged_tasks():
    """Tasks flagged is_today, not yet done -- used on the Dashboard, kept
    separate from the overdue list there."""
    db = get_db()
    return db.execute(
        """SELECT * FROM task WHERE is_today = 1 AND status != 'done'
           ORDER BY due_date IS NULL, due_date, id"""
    ).fetchall()


def list_today_view_tasks():
    """Tasks for the Today checklist: anything flagged is_today (even if
    already done today, so you can see it ticked off), plus anything
    overdue and not yet done."""
    db = get_db()
    today = date.today().isoformat()
    return db.execute(
        """SELECT * FROM task
           WHERE is_today = 1
              OR (due_date IS NOT NULL AND due_date < ? AND status != 'done')
           ORDER BY (status = 'done'), due_date IS NULL, due_date, id""",
        (today,),
    ).fetchall()


def list_overdue_tasks():
    db = get_db()
    today = date.today().isoformat()
    return db.execute(
        """SELECT * FROM task WHERE due_date IS NOT NULL AND due_date < ?
           AND status != 'done' ORDER BY due_date""",
        (today,),
    ).fetchall()


def list_tasks_completed_this_week():
    db = get_db()
    monday = date.today() - timedelta(days=date.today().weekday())
    return db.execute(
        """SELECT * FROM task WHERE status = 'done' AND completed_at >= ?
           ORDER BY completed_at DESC""",
        (monday.isoformat(),),
    ).fetchall()
