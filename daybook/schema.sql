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
    team TEXT,
    how_met TEXT,
    -- "Useful context" in the UI -- this column predates the CRM fields
    -- below and already meant free-form notes about the person, so it's
    -- reused rather than adding a redundant column.
    notes TEXT,
    last_contacted_date TEXT,
    follow_up TEXT
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
    bucket TEXT NOT NULL DEFAULT 'today'
        CHECK (bucket IN ('today', 'long_term', 'background')),
    project_id INTEGER REFERENCES project(id),
    source_note_id INTEGER REFERENCES note(id) ON DELETE SET NULL,
    -- Text of the "- [ ] ..." / "TODO: ..." line this task was extracted
    -- from, used both to avoid re-creating it on every note save and to
    -- find the line again when flipping its checkbox (see db.set_task_status).
    -- NULL for tasks created directly (not from a note).
    source_line_text TEXT,
    -- Manual order within a bucket, renumbered 1..n by
    -- db.set_bucket_order when a task is dragged. 0 means "never
    -- hand-ordered", which sorts above the rest and then falls
    -- through to the priority/date ordering -- so a database that has
    -- never been reordered behaves exactly as before.
    position INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS skill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT 'technical'
        CHECK (category IN ('technical', 'financial', 'communication', 'domain')),
    level INTEGER NOT NULL DEFAULT 1 CHECK (level BETWEEN 1 AND 5),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

-- One row per level change, so a skill's page can show how it grew over
-- time. The current level also lives on `skill` itself for quick display.
CREATE TABLE IF NOT EXISTS skill_level_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id INTEGER NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 5),
    changed_at TEXT NOT NULL
);

-- Links a skill to whatever it was practiced on. entity_type/entity_id is
-- a lightweight polymorphic reference (not a real foreign key, since SQLite
-- can't target one of several tables) rather than four separate nullable
-- FK columns.
CREATE TABLE IF NOT EXISTS skill_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id INTEGER NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('note', 'task', 'log_entry', 'win')),
    entity_id INTEGER NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS log_entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL,
    description TEXT NOT NULL,
    project_id INTEGER REFERENCES project(id),
    time_spent TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS win (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    win_date TEXT NOT NULL,
    title TEXT NOT NULL,
    what_i_did TEXT NOT NULL DEFAULT '',
    impact_result TEXT NOT NULL DEFAULT '',
    project_id INTEGER REFERENCES project(id),
    source_task_id INTEGER REFERENCES task(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS win_person (
    win_id INTEGER NOT NULL REFERENCES win(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    PRIMARY KEY (win_id, person_id)
);

CREATE TABLE IF NOT EXISTS weekly_review (
    week TEXT PRIMARY KEY,  -- ISO week, e.g. "2026-W41"
    went_well TEXT NOT NULL DEFAULT '',
    to_improve TEXT NOT NULL DEFAULT '',
    focus_next_week TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

-- Generic key/value store for small app-wide settings (currently just the
-- Phase 4 AI-features toggle). See db.get_setting/set_setting.
CREATE TABLE IF NOT EXISTS setting (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
