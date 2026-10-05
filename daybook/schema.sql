-- Daybook database schema.
-- Run once at startup by db.init_db() if tables don't exist yet.

CREATE TABLE IF NOT EXISTS note_type (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT 'clay',
    template_markdown TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS person (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    description TEXT
);

CREATE TABLE IF NOT EXISTS topic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    note_type_id INTEGER NOT NULL REFERENCES note_type(id),
    event_date TEXT NOT NULL,
    body_markdown TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS note_person (
    note_id INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, person_id)
);

CREATE TABLE IF NOT EXISTS note_project (
    note_id INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, project_id)
);

CREATE TABLE IF NOT EXISTS note_topic (
    note_id INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topic(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, topic_id)
);

-- Full-text index over note title/body. "External content" table: it stores
-- no data of its own, just a search index pointing back at note.id, kept in
-- sync by the triggers below.
CREATE VIRTUAL TABLE IF NOT EXISTS note_fts USING fts5(
    title,
    body_markdown,
    content='note',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS note_ai AFTER INSERT ON note BEGIN
    INSERT INTO note_fts(rowid, title, body_markdown)
    VALUES (new.id, new.title, new.body_markdown);
END;

CREATE TRIGGER IF NOT EXISTS note_ad AFTER DELETE ON note BEGIN
    INSERT INTO note_fts(note_fts, rowid, title, body_markdown)
    VALUES ('delete', old.id, old.title, old.body_markdown);
END;

CREATE TRIGGER IF NOT EXISTS note_au AFTER UPDATE ON note BEGIN
    INSERT INTO note_fts(note_fts, rowid, title, body_markdown)
    VALUES ('delete', old.id, old.title, old.body_markdown);
    INSERT INTO note_fts(rowid, title, body_markdown)
    VALUES (new.id, new.title, new.body_markdown);
END;

CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'todo'
        CHECK (status IN ('todo', 'in_progress', 'blocked', 'done')),
    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low', 'medium', 'high')),
    due_date TEXT,
    is_today INTEGER NOT NULL DEFAULT 0,
    project_id INTEGER REFERENCES project(id),
    source_note_id INTEGER REFERENCES note(id) ON DELETE SET NULL,
    -- Text of the "- [ ] ..." / "TODO: ..." line this task was extracted
    -- from, used both to avoid re-creating it on every note save and to
    -- find the line again when flipping its checkbox (see db.set_task_status).
    -- NULL for tasks created directly (not from a note).
    source_line_text TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
