"""Thin data-access layer over plain sqlite3.

No ORM: every query here is plain SQL. For a single-user local app this
keeps it obvious what each page actually asks the database for, and makes
the FTS5 search queries (which ORMs handle awkwardly) straightforward.
"""
import shutil
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
    _add_column_if_missing(db, "note", "ai_summary", "TEXT")
    db.commit()


def _add_column_if_missing(db, table, column, column_type):
    """CREATE TABLE IF NOT EXISTS in schema.sql only helps brand-new
    databases -- it can't add a column to a table that already exists from
    an earlier phase. This covers that case so `flask init-db` stays
    idempotent and safe to re-run after a schema change."""
    existing_columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
    if column not in existing_columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(backup_db_command)


@click.command("init-db")
def init_db_command():
    """Create tables if they don't exist yet, then seed default note types."""
    from . import seed

    init_db()
    seed.seed_note_types(get_db())
    seed.migrate_default_templates(get_db())
    click.echo("Database initialised.")


@click.command("backup-db")
def backup_db_command():
    """Copy the SQLite file to data/backups/daybook-<timestamp>.db."""
    db_path = current_app.config["DATABASE_PATH"]
    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backups_dir / f"daybook-{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    click.echo(f"Backed up to {backup_path}")


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

def _set_join_rows(entity_id, table, entity_column, tag_column, tag_ids):
    """Replace every row in a join table (note_person, win_person, ...) for
    one entity. Shared by notes and wins, which both tag people/projects."""
    db = get_db()
    db.execute(f"DELETE FROM {table} WHERE {entity_column} = ?", (entity_id,))
    db.executemany(
        f"INSERT INTO {table} ({entity_column}, {tag_column}) VALUES (?, ?)",
        [(entity_id, tag_id) for tag_id in tag_ids],
    )


def _set_note_tags(note_id, table, column, tag_ids):
    _set_join_rows(note_id, table, "note_id", column, tag_ids)


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

# Priority isn't alphabetically sortable (high/low/medium would put "high"
# before "low" before "medium") -- this maps each to a rank so ORDER BY can
# sort high-to-low. Shared by every query that lists active tasks.
_PRIORITY_RANK_SQL = "CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 ELSE 3 END"


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
        f"""SELECT * FROM task WHERE project_id = ?
            ORDER BY (status = 'done'), {_PRIORITY_RANK_SQL}, due_date IS NULL, due_date, id""",
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
    query += f" ORDER BY (status = 'done'), {_PRIORITY_RANK_SQL}, due_date IS NULL, due_date, id"
    return db.execute(query, params).fetchall()


def list_today_flagged_tasks():
    """Tasks flagged is_today, not yet done -- used on the Dashboard, kept
    separate from the overdue list there."""
    db = get_db()
    return db.execute(
        f"""SELECT * FROM task WHERE is_today = 1 AND status != 'done'
            ORDER BY {_PRIORITY_RANK_SQL}, due_date IS NULL, due_date, id"""
    ).fetchall()


def list_today_view_tasks():
    """Tasks for the Today checklist: anything flagged is_today (even if
    already done today, so you can see it ticked off), plus anything
    overdue and not yet done."""
    db = get_db()
    today = date.today().isoformat()
    return db.execute(
        f"""SELECT * FROM task
            WHERE is_today = 1
               OR (due_date IS NOT NULL AND due_date < ? AND status != 'done')
            ORDER BY (status = 'done'), {_PRIORITY_RANK_SQL}, due_date IS NULL, due_date, id""",
        (today,),
    ).fetchall()


