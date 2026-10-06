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
- **Turndown** (vendored, `static/vendor/turndown.js`) converts the note
  body editor's HTML back to Markdown client-side on submit — see "The
  note body editor is WYSIWYG" below. The server only ever stores/renders
  plain Markdown; Turndown exists purely so typing feels like a normal
  rich-text editor instead of raw Markdown source.
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
  tag_utils.py           # shared comma-separated-tag-field parsing (notes + wins)
  ai.py                  # Phase 4: optional Anthropic API features, off by default
  static/app.js           # Phase 5: keyboard shortcuts (n/t//) + dark mode toggle
  static/editor-toolbar.js # formatting toolbar for plain Markdown textareas
                          # (note-type templates only -- see note body below)
  static/rich-editor.js    # WYSIWYG note body editor (contenteditable + Turndown)
  blueprints/           # one file per feature area (notes, people, projects,
                        # tasks, topics, search, settings, dashboard, skills,
                        # wins, activity, weekly_review)
  templates/            # Jinja templates, mirroring the blueprints
  static/style.css       # warm-neutral design system (CSS custom properties)
  static/board.js        # vanilla JS drag-and-drop for the task board
  static/vendor/         # vendored JS (htmx, turndown)
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
- **SkillEvidence is a lightweight polymorphic link**, not four nullable FK
  columns: `entity_type` (`note`/`task`/`log_entry`/`win`) + `entity_id`,
  resolved back to a title via `_EVIDENCE_ENTITY_TABLES` in `db.py`. The
  "tag a skill" UI (`templates/skills/_tagger.html`, posts to
  `POST /skills/evidence`) is one include shared by note detail, task edit,
  win detail, and the log entry edit page — don't duplicate this form.
  Every view that includes it must pass `entity_type`, `entity_id`,
  `evidence` (from `db.evidence_for_entity`), and `all_skills`
  (from `db.list_skills()`).
- **Win → people is a join table** (`win_person`, plural "people involved"
  in the spec); **Win → project is a single column** (singular "project",
  matching how `task.project_id` already works). "Links to related
  notes/tasks" is implemented as a single optional `source_task_id`, set by
  the "Mark as win" link on a completed task — not an open-ended
  many-to-many note/task picker.
- **Activity log is a Python-side merge**, not a SQL UNION: `db.list_activity`
  runs one small query per source (notes created, tasks completed, wins,
  manual log entries) and sorts the combined list in Python. The four
  sources don't share a schema, so this reads far more clearly than SQL
  that reconciles mismatched columns.
- **Weekly review** keys off an ISO week string like `"2026-W41"`
  (`db.current_week_str`/`week_str_to_monday`/`adjacent_week_str`). Its
  auto-summary is computed on the fly from existing tables, not stored —
  only the three reflection fields persist, upserted per week in
  `weekly_review`.
- **AI features (Phase 4) are off by default**, gated on two independent
  conditions checked by `ai.is_ai_enabled()`: `ANTHROPIC_API_KEY` set in
  `.env` (`ai.api_key_configured()`) AND the Settings toggle switched on
  (stored in the generic `setting` key/value table via
  `db.get_setting`/`set_setting`). Every feature's template shows a
  one-line "sends X to the Anthropic API" note next to its button —
  don't add a new AI-backed button without one.
  - Uses the official `anthropic` Python SDK (never raw HTTP), model id
    from `config.ANTHROPIC_MODEL` (never hard-coded in a call site).
  - `ai._complete()` is the only function that touches the network;
    everything else (`parse_bullet_list`, `parse_weekly_draft`,
    `_summary_digest`) is pure text processing, kept separate so it's
    testable without mocking an API call (see `tests/test_ai.py`, which
    mocks `ai._client`).
  - AI-suggested tasks (from `suggest_action_items`) require approval: the
    note route renders a checkbox list and only creates tasks for the ones
    submitted, per the spec. These tasks have `source_note_id` set but no
    `source_line_text` — they didn't come from a literal note line, so
    the task/note checkbox sync (see above) doesn't apply to them.
  - `ai.AIError` is the one exception type blueprints need to catch; it
    wraps both "features are off" and any underlying `anthropic.APIError`,
    and is shown to the user via `flash()`.
- **Export (`GET /settings/export`)** builds a zip in memory
  (`io.BytesIO` + `zipfile`, no temp files) from `db.export_all_data()` —
  one `data.json` plus one Markdown file per note. Notes/wins in the
  export have their tag names resolved inline (not just join-table ids),
  since that's what's actually useful outside the app.
- **Backup is a CLI command** (`flask backup-db`), not a web route — it
  just copies the sqlite file to `data/backups/`. Deliberately separate
  from the "export everything" feature: one is a full structured export,
  the other is a raw file copy for disaster recovery.
