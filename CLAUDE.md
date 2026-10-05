# CLAUDE.md

Project conventions and layout for Daybook. Read this before making changes.

## What this is

A local-only Flask app (see `daybook_spec.md`-style brief from the user) for
managing notes, tasks, activity, skills, wins, and weekly reviews at work.
Single user, runs on `127.0.0.1`, SQLite file in `data/` (git-ignored).

## Stack and why

- **Flask**, not FastAPI — this is server-rendered and synchronous; FastAPI's
  async/auto-docs strengths don't apply to a single-user local app.
- **Plain `sqlite3`**, not an ORM — all SQL lives in `daybook/db.py` as
  explicit functions (`create_note`, `list_notes`, ...). This keeps FTS5
  queries (which ORMs handle awkwardly) simple and keeps "what query runs"
  visible, which matters more than ORM convenience at this scale.
- **Jinja templates + HTMX** for interactivity, vendored locally at
  `daybook/static/vendor/htmx.min.js` (fetched once via npm during
  development — never loaded from a CDN at runtime).
- **python-markdown + pymdown-extensions** for Markdown rendering (task list
  checkboxes via `pymdownx.tasklist`).
- **python-docx** for `.docx` → Markdown conversion — a deliberately partial
  converter (headings, bold/italic, bullet/numbered lists, paragraphs only;
  no tables or images). See `daybook/docx_utils.py`.

## Layout

```
daybook/
  __init__.py         # app factory (create_app), registers blueprints + markdown filter
  config.py           # reads .env, defines DATA_DIR / DATABASE_PATH / SECRET_KEY
  db.py               # all SQL lives here; thin functions, sqlite3.Row results
  schema.sql           # CREATE TABLE/TRIGGER statements, run by `flask init-db`
  seed.py              # default note types + their Markdown templates
  markdown_utils.py    # render_markdown(text) -> HTML
  docx_utils.py         # docx_bytes_to_markdown(bytes) -> Markdown
  task_extraction.py    # extract_action_items(markdown) -> ["line text", ...]
  blueprints/           # one file per feature area (notes, people, projects,
                        # tasks, topics, search, settings, dashboard)
  templates/            # Jinja templates, mirroring the blueprints
  static/style.css       # warm-neutral design system (CSS custom properties)
  static/board.js        # vanilla JS drag-and-drop for the task board
  static/vendor/         # vendored JS (htmx)
tests/                   # pytest; conftest.py gives `app`/`client`/`db` fixtures
run.py                   # entry point: `python run.py`
data/                    # git-ignored; daybook.db lives here
```

## Conventions

- **No ORM.** Add new queries as functions in `db.py`, not inline SQL in
  blueprints.
- **Tag-like entities** (Person, Project, Topic) share a pattern: find-or-
  create by case-insensitive name (`find_or_create_person`, etc.), a join
  table per note relationship (`note_person`, `note_project`, `note_topic`),
  and a detail page listing every note linked to that entity. Follow this
  pattern for any future taggable entity.
- **Tag input in forms** is a single comma-separated text field with an
  HTML `<datalist>` for autocomplete (not a JS multi-select widget) — simple
  and dependency-free. Known limitation: the browser's datalist suggests
  whole-field matches, not per-comma-segment, so autocomplete only helps
  while typing the first tag in the field.
- **Markdown rendering** happens only at display time (`| markdown` Jinja
  filter in templates); the stored `body_markdown` is always the raw
  Markdown source, never pre-rendered HTML.
- **FTS5 search index** (`note_fts`) is an external-content table kept in
  sync by SQL triggers in `schema.sql` (`note_ai`/`note_ad`/`note_au`) —
  don't write to `note_fts` directly; it follows `note` automatically.
- **Note type colors** are a fixed palette (`clay`, `sage`, `ochre`,
  `dustyblue`, `plum`, `slate`, `moss`, `rose`), each with a CSS class in
  `style.css` (`.tag-<color>`). Add new colors there before using them in
  `settings.NOTE_TYPE_COLORS`.
- **htmx usage is minimal by design**: the note-type template prefill
  (`GET /notes/template?note_type_id=`), wired via `hx-get`/
  `hx-trigger="change"` on the type `<select>`, and the Today checklist's
  checkbox toggle (`POST /tasks/<id>/toggle`, swaps in the updated `<li>`).
  Prefer plain forms/links over htmx unless there's a genuine partial-update
  case.
- **Action-item extraction** (`task_extraction.extract_action_items`) finds
  `- [ ]` and `TODO:` lines in a note's body. `db.sync_tasks_from_note` is
  called after every note save; it creates a task per new line, keyed by
  the line's exact text so re-saving never duplicates. Sync is **one-way**:
  marking a task done flips its source line to `- [x]` in the note
  (`db.set_task_status` → `db._sync_note_checkbox`), but hand-editing a
  checkbox in the note body does not flip the task back. If you need to
  change this, start from `test_tasks.py`, which pins the current behaviour.
- **Board drag-and-drop** is plain HTML5 drag/drop (`static/board.js`), no
  library. It moves the card optimistically and POSTs the new status;
  on failure it just alerts and relies on a refresh to show the true state
  — acceptable for a single-user local tool, not a model to extend without
  reconsidering if this app ever needs to be more robust about it.

## Running and testing

```bash
pip install -r requirements.txt
cp .env.example .env
export FLASK_APP=run.py
flask init-db        # idempotent: creates tables + seeds note types if empty
python run.py         # http://127.0.0.1:5000

python -m pytest tests/ -v
```

Tests use a temporary SQLite file per test (see `tests/conftest.py`), never
the real `data/daybook.db`.

## Data model (Phase 1 + 2)

`note_type`, `person`, `project`, `topic`, `note`, three join tables
(`note_person`, `note_project`, `note_topic`), the `note_fts` virtual table,
and `task` (status/priority/due_date/is_today/project_id/source_note_id/
source_line_text). `LogEntry`, `Skill`, `SkillEvidence`, `Win`, and
`WeeklyReview` are not implemented yet — they arrive in Phase 3.

Note: `task` has no `person` field (matches the original spec's data
model), so a task isn't directly linked to a person — only to a project
and/or its source note. The People page still only shows notes.

## Phase status

- **Phase 1 (done):** notes, note types + templates, people/projects/topics
  tagging, Knowledge Bank, full-text search, settings.
- **Phase 2 (done):** Task model, Today checklist (quick-add, overdue +
  is_today), Board (kanban, drag-and-drop, filter by project/priority),
  auto-extraction of `- [ ]` / `TODO:` lines from notes into linked tasks
  (dedup on resave, one-way checkbox sync back to the note), dashboard
  now shows today's tasks / overdue / completed-this-week.
- **Phase 3 (not started):** activity log, skills tracker, wins log, weekly
  review.
- **Phase 4 (not started):** optional AI features via Anthropic API, off by
  default.
- **Phase 5 (not started):** export/backup, keyboard shortcuts, dark mode,
  responsive layout.

When starting the next phase, update this file's "Phase status" section and
the data model section above.