def list_overdue_tasks():
    db = get_db()
    today = date.today().isoformat()
    return db.execute(
        f"""SELECT * FROM task WHERE due_date IS NOT NULL AND due_date < ?
            AND status != 'done' ORDER BY {_PRIORITY_RANK_SQL}, due_date""",
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


# --- Skills ------------------------------------------------------------

def create_skill(name, category="technical", level=1, notes=""):
    db = get_db()
    cur = db.execute(
        "INSERT INTO skill (name, category, level, notes, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, category, level, notes, now_iso()),
    )
    skill_id = cur.lastrowid
    db.execute(
        "INSERT INTO skill_level_history (skill_id, level, changed_at) VALUES (?, ?, ?)",
        (skill_id, level, now_iso()),
    )
    db.commit()
    return skill_id


def find_or_create_skill(name):
    db = get_db()
    name = name.strip()
    row = db.execute(
        "SELECT id FROM skill WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    if row:
        return row["id"]
    return create_skill(name)


def update_skill(skill_id, name, category, notes, level):
    db = get_db()
    current = get_skill(skill_id)
    db.execute(
        "UPDATE skill SET name = ?, category = ?, notes = ?, level = ? WHERE id = ?",
        (name, category, notes, level, skill_id),
    )
    if current is not None and current["level"] != level:
        db.execute(
            "INSERT INTO skill_level_history (skill_id, level, changed_at) VALUES (?, ?, ?)",
            (skill_id, level, now_iso()),
        )
    db.commit()


def get_skill(skill_id):
    db = get_db()
    return db.execute("SELECT * FROM skill WHERE id = ?", (skill_id,)).fetchone()


def list_skills():
    db = get_db()
    return db.execute("SELECT * FROM skill ORDER BY category, name").fetchall()


def skill_level_history(skill_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM skill_level_history WHERE skill_id = ? ORDER BY changed_at",
        (skill_id,),
    ).fetchall()


# entity_type -> (table, id_column, title_column) for resolving evidence
# back to something displayable without four separate evidence tables.
_EVIDENCE_ENTITY_TABLES = {
    "note": ("note", "id", "title"),
    "task": ("task", "id", "title"),
    "log_entry": ("log_entry", "id", "description"),
    "win": ("win", "id", "title"),
}


def add_skill_evidence(skill_name, entity_type, entity_id, comment=""):
    db = get_db()
    skill_id = find_or_create_skill(skill_name)
    db.execute(
        """INSERT INTO skill_evidence (skill_id, entity_type, entity_id, comment, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (skill_id, entity_type, entity_id, comment, now_iso()),
    )
    db.commit()


def evidence_for_entity(entity_type, entity_id):
    db = get_db()
    return db.execute(
        """SELECT skill_evidence.*, skill.name AS skill_name
           FROM skill_evidence JOIN skill ON skill.id = skill_evidence.skill_id
           WHERE entity_type = ? AND entity_id = ? ORDER BY skill_evidence.created_at""",
        (entity_type, entity_id),
    ).fetchall()


def evidence_for_skill(skill_id):
    """Each evidence row plus a human-readable title for whatever it's
    attached to, resolved from _EVIDENCE_ENTITY_TABLES."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM skill_evidence WHERE skill_id = ? ORDER BY created_at DESC",
        (skill_id,),
    ).fetchall()
    results = []
    for row in rows:
        table, id_column, title_column = _EVIDENCE_ENTITY_TABLES[row["entity_type"]]
        entity = db.execute(
            f"SELECT {title_column} AS title FROM {table} WHERE {id_column} = ?",
            (row["entity_id"],),
        ).fetchone()
        results.append({
            "id": row["id"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "entity_title": entity["title"] if entity else "(deleted)",
            "comment": row["comment"],
            "created_at": row["created_at"],
        })
    return results


def skills_touched_between(date_from, date_to):
    db = get_db()
    rows = db.execute(
        """SELECT DISTINCT skill.id, skill.name FROM skill
           JOIN skill_evidence ON skill_evidence.skill_id = skill.id
           WHERE date(skill_evidence.created_at) BETWEEN ? AND ?
           ORDER BY skill.name""",
        (date_from, date_to),
    ).fetchall()
    return rows


# --- Log entries (manual activity log items) ----------------------------

def create_log_entry(entry_date, description, project_id=None, time_spent=None):
    db = get_db()
    cur = db.execute(
        """INSERT INTO log_entry (entry_date, description, project_id, time_spent, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (entry_date, description, project_id, time_spent, now_iso()),
    )
    db.commit()
    return cur.lastrowid


def update_log_entry(log_entry_id, entry_date, description, project_id, time_spent):
    db = get_db()
    db.execute(
        """UPDATE log_entry SET entry_date = ?, description = ?, project_id = ?, time_spent = ?
           WHERE id = ?""",
        (entry_date, description, project_id, time_spent, log_entry_id),
    )
    db.commit()


def get_log_entry(log_entry_id):
    db = get_db()
    return db.execute("SELECT * FROM log_entry WHERE id = ?", (log_entry_id,)).fetchone()


def delete_log_entry(log_entry_id):
    db = get_db()
    db.execute("DELETE FROM log_entry WHERE id = ?", (log_entry_id,))
    db.commit()


# --- Wins ----------------------------------------------------------------

def create_win(win_date, title, what_i_did="", impact_result="", project_id=None,
                source_task_id=None, person_ids=None):
    db = get_db()
    cur = db.execute(
        """INSERT INTO win (win_date, title, what_i_did, impact_result, project_id,
                             source_task_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (win_date, title, what_i_did, impact_result, project_id, source_task_id, now_iso()),
    )
    win_id = cur.lastrowid
    _set_join_rows(win_id, "win_person", "win_id", "person_id", person_ids or [])
    db.commit()
    return win_id


def update_win(win_id, win_date, title, what_i_did, impact_result, project_id, person_ids=None):
    db = get_db()
    db.execute(
        """UPDATE win SET win_date = ?, title = ?, what_i_did = ?, impact_result = ?,
                           project_id = ? WHERE id = ?""",
        (win_date, title, what_i_did, impact_result, project_id, win_id),
    )
    _set_join_rows(win_id, "win_person", "win_id", "person_id", person_ids or [])
    db.commit()


def get_win(win_id):
    db = get_db()
    return db.execute("SELECT * FROM win WHERE id = ?", (win_id,)).fetchone()


def delete_win(win_id):
    db = get_db()
    db.execute("DELETE FROM win WHERE id = ?", (win_id,))
    db.commit()


def people_for_win(win_id):
    db = get_db()
    return db.execute(
        """SELECT person.* FROM person JOIN win_person ON win_person.person_id = person.id
           WHERE win_person.win_id = ? ORDER BY person.name""",
        (win_id,),
    ).fetchall()


def list_wins(project_id=None, date_from=None, date_to=None):
    db = get_db()
    query = "SELECT * FROM win WHERE 1 = 1"
    params = []
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if date_from:
        query += " AND win_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND win_date <= ?"
        params.append(date_to)
    query += " ORDER BY win_date DESC, id DESC"
    return db.execute(query, params).fetchall()


def wins_for_project(project_id):
    return list_wins(project_id=project_id)


# --- Activity log ----------------------------------------------------------

def list_activity(date_from=None, date_to=None, project_id=None):
    """Merge notes created, tasks completed, wins, and manual log entries
    into one timeline, newest first. Each source is a small, separate query
    (rather than one SQL UNION) since the four kinds have different shapes
    -- simpler to read than SQL that reconciles differing shapes."""
    db = get_db()
    items = []

    note_query = """
        SELECT DISTINCT note.id, note.title, note.created_at AS occurred_at
        FROM note LEFT JOIN note_project ON note_project.note_id = note.id
        WHERE 1 = 1
    """
    params = []
    if project_id:
        note_query += " AND note_project.project_id = ?"
        params.append(project_id)
    if date_from:
        note_query += " AND date(note.created_at) >= ?"
        params.append(date_from)
    if date_to:
        note_query += " AND date(note.created_at) <= ?"
        params.append(date_to)
    for row in db.execute(note_query, params).fetchall():
        items.append(dict(kind="note", occurred_at=row["occurred_at"],
                           title=row["title"], entity_id=row["id"]))

    task_query = "SELECT id, title, completed_at AS occurred_at FROM task WHERE status = 'done'"
    params = []
    if project_id:
        task_query += " AND project_id = ?"
        params.append(project_id)
    if date_from:
        task_query += " AND date(completed_at) >= ?"
        params.append(date_from)
    if date_to:
        task_query += " AND date(completed_at) <= ?"
        params.append(date_to)
    for row in db.execute(task_query, params).fetchall():
        items.append(dict(kind="task", occurred_at=row["occurred_at"],
                           title=row["title"], entity_id=row["id"]))

    win_query = "SELECT id, title, win_date AS occurred_at FROM win WHERE 1 = 1"
    params = []
    if project_id:
        win_query += " AND project_id = ?"
        params.append(project_id)
    if date_from:
        win_query += " AND win_date >= ?"
        params.append(date_from)
    if date_to:
        win_query += " AND win_date <= ?"
        params.append(date_to)
    for row in db.execute(win_query, params).fetchall():
        items.append(dict(kind="win", occurred_at=row["occurred_at"],
                           title=row["title"], entity_id=row["id"]))

    log_query = "SELECT id, description, entry_date AS occurred_at FROM log_entry WHERE 1 = 1"
    params = []
    if project_id:
        log_query += " AND project_id = ?"
        params.append(project_id)
    if date_from:
        log_query += " AND entry_date >= ?"
        params.append(date_from)
    if date_to:
        log_query += " AND entry_date <= ?"
        params.append(date_to)
    for row in db.execute(log_query, params).fetchall():
        items.append(dict(kind="log_entry", occurred_at=row["occurred_at"],
                           title=row["description"], entity_id=row["id"]))

    items.sort(key=lambda item: item["occurred_at"] or "", reverse=True)
    return items


# --- Weekly review -----------------------------------------------------

def current_week_str():
    year, week, _ = date.today().isocalendar()
    return f"{year}-W{week:02d}"


def week_str_to_monday(week_str):
    year, week = week_str.split("-W")
    return date.fromisocalendar(int(year), int(week), 1)


def adjacent_week_str(week_str, delta_weeks):
    monday = week_str_to_monday(week_str) + timedelta(weeks=delta_weeks)
    year, week, _ = monday.isocalendar()
    return f"{year}-W{week:02d}"


def get_weekly_review(week_str):
    db = get_db()
    return db.execute("SELECT * FROM weekly_review WHERE week = ?", (week_str,)).fetchone()


def save_weekly_review(week_str, went_well, to_improve, focus_next_week):
    db = get_db()
    db.execute(
        """INSERT INTO weekly_review (week, went_well, to_improve, focus_next_week, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT (week) DO UPDATE SET
               went_well = excluded.went_well,
               to_improve = excluded.to_improve,
               focus_next_week = excluded.focus_next_week,
               updated_at = excluded.updated_at""",
        (week_str, went_well, to_improve, focus_next_week, now_iso()),
    )
    db.commit()


def weekly_review_summary(week_str):
    db = get_db()
    monday = week_str_to_monday(week_str)
    sunday = monday + timedelta(days=6)
    date_from, date_to = monday.isoformat(), sunday.isoformat()

    notes_by_type = db.execute(
        """SELECT note_type.name AS type_name, COUNT(*) AS count
           FROM note JOIN note_type ON note_type.id = note.note_type_id
           WHERE date(note.created_at) BETWEEN ? AND ?
           GROUP BY note_type.name ORDER BY note_type.name""",
        (date_from, date_to),
    ).fetchall()

    tasks_completed = db.execute(
        """SELECT * FROM task WHERE status = 'done'
           AND date(completed_at) BETWEEN ? AND ? ORDER BY completed_at""",
        (date_from, date_to),
    ).fetchall()

    tasks_open_or_overdue = db.execute(
        f"SELECT * FROM task WHERE status != 'done' "
        f"ORDER BY {_PRIORITY_RANK_SQL}, due_date IS NULL, due_date"
    ).fetchall()

    wins = db.execute(
        "SELECT * FROM win WHERE win_date BETWEEN ? AND ? ORDER BY win_date",
        (date_from, date_to),
    ).fetchall()

    return dict(
        week_start=monday,
        week_end=sunday,
        notes_by_type=notes_by_type,
        tasks_completed=tasks_completed,
        tasks_open_or_overdue=tasks_open_or_overdue,
        skills_touched=skills_touched_between(date_from, date_to),
        wins=wins,
    )


# --- Settings (generic key/value) --------------------------------------

def get_setting(key, default=None):
    db = get_db()
    row = db.execute("SELECT value FROM setting WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    db = get_db()
    db.execute(
        """INSERT INTO setting (key, value) VALUES (?, ?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
        (key, value),
    )
    db.commit()


# --- AI (Phase 4) --------------------------------------------------------

def save_note_ai_summary(note_id, summary):
    db = get_db()
    db.execute("UPDATE note SET ai_summary = ? WHERE id = ?", (summary, note_id))
    db.commit()


# --- Export (Phase 5) ---------------------------------------------------

def export_all_data():
    """Everything in the database as plain dicts/lists, ready for
    json.dumps. Notes and wins get their tag names resolved inline (not
    just join-table ids) since that's far more useful in an export."""
    db = get_db()

    def all_rows(table):
        return [dict(row) for row in db.execute(f"SELECT * FROM {table}").fetchall()]

    notes = []
    note_query = """SELECT note.*, note_type.name AS type_name FROM note
                     JOIN note_type ON note_type.id = note.note_type_id
                     ORDER BY note.id"""
    for row in db.execute(note_query).fetchall():
        note = dict(row)
        tags = get_note_tags(note["id"])
        note["people"] = [p["name"] for p in tags["people"]]
        note["projects"] = [p["name"] for p in tags["projects"]]
        note["topics"] = [t["name"] for t in tags["topics"]]
        notes.append(note)

    wins = []
    for row in db.execute("SELECT * FROM win ORDER BY id").fetchall():
        win = dict(row)
        win["people"] = [p["name"] for p in people_for_win(win["id"])]
        wins.append(win)

    return {
        "note_types": all_rows("note_type"),
        "people": all_rows("person"),
        "projects": all_rows("project"),
        "topics": all_rows("topic"),
        "notes": notes,
        "tasks": all_rows("task"),
        "skills": all_rows("skill"),
        "skill_level_history": all_rows("skill_level_history"),
        "skill_evidence": all_rows("skill_evidence"),
        "log_entries": all_rows("log_entry"),
        "wins": wins,
        "weekly_reviews": all_rows("weekly_review"),
    }