- **Dark mode is pure CSS + localStorage**, no server-side setting: a
  `:root[data-theme="dark"]` block in `style.css` overrides the same
  custom properties the light theme defines, toggled by
  `toggleDarkMode()` in `static/app.js` and applied before first paint by
  an inline script in `base.html`'s `<head>` (reads `localStorage`, sets
  `document.documentElement.dataset.theme` before the stylesheet renders,
  so there's no flash). Any new color in a template or CSS rule should go
  through an existing custom property, or add one to *both* the light and
  dark blocks — a hard-coded hex value will look wrong in one theme.
- **Keyboard shortcuts** (`static/app.js`): `n` new note, `t` Tasks
  (Today view, whose quick-add input has `autofocus`), `/` focuses
  `#global-search`. Guarded against firing while typing in a field or with
  a modifier key held — don't add a new single-key shortcut without the
  same guard.
- **The note body editor is WYSIWYG, not a Markdown-source textarea.**
  `templates/notes/form.html` renders a `contenteditable` div
  (`#body_editor`, class `.rich-editor`) pre-filled with
  `{{ body_markdown | markdown | safe }}` — so editing a note shows
  already-formatted bold/italic/headings/lists, never raw `**`/`##`
  syntax. A hidden `<textarea name="body_markdown" data-source="body_editor">`
  is what actually submits: `static/rich-editor.js`'s `syncRichEditors(form)`
  (wired via the form's `onsubmit`) converts the editor's current HTML to
  Markdown with Turndown (vendored at `static/vendor/turndown.js`) right
  before submit. **The server never sees HTML** — `body_markdown` in the
  database is unchanged plain Markdown, so search, task extraction, the
  note/win Markdown exports, and `.docx` import are all unaffected by this;
  only the editing experience changed.
  - Toolbar buttons (`.md-toolbar` + `data-md-action`, same markup as
    before) now call `document.execCommand` (`bold`/`italic`/
    `insertUnorderedList`/`insertOrderedList`/`formatBlock`/`indent`/
    `outdent`/`createLink`) instead of manipulating textarea text.
    Checklist items insert the *exact* HTML `pymdownx.tasklist` renders
    server-side (`markdown_utils.py`) — matching it exactly is what lets
    a checklist item round-trip to `- [ ] `/`- [x] ` either direction.
  - **Three load-bearing DOM fix-ups in `rich-editor.js`, found by actually
    exercising the editor in a browser (Chrome's execCommand is notoriously
    inconsistent — don't trust it to produce valid HTML and don't remove
    these without re-testing the exact scenarios in their comments):
    - `normalizeNestedLists` — `execCommand('indent')` nests a sub-list as
      a *sibling* of the preceding `<li>` (invalid: `<ul><li>A</li>
      <ul>...</ul></ul>`), which Turndown doesn't read as nesting; without
      this, an indented list item silently flattens back to the top level
      on save. Run at submit time on a cloned copy (not live — the
      invalid-but-equivalent form renders fine, so there's no visible bug
      to fix live).
    - `unwrapBlockChildrenFromParagraphs` — `execCommand('insertUnorderedList'
      /'insertOrderedList')` sometimes nests the new `<ul>`/`<ol>` *inside*
      the current `<p>` instead of replacing it (also invalid — a `<p>`
      can't contain a `<ul>`). Unlike the above, this one *is* visible
      live (it defeats the `:has()` bullet-hiding rule below, among other
      things), so it runs after every toolbar action, after Tab/Shift+Tab,
      and on every `input` event, not just at submit time.
    - `insertChecklistItem`'s empty-block detection treats `<p>`/`<div>`
      and `<li>` differently on purpose. Pressing Enter to exit a *nested*
      list only backs out one level (to a new empty `<li>`, not a plain
      paragraph) — replacing that `<li>` in place would nest a `<ul>`
      directly inside another `<ul>`. For that case it walks up to the
      outermost list and inserts after it instead. (A bug here previously
      scrambled an entire note's checklist + list items into one garbled
      task on save — if you touch this function, re-test a checklist
      added right after a *nested* (Tab-indented) list item, not just a
      flat one.)
  - **Checklist bullet-hiding is per-`<li>`, not per-`<ul>`.** Markdown
    merges a plain list and a checklist that follow each other with only a
    blank line between into *one* list block (common: jot plain notes,
    then add action items right after) — so `.rich-editor li:has(
    .task-list-control)` hides the marker on individual checkbox items
    only; a blanket rule on `ul.task-list` would also hide the bullet on
    any plain items Markdown merged into the same list.
  - Tab/Shift+Tab inside the editor call `execCommand('indent'/'outdent')`
    directly (meaningful mainly inside a list); this is unrelated to
    `editor-toolbar.js`'s own Tab handling, which only applies to plain
    textareas (see below).
- **`editor-toolbar.js` is now only for plain Markdown-source textareas**
  (currently just the note-type template editor in Settings) — a
  `.md-toolbar` div with `data-target="<textarea id>"` and buttons
  carrying `data-md-action` wraps or line-prefixes the current selection,
  plus Tab/Shift+Tab to indent/outdent (2 literal spaces). It explicitly
  skips any toolbar whose target isn't a real `<textarea>` (so it can't
  collide with the note body's rich-editor), and `rich-editor.js`
  symmetrically skips any target that isn't `isContentEditable` — the two
  files coexist on every page via `base.html` but never touch the same
  element. Both files are wrapped in an IIFE (`(function () {...})()`) to
  avoid colliding on shared top-level names like `ACTIONS`; if you add
  globally-callable glue (like `syncRichEditors`, called from an inline
  `onsubmit=""`), attach it explicitly via `window.fnName = fnName`.
- **Keyboard shortcuts** (`static/app.js`): `n` new note, `t` Tasks
  (Today view, whose quick-add input has `autofocus`), `/` focuses
  `#global-search`. Guarded against firing while typing in a field or with
  a modifier key held — don't add a new single-key shortcut without the
  same guard.
- **The note type `<select>` no longer touches the body.** It used to
  `hx-get` the type's template into the editor on every `change` — which
  meant picking a different type after you'd already started writing wiped
  it out. That endpoint (`GET /notes/template`) and wiring are gone;
  switching types now only affects metadata (color, settings link). The
  body is still prefilled once, server-side, for a genuinely new note —
  `{{ (note['body_markdown'] if note else (note_type['template_markdown']
  if note_type else '')) | markdown | safe }}` — via the dormant
  `?type=<id>` query param on `GET /notes/new` (not currently linked from
  any page, but harmless to leave in place).
- **Default note type templates have no `##` headers** (`seed.py`) — just
  bold labels (`**Attendees**`), since a heading felt heavier than the
  template needs. `seed.migrate_default_templates()`, called from `flask
  init-db`, updates any *unmodified* legacy (header-style) template to the
  new text — matched by exact string equality against a frozen snapshot
  (`_LEGACY_V1_TEMPLATES`), so a template you've hand-edited is never
  touched. Never add to `_LEGACY_V1_TEMPLATES` after the fact; it's a
  historical snapshot, not a place to track the "current previous" version.

## Running and testing

```bash
pip install -r requirements.txt
cp .env.example .env
export FLASK_APP=run.py
flask init-db        # idempotent: creates tables + seeds note types if empty
python run.py         # http://127.0.0.1:5000

python -m pytest tests/ -v

flask backup-db       # copies data/daybook.db to data/backups/daybook-<timestamp>.db
```

Tests use a temporary SQLite file per test (see `tests/conftest.py`), never
the real `data/daybook.db`.

## Data model (Phase 1 + 2 + 3 + 4)

`note_type`, `person`, `project`, `topic`, `note` (incl. `ai_summary`,
added via a manual `ALTER TABLE` migration in `db.init_db` since
`CREATE TABLE IF NOT EXISTS` doesn't add columns to an existing table —
see `_add_column_if_missing`), three join tables (`note_person`,
`note_project`, `note_topic`), the `note_fts` virtual table, `task`
(status/priority/due_date/is_today/project_id/source_note_id/
source_line_text), `skill` + `skill_level_history` + `skill_evidence`,
`log_entry`, `win` + `win_person`, `weekly_review`, and `setting`
(generic key/value, currently just the AI-features toggle).

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
- **Phase 3 (done):** activity log (auto timeline + manual entries), skills
  tracker (level history + evidence tagged from any note/task/log
  entry/win), wins log ("Mark as win" from a completed task, Markdown
  export), weekly review (auto-summary + reflection fields, prev/next
  week nav, Markdown export).
- **Phase 4 (done):** optional AI features via the Anthropic API, off by
  default (`ANTHROPIC_API_KEY` in `.env` + Settings toggle) — summarize a
  note, suggest action items from a note (approved before creating tasks),
  draft a weekly review's reflection fields from that week's summary.
- **Phase 5 (done):** export everything as a zip (JSON + per-note
  Markdown), `flask backup-db` CLI command, keyboard shortcuts (n/t//),
  dark mode (CSS custom properties + localStorage), responsive layout
  (stacked sidebar, single/double-column grids below 760px).

All five phases from the original spec are complete.
