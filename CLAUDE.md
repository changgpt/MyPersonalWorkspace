# CLAUDE.md

Project conventions and layout for FiloFax. Read this before making changes.

## What this is

A local-only Flask app (see `daybook_spec.md`-style brief from the user) for
managing notes, tasks, people, skills and weekly reviews at work.
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
  checkboxes via `pymdownx.tasklist`, `~~strikethrough~~` via
  `pymdownx.tilde` with its subscript half switched off — a lone `~` is
  ordinary punctuation in a note).
- **Turndown** (vendored, `static/vendor/turndown.js`) converts the note
  body editor's HTML back to Markdown client-side on submit — see "The
  note body editor is WYSIWYG" below. The server only ever stores/renders
  plain Markdown; Turndown exists purely so typing feels like a normal
  rich-text editor instead of raw Markdown source.
- **msal + requests** (optional) for the Microsoft Graph path of the
  Dashboard's Outlook card, **pywin32** (optional, Windows-only) for the
  classic-Outlook-desktop path. Both imports are guarded — the app runs
  with neither installed and just reports that no calendar source is
  available.
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
                        # and automatically by `python run.py` on every startup
  seed.py              # default note types + their Markdown templates
  markdown_utils.py    # render_markdown(text) -> HTML
  date_utils.py         # human_date / human_date_range Jinja filters
  docx_utils.py         # docx_bytes_to_markdown(bytes) -> Markdown
  task_extraction.py    # action-item + checkbox-line parsing of a note body
  tag_utils.py           # shared comma-separated-tag-field parsing (note tags)
  greetings.py           # Dashboard greeting + motivational quote
  internship.py          # Dashboard "Week N" + days-left countdown
  calendar_sources.py    # Outlook: COM + Graph sources (the only I/O here)
  calendar_utils.py      # pure grouping/formatting for "Coming up" + cache
  htmx.py                # template_for/is_htmx: one route, page or fragment
  ai.py                  # Phase 4: optional Anthropic API features, off by default
  static/app.js           # Phase 5: keyboard shortcuts (n/t//) + dark mode toggle
  static/editor-toolbar.js # formatting toolbar for plain Markdown textareas
                          # (note-type templates only -- see note body below)
  static/rich-editor.js    # WYSIWYG note body editor (contenteditable + Turndown)
  static/note-checkboxes.js # makes a rendered note's own checkboxes live
  static/drag-drop.js       # generic delegated HTML5 drag/drop (Today + Board)
  static/toasts.js          # flash messages + window.showToast()
  static/select.js          # styled hover-to-open dropdowns over <select>
  static/search.js          # search typeahead: dismissal + arrow keys
  blueprints/           # one file per feature area (notes, people, projects,
                        # tasks, topics, search, settings, dashboard, skills,
                        # calendar, weekly_review)
  templates/            # Jinja templates, mirroring the blueprints;
                        # _name.html partials are htmx swap targets the
                        # full page also includes
  static/style.css       # warm-neutral design system (CSS custom properties)
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
- **Person is also a lightweight CRM profile** on top of the tag-entity
  pattern above: `role`, `team`, `how_met`, `last_contacted_date`,
  `follow_up`, plus the original `notes` column (labeled "Useful context"
  in the UI — it predates the other CRM fields and already meant free-form
  notes about the person, so it was reused rather than adding a redundant
  column; `db.update_person`'s `context` parameter maps to it). There's no
  `/people/new` — people are still only created by tagging them on a note
  (`find_or_create_person`), matching the Tag-like entities convention
  above; `GET/POST /people/<id>/edit` only ever edits a person that
  already exists. `templates/people/detail.html` shows every filled-in
  field in one card and an empty-state prompt to "add some" when none are
  set yet, rather than always rendering empty labels.
- **Tag input in forms** is a single comma-separated text field with an
  HTML `<datalist>` for autocomplete (not a JS multi-select widget) — simple
  and dependency-free. Known limitation: the browser's datalist suggests
  whole-field matches, not per-comma-segment, so autocomplete only helps
  while typing the first tag in the field.
- **The Notes list groups by note type by default, and auto-applies its
  filters.** The filter bar has no "Filter" button — a GET form already
  re-renders correctly from the query string on every change (it now does
  that through htmx, see the in-place-updates bullet below); "Clear" stays
  a plain link back to the unfiltered URL. Notes render in a `.card-grid`
  (the same auto-fill grid People/Projects use), not stacked full-width.
  - Ordering is a `sort` query param, resolved through
    `db._NOTE_SORTS` — an explicit `{name: order-by}` map, because the
    value goes straight into the SQL and an unknown one must fall back to
    the default rather than be interpolated or raise.
    `"type"` (default) is `note_type.name ASC, event_date DESC`; `"date"`
    is the old plain reverse-chronological order, still one click away in
    the bar.
  - `notes._group_by_type` turns the type-ordered rows into
    `[(type_name, type_color, [note, ...])]` in **one pass in Python**, not
    a GROUP BY — the template needs the whole row for each card anyway
    (same reasoning as `db.list_activity`'s Python-side merge). It relies
    on the query already being type-ordered, so don't change one without
    the other.
  - `notes/_grid.html` is **one partial with two shapes**: grouped
    sections under a coloured type heading, or a single flat grid when
    sorting by date. The flat case is deliberately *not* a degenerate
    group of one — a lone "All notes" heading above one grid is noise.
  - Inside a group the cards pass `note_card(note, show_type=false)`: the
    heading already names the type, and repeating the tag on every card
    was the noisiest thing on the page.
- **Markdown rendering** happens only at display time (`| markdown` Jinja
  filter in templates); the stored `body_markdown` is always the raw
  Markdown source, never pre-rendered HTML.
- **Dates are never rendered raw.** Storage is ISO text (`"2026-10-07"`),
  which reads like a database on screen, so every *displayed* date goes
  through the `| human_date` Jinja filter (`daybook/date_utils.py`,
  registered in `__init__.py` beside `markdown`): "Today" / "Yesterday" /
  "Tomorrow", then "Mon 5 Oct" for the rest of the surrounding week (the
  date stays on so a bare weekday can't be read as the wrong week), then
  "5 Oct", and "5 Oct 2025" once the year differs. `| human_date_range`
  does the weekly review's "This week · 5 - 11 Oct". Both accept an ISO
  date, an ISO timestamp, a `date` or a `datetime`, and return the input
  untouched if it won't parse, so a filter can't 500 a page. Two things
  deliberately stay ISO: an `<input type="date">` value (the browser
  requires it) and the weekly review's `week_str` identifier, which is
  shown as faint meta and used in URLs/export filenames. Day-of-month is
  interpolated (`{d.day}`) rather than `strftime("%-d")`, which is a
  glibc/macOS extension that raises on Windows.
- **FTS5 search index** (`note_fts`) is an external-content table kept in
  sync by SQL triggers in `schema.sql` (`note_ai`/`note_ad`/`note_au`) —
  don't write to `note_fts` directly; it follows `note` automatically.
- **The search box is a typeahead over everything, not just notes.**
  Typing fires `GET /search/suggest` (htmx, 180ms debounce) and drops a
  grouped panel under the box — notes, tasks, people, projects, topics —
  so results arrive without pressing Enter; Enter still goes to the full
  results page. `db.search_suggestions` runs notes through FTS5 (the
  trailing `*` in `search_notes`' query is what prefix-matches "hedg" to
  "hedging") and the other four through a `LIKE` over their name/title:
  they're small tables, and a LIKE reads far clearer than keeping four
  more external-content indexes in sync. User-typed `%`/`_`/`\` are
  escaped (`db._like_pattern`), or searching "100%" would match every row.
  - `/search/suggest` is deliberately its *own* endpoint rather than an
    `HX-Request` branch on `search_view` (the usual convention above):
    it isn't the results page in fragment form but a different, shorter
    thing, capped per kind and rendered over whatever page you're on.
  - An empty query renders **nothing at all**, and `.search-suggestions:empty`
    hides the panel — so "closed" is not a state anything has to track.
    `static/search.js` only handles dismissal (Escape, click-outside) and
    arrow-key navigation; htmx does the fetching.
  - The search form carries the page it was used from as a hidden `from`
    field, which is what lets the results page offer "← Back to Tasks"
    (`search._back_target`, labelled from `_SECTION_LABELS` by longest
    prefix). It's validated as an internal path exactly like
    `tasks._safe_next`, and `base.html` re-emits the *validated* value on
    the results page so a hand-crafted `from` can't be reflected back into
    the form. htmx only sends the triggering element's own value, so the
    input needs `hx-include="[name='from']"` or the dropdown's "See all
    results" link silently loses the Back target.
- **Every detail page has a back link to its own list page**, via the
  `back_link(href, label)` macro in `_macros.html` (`.back-link` in
  `style.css`). Used on notes/people/projects/topics/skills detail
  pages. It points at the *parent list*, not at the previous page: a note
  is reachable from Notes, the Dashboard, a person, a project or search, so
  "where you came from" would have to be threaded through every link (the
  way `tasks.edit_view` does with `next=`, which is only worth it there
  because a task genuinely has no single parent page), whereas the parent
  list is always a correct answer. The label is the page's *nav* name, so
  Topics' says "Knowledge Bank". Form pages deliberately don't use it --
  they already have a Cancel button, which is the same escape hatch with a
  clearer meaning mid-edit. `tests/test_back_links.py` pins all five.
- **Note type colors** are a fixed palette (`clay`, `sage`, `ochre`,
  `dustyblue`, `plum`, `slate`, `moss`, `rose`), each with a CSS class in
  `style.css` (`.tag-<color>`). Add new colors there before using them in
  `settings.NOTE_TYPE_COLORS`.
- **Interactions update in place, and one route serves both halves.** htmx
  used to be deliberately minimal here; it isn't any more — every click
  reloading the whole page was the main thing that made the app feel
  static. The pattern, applied to the Notes/Board/Activity filter bars, the
  Today quick-add, the Activity add-entry form and the weekly review save:
  - The swappable part of the page lives in a `_partial.html` the full page
    `include`s, so the two can't drift. It owns its own wrapper id
    (`#notes-results`, `#board-columns`, `#today-checklists`,
    `#activity-items`) and the template's `hx-target` points at that id.
  - The view renders `htmx.template_for(full_page, fragment)`
    (`daybook/htmx.py`, keyed on the `HX-Request` header): htmx gets the
    fragment, a browser gets the whole page. Routes that *write*
    (`quick_add_view`, `activity.create_view`, `weekly_review.save_view`)
    branch on `htmx.is_htmx()` and still return their redirect otherwise,
    so every form keeps working if JS doesn't run.
  - Filter bars use `hx-get` + `hx-trigger="change"` + `hx-push-url="true"`
    rather than `onchange="this.form.submit()"`. Pushing the URL is what
    keeps a filtered view shareable, bookmarkable, reload-safe and
    back-button-correct — don't drop it when adding a new filter.
  - `hx-indicator` points at the target so it dims (`.htmx-request`) while
    the request is in flight.
  - A save with nothing to redraw (the weekly review) returns `204` and the
    template raises a toast in `hx-on::after-request`; don't invent a
    fragment just to have something to swap.
- **Action-item extraction** (`task_extraction.extract_action_items`) finds
  `- [ ]` and `TODO:` lines in a note's body. `db.sync_tasks_from_note` is
  called after every note save; it creates a task per new line, keyed by
  the line's exact text so re-saving never duplicates. Sync is **one-way**:
  marking a task done flips its source line to `- [x]` in the note
  (`db.set_task_status` → `db._sync_note_checkbox`), but hand-editing a
  checkbox in the note body does not flip the task back. If you need to
  change this, start from `test_tasks.py`, which pins the current behaviour.
- **Task lists are ordered priority-then-date** (`db._PRIORITY_RANK_SQL`,
  a `CASE priority WHEN 'high' THEN 0 ...` expression — priority isn't
  alphabetically sortable). Shared by every query that lists *active*
  tasks (`list_tasks`, `list_tasks_by_bucket`, `list_today_flagged_tasks`,
  `list_overdue_tasks`, `tasks_for_project`, the weekly review's open/
  overdue list). Deliberately **not** applied to `tasks_for_note` (keeps
  the order they appear in the note) or `list_tasks_completed_this_week`
  (chronological completion order reads better there).
- **A task's prioritization is a `bucket`** (`today` / `long_term` /
  `background` — "Now / Next / Later" under a plainer name), not the
  `status` column. `status` still only ever means `todo`/`done` in the UI
  (`in_progress`/`blocked` remain in the schema's `CHECK` constraint for
  backward compatibility but nothing sets them anymore). `db.set_task_bucket`
  moves a task between buckets; `db.list_tasks_by_bucket(bucket)` powers
  both the Today page's three checklists and the Board's three non-Done
  columns. The `"today"` bucket's query also pulls in anything overdue
  regardless of its *own* bucket (so nothing slips through unnoticed) —
  the one case a task can show up away from its stored bucket; `long_term`/
  `background` show exactly what's filed there, no pull-forward, so a task
  never appears in two checklists at once. `bucket` replaces the old
  `is_today` boolean, which is gone from `schema.sql`'s `CREATE TABLE` (a
  brand-new database never has the column) but can still be sitting in an
  existing `data/daybook.db` predating this change — `db.init_db`'s
  `_add_column_if_missing` migration adds `bucket` and, the one time it
  actually adds the column (`bucket_added`), backfills from whatever
  `is_today` is already there (`is_today=1` → `today`, `is_today=0` →
  `background`) before leaving the now-unused `is_today` column in place
  (SQLite can't cheaply drop a column). Don't read or write `is_today` from
  any new code.
- **One consolidated `POST /tasks/<id>/move`** (`tasks.move_view`) handles
  every drag-and-drop move: it reads optional `bucket` and/or `status`
  form fields and applies whichever are present, reusing `db.set_task_bucket`
  and `db.set_task_status` (the latter to keep `completed_at` and the
  note-checkbox-sync behavior intact). Today's checklists only ever send
  `bucket`; Board's three bucket columns send `bucket` *and* `status=todo`
  (so dragging a card out of Done reopens it — safe to send unconditionally,
  since a task sitting in a non-Done Board column is never already done,
  by construction of how `board_view` groups tasks); Board's Done column
  sends only `status=done` (bucket is left untouched, so reopening later
  returns it to the bucket it came from).
- **A task's edit/delete redirect target is explicit (`next`), not
  `request.referrer`.** A task can be edited from Today, Board, a note's
  or project's linked-tasks list, or the dashboard — unlike every other
  "edit X" page in this app, there's no single page to fall back to, and
  `request.referrer` pointed at the edit page itself (so Save looked like
  it did nothing, and Delete sent you to a 404 for the task you'd just
  deleted). Every link to `tasks.edit_view` passes `next=request.full_path`
  (or, for the Today checklist's htmx-swapped row, the page read from the
  `HX-Current-URL` header `toggle_view` receives — `request.full_path`
  there would resolve to the AJAX endpoint itself, not the page the user is
  on). `tasks._safe_next()` reads it back from `request.values` (query
  string or form body) on save/delete, falling back to Today, and only
  honors an internal path (starts with `/`). Adding a new place that links
  to `tasks.edit_view` needs the same `next=...`, or Save/Delete there will
  silently fall back to Today instead of returning you to it.
- **Two ways to create a task, on purpose.** The Today/Board pages' quick-add
  box (`POST /tasks`, `tasks.quick_add_view`) is title-only, always lands in
  the `today` bucket, and exists for capturing something fast. `GET/POST
  /tasks/new` (`tasks.new_view`/`create_view`) reuses `tasks/form.html` in a
  create mode (`task=None`) for everything else (description, priority, due
  date, project, bucket) — the same template `edit_view` uses, just with the
  delete button, "Mark as win" link, and skills tagger all hidden behind
  `{% if task %}` (a task that doesn't exist yet has nothing to delete, tag,
  or have already been a win).
- **Drag-and-drop is plain HTML5 drag/drop** (`static/drag-drop.js`), no
  library, and is generic over any page: a draggable item needs
  `draggable="true" data-task-id="<id>"`, a drop target needs
  `data-drop-zone` plus `data-bucket="<bucket>"` and/or `data-status="<status>"`
  (whichever the zone should set on drop — see the `move` endpoint above).
  Shared verbatim by the Today page's three checklists and the Board's four
  columns. **Every** listener is delegated to `document` — including
  `dragover`/`drop`, which bubble — rather than bound to the zones found at
  load time: htmx now swaps whole checklists and columns in place, and
  anything bound per-zone would silently stop working on the replacement
  markup. `dragover` also sets `.drop-active` on the zone under the pointer
  (cleared on `dragleave`/`dragend`/`drop`), since previously there was no
  way to tell which column would receive the card, or that the drag was
  being tracked at all. Note that Playwright's mouse-driven drag does not
  emit `dragover`, so that highlight has to be verified by dispatching a
  real `DragEvent` rather than by dragging with the mouse. The move
  happens optimistically and POSTs via `fetch`; on failure it raises a
  toast and relies on a refresh to show the true state — acceptable for a
  single-user local tool, not a model to extend without reconsidering if
  this app ever needs to be more robust about it. `_task_row.html` (the
  checklist `<li>`, shared with dashboard/notes/projects' plain task
  lists) only renders `draggable`/`data-task-id` when the including
  template explicitly passes `draggable=true` — true only for the Today
  checklists (set directly in `today.html`, and by `tasks.toggle_view` on
  the swapped-in row when it recognizes the page it's swapping into as
  Today).
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
- **The Activity Log and Wins pages were removed** (user's call: "get rid
  of activity log, irrelevant. i think wins can also be gotten rid off").
  **Only the UI went** — the `win`, `win_person` and `log_entry` tables,
  their `db.py` functions, and their place in `db.export_all_data` are all
  untouched, so nothing already recorded is lost and the pages could come
  back. Deleting the tables would have been irreversible for the sake of a
  nav tidy-up, which isn't a trade worth making silently. What that costs:
  - `tests/test_removed_sections.py` pins both halves — the routes 404,
    and the rows still come out of the export.
  - Skill evidence can still point at a `win`/`log_entry` (older rows do),
    so `skills/detail.html` renders those as **plain text** rather than a
    link; don't delete the `{% else %}` branch thinking it's dead.
  - The weekly review's summary and its Markdown export no longer include
    a Wins section, and `ai._summary_digest` no longer sends one. A section
    you can't add to is dead weight.
  - `db.list_activity` is now unused by any route. It is kept as the
    reference for the one convention worth remembering from it: **merging
    heterogeneous sources happens in Python, not a SQL UNION** — one small
    query per source, sorted in Python, because the sources don't share a
    schema and SQL reconciling mismatched columns reads far worse.
    `notes._group_by_type` follows the same reasoning.
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
  export have their tag names resolved inline (wins no longer have a UI,
  but their rows and this resolution are deliberately still exported) (not just join-table ids),
  since that's what's actually useful outside the app.
- **Backup is a CLI command** (`flask backup-db`), not a web route — it
  just copies the sqlite file to `data/backups/`. Deliberately separate
  from the "export everything" feature: one is a full structured export,
  the other is a raw file copy for disaster recovery.
- **The content measure is viewport-*relative*, centred, and has been got
  wrong twice — read this before changing it.** Both obvious answers are
  wrong, and both have already shipped and been rejected by the user:
  1. A fixed `max-width: 920px` on `.main`. Full-screening the browser
     then did nothing at all ("it does not adjust to my screen which
     makes it feel weird").
  2. Removing the cap entirely (`.main-inner { width: 100% }`). Every
     card then ran to the screen edge, which read as untidy and
     oversized ("all the boxes are stretched to the end of the screen").
  The answer is neither: `--content-width: 61vw` with a
  `--content-min: 720px` floor, applied as
  `.main-inner { width: min(100%, max(var(--content-min), var(--content-width))); margin-inline: auto; }`.
  Being a *percentage of the viewport* is what satisfies both complaints
  at once — the column genuinely grows when the window does (1352px → 825,
  1920px → 1171, 2560px → 1562) and it always leaves gutters, so nothing
  touches the edge. The floor means a small laptop still fills its width,
  which is correct there. **Tune the two custom properties in `:root`**
  rather than adding a `max-width` to any individual page; a per-page cap
  is how this drifts back to problem 1.
  - `.main` itself still spans the window, so the gutters are page
    background rather than a narrower slab of surface colour, and
    `.main-inner` is centred *within the content area* (i.e. to the right
    of the sidebar), not within the whole window.
  - `.main` needs `min-width: 0` or a wide grid child forces the flex row
    past the viewport.
  - Grids stay `auto-fill`, so extra width still becomes *more columns*
    rather than stretched ones; the board keeps four comfortable columns
    at the narrower measure. Task/board columns drop from 3-4 to 2 below
    1200px — well before the layout breaks — because a task title needs
    real width to be readable.
  - `.note-article` keeps its own `68ch` measure, which is *narrower*
    than `--content-width` and stays that way (see the note-reading
    bullet below).
  - Form fields fill their column
    (`form:not(.filter-bar):not(.search-form) > input`, `.form-row`
    children); filter bars and the search box are excluded, since their
    controls are meant to sit inline at their natural size.
  - Overflow is checked by driving every page in a browser and asserting
    nothing in `.main-inner` extends past the viewport; do that again if
    you change the measure.
- **Base UI type is `--ui-size` (14px), set on `body`.** It was left at
  the browser's 16px default originally, which made the whole app read a
  size larger than it should next to its own 13-14px meta text ("everything
  is a bit big"). The dashboard's loudest items were scaled with it
  (stat tile value 28→23px, `.page-header h2` 22→19px, card padding
  16/20→13/16px, `.main-inner > h3` section headings pulled down to 15px
  with tighter margins — those margins were most of what read as airy once
  several sections stacked up). The **greeting went the other way**
  (30→25→28px): it's the page's only real title, and shrinking everything
  around it left it looking like just another heading.
  This is a *global UI* knob and is unrelated to `--note-size`, which is
  the reader-controlled A−/A+ size for note bodies only — don't conflate
  them or the A−/A+ buttons will appear to resize the chrome.
- **Dropdowns are a custom control** (`static/select.js` + the `.select-*`
  rules), because a native `<select>` can't be restyled (its popup is drawn
  by the OS, so border-radius, our colours and the dark theme never reach
  it) and can't be opened on hover (`showPicker()` throws without a real
  user gesture, and hovering isn't one). The native element **stays in the
  DOM** as the value holder — visually hidden but *not* `display: none`,
  which would make a `required` select unfocusable and block form
  submission — so form serialization, constraint validation, and the
  `change` event the filter bars' `hx-trigger` listens for all still see an
  ordinary select. Selecting an option sets `selectedIndex` and dispatches
  `change` manually (assigning `.value` fires nothing). Opens on hover
  after a short delay and closes after a longer one, so moving diagonally
  onto the panel doesn't close it; click, arrow keys, Enter and Escape all
  work too. `enhanceAll()` re-runs on `htmx:afterSettle` and is guarded by
  `data-enhanced`, so swapped-in markup gets enhanced exactly once.
- **Motion is one shared system, not per-element.** `--ease`/`--t`/`--t-fast`
  in `style.css` are the only easing and durations used; one rule lists
  every interactive element (buttons, cards, nav links, task rows, board
  cards, inputs) and transitions the same properties on all of them, so
  hovers feel identical everywhere. Keep new interactive elements in that
  list rather than giving them their own `transition`. Kept short on
  purpose (~120-160ms): past ~250ms a hover reads as lag. Only cards that
  are a link target lift (`.card:has(a.card-title):hover`) — a card that
  does nothing shouldn't invite a click. Keyboard focus uses
  `:focus-visible` so a clicked button doesn't keep a ring. Everything sits
  behind a `prefers-reduced-motion` block that drops the movement but keeps
  the colour changes.
- **Flash messages are toasts** (`static/toasts.js`, `.toast-stack` at the
  end of `base.html`), not a repurposed `.empty-state` div with inline
  style overrides as before. Two ways in, one appearance: server-side
  `flash()`es render into the stack on load, and `window.showToast(text)`
  raises one with no round trip (used by the weekly review save and by the
  failure paths in `drag-drop.js`/`note-checkboxes.js`, which used to call
  `alert()`). They self-dismiss after 4s or on click.
- **Headings use a serif font, body text a sans-serif one** — `--font-serif`
  (Georgia, falling back through a few other system serifs) on every
  `h1`-`h6` via one global rule in `style.css`, `--font-sans` (the original
  system-UI stack) everywhere else. No font files are vendored or loaded
  from a CDN (consistent with htmx/Turndown below) — Georgia ships with
  essentially every OS, so the stack is system-only by design, not a
  placeholder waiting for a real webfont.
- **Dark mode is pure CSS + localStorage**, no server-side setting: a
  `:root[data-theme="dark"]` block in `style.css` overrides the same
  custom properties the light theme defines, toggled by
  `toggleDarkMode()` in `static/app.js` and applied before first paint by
  an inline script in `base.html`'s `<head>` (reads `localStorage`, sets
  `document.documentElement.dataset.theme` before the stylesheet renders,
  so there's no flash). Any new color in a template or CSS rule should go
  through an existing custom property, or add one to *both* the light and
  dark blocks — a hard-coded hex value will look wrong in one theme.
- **The Dashboard's greeting banner** (`daybook/greetings.py`) is pure
  presentation, computed fresh on every request from `datetime.now()` (this
  is a 127.0.0.1-only app, so server time is the user's own time) — nothing
  is stored. `greeting_for_hour(hour)` buckets into morning (5-11) /
  afternoon (12-16) / evening (17-20) / `_LATE_NIGHT` (everything else) and
  pairs each with an emoji; `greeting_message` appends `config.DISPLAY_NAME`
  (from `.env`, blank by default so a fresh install doesn't greet you by
  someone else's name) only when it's set, so there's no dangling comma
  with no name. `random_quote()` picks one of a hardcoded `QUOTES` list
  (public-domain/widely-attributed figures, no copyrighted song lyrics or
  recent authors) on every load — intentionally random per visit rather
  than pinned per day, since "throw a quote at me" reads better as a
  surprise than a repeat. Keep this module free of any DB or network call;
  it's a presentation helper like `markdown_utils.py`, not a Phase 4
  AI feature.
- **The Dashboard's internship countdown** (`daybook/internship.py`,
  alongside `greetings.py` — same "pure presentation, no DB, no network"
  rule) computes `week_number(start_date)` (1-indexed, clamped to 1 if
  `today` is before `start_date`) and `days_remaining(end_date)` (clamped
  to 0 once past it) from `config.INTERNSHIP_START_DATE`/
  `INTERNSHIP_END_DATE` — both overridable in `.env` as `YYYY-MM-DD`,
  parsed by `config._parse_date` which falls back to the hardcoded default
  on anything malformed rather than crashing the app. The displayed end
  date is built manually in `dashboard.py`
  (`f"{d:%B} {d.day}, {d:%Y}"`), not `strftime("%b %-d, %Y")` — `%-d` (no
  leading zero) is a glibc/macOS `strftime` extension that raises on
  Windows, and this app needs to run there too.
- **The Dashboard's "Coming up" card reads Outlook, and is loaded
  *separately from the page*.** `dashboard.html` renders only a
  placeholder with `hx-trigger="load"` pointing at `GET
  /calendar/upcoming` (`blueprints/calendar.py`), which swaps the whole
  card `outerHTML`. Reading a calendar costs a few hundred milliseconds at
  best, and the Dashboard is the first thing you see — don't move this
  back inline. The card is the one partial with no full-page variant
  (hence no `htmx.template_for`): it only ever exists inside the
  Dashboard. `tests/test_calendar.py` pins that the Dashboard never
  touches a calendar source during its own render.
  - **Two sources behind one interface** (`calendar_sources.py`, the only
    module here that touches COM or the network — same split as `ai.py`):
    `OutlookComSource` drives a *classic* Outlook desktop install over COM
    and needs no credentials and nothing registered, which is what makes
    it the low-friction option on a managed work laptop — but it does need
    `pywin32` installed, so it is **not** "no setup", and describing it
    that way in the card's own hint actively misled (see
    `unavailable_hint` below); `GraphSource` calls Microsoft Graph with a
    delegated token. `resolve_source()` honours
    `config.OUTLOOK_SOURCE` (`auto`/`com`/`graph`/`off`) and prefers COM
    under `auto` because it needs nothing set up. An explicitly named
    source that isn't available **raises** rather than falling through, so
    a typo in `.env` is visible.
  - **A calendar that can't be read is never an error page and never a
    toast.** `upcoming_view` catches `CalendarError` and renders the
    message inside the card; "no source available" is a separate state
    (`days is None`) that shows a setup hint instead. A toast on every
    Dashboard load would be unbearable, and a 500 would take the whole
    Dashboard down with it.
  - **That hint is computed per machine** (`unavailable_hint()`), not a
    fixed sentence. `OutlookComSource.is_available()` only tests whether
    `win32com.client` imports, so on Windows "unavailable" nearly always
    means `pywin32` isn't installed — and the single generic line that
    used to sit here told the user it "works with no setup", which is the
    one thing that wasn't true. Each branch names the one next step for
    the platform it's actually on (install pywin32 / `OUTLOOK_SOURCE` is
    pinned elsewhere / set `GRAPH_CLIENT_ID` / run `--outlook-login`).
    Keep it that way: a card with one line of room has to spend it on the
    actual cause. `calendar_sources.diagnose()` prints the same facts plus
    a trial fetch (counts only, never subjects, so it's safe to paste) for
    when one line isn't enough, reachable both as `flask outlook-check`
    **and** as `python run.py --check-outlook`. Every user-facing string
    points at the `run.py` form: on Windows `flask` is routinely absent
    from PATH for the same reason pywin32 lands in the wrong interpreter,
    and a diagnostic that needs the broken plumbing to run is no
    diagnostic. Same for `--outlook-login`. Keep new advice on that form.
  - **`OutlookComSource.import_error()` keeps the ImportError rather than
    collapsing it to a boolean**, because pywin32 has two failure modes
    that both raise ImportError and need *opposite* fixes:
    `ModuleNotFoundError` means it isn't in the interpreter running the
    app (reinstall — and the hint says `python -m pip`, not bare `pip`,
    since installing into a different interpreter is the usual reason a
    package "installed fine" and still won't import), while a `DLL load
    failed` ImportError means it *is* installed but its native extensions
    aren't registered (`python -m pywin32_postinstall -install`, elevated
    — pip can't do it unelevated). Telling someone to reinstall something
    already installed sends them round in circles, so the underlying error
    is quoted in the card. `outlook-check` also prints `sys.executable`,
    which is the one fact the card can't show and the commonest culprit.
  - **The device-code prompt lives in the `--outlook-login` command, not
    in a request.** A web request can't block for a minute while someone types
    a code into a browser, so the CLI does it once and leaves an MSAL
    token cache in `data/` (git-ignored, chmod 600 where the OS honours
    it); the app itself only ever calls `acquire_token_silent`. There is
    deliberately **no client secret** anywhere — it's a public-client
    registration reading your own calendar.
  - **Times are localised at the boundary, not in Python.** Graph is sent
    a `Prefer: outlook.timezone="<Windows tz name>"` header
    (`config.CALENDAR_TIMEZONE`) and COM is local already, so
    `CalendarEvent.start`/`.end` are always naive local datetimes and
    nothing downstream does DST arithmetic. **Neither converter may
    convert**: both read clock fields verbatim.
    - `_com_naive_local` exists because that rule was broken once.
      `AppointmentItem.Start` is already the local wall-clock time Outlook
      displays, but pywin32 returns it timezone-*aware*, labelling that
      local time as UTC — so the original
      `datetime.fromtimestamp(value.timestamp())` round trip shifted every
      meeting by the host's UTC offset. An hour late all summer in London,
      and *correct wherever the offset is zero*, which is why it passed
      every test and every review on a UTC machine and only showed up on
      the user's laptop. Read the fields; never consult the tzinfo.
      `tests/test_calendar.py` pins this with a tz-aware stub and asserts
      the result is identical under London, UTC and New York.
    - Run the suite under a non-UTC `TZ` when touching anything in this
      area (`TZ=Europe/London python -m pytest tests/`). A UTC-only run
      cannot see an offset bug, which is the whole lesson here; the suite
      is green under UTC/London/New York/Tokyo/Sydney/Kiritimati.
    - The Graph side of this is *structurally* safe for the same reason
      (`event_from_graph` is a plain `fromisoformat` of whatever string
      Graph returns, no arithmetic) but rests on Graph honouring the
      `Prefer` header. That has not been verified end to end through this
      code — only the payload shape has. If Graph ever ignored it, times
      would come back UTC and be wrong by the offset in the *other*
      direction; the returned `start.timeZone` is what to check first.
  - `event_from_graph` / `event_from_com_item` are **pure** — they take a
    dict / any object with the COM attribute names — which is the only
    reason this is testable at all on a machine with no Outlook. The COM
    *fetch* path can't be exercised outside Windows; if you touch it,
    re-test on a real classic Outlook, and keep `IncludeRecurrences = True`
    before `Sort("[Start]")` before `Restrict(...)` — in that order, or
    every recurring meeting silently vanishes.
  - **`show_as` is normalised to Graph's vocabulary** (`free`/`tentative`/
    `busy`/`oof`/`workingElsewhere`), with COM's numeric `BusyStatus`
    mapped onto it, so templates only ever learn one set of names.
    `free` items are dimmed and `tentative` ones get a dashed bar: real
    calendars are full of all-day informational notices that otherwise
    drown out the actual meetings.
  - **Finished events drop off *today* only.** The card says "coming up",
    so `group_by_day` filters out anything already ended today (an all-day
    event stays, and a meeting still running counts as upcoming) — but
    past days reached with the back arrow keep everything, because there
    the framing doesn't apply. Empty days are still rendered: a blank
    Friday is information. Today's empty label is "No more events today",
    every other day's is "Nothing scheduled".
  - The arrows page by **whole windows** (`day_window(offset, days)`), not
    by a day, so `offset=0` is always "starting today" and that's all
    "Back to today" has to do.
  - Results are cached in **process memory** (`calendar_utils._CACHE`,
    TTL `config.CALENDAR_CACHE_SECONDS`), not in the `setting` table: the
    data is read-only and disposable, and a restart just re-fetches.
- **"Take notes" on a calendar event prefills a note** rather than
  creating one: `calendar_utils.note_prefill` builds query args for `GET
  /notes/new` (`title`, `date`, `people`), so an Outlook 1:1 becomes a 1:1
  note with the person already in the people field — tagging happens
  through the normal `find_or_create_person` path on save, so nothing is
  written until you submit the form. The people field is **left empty
  above `MAX_PREFILL_PEOPLE` (5) attendees**: tagging the two people in a
  1:1 is the point, but a fifteen-recipient distribution-list notice would
  spray fifteen Person rows into the database on one careless save.
  `notes.new_view`'s prefilled date goes through `_safe_iso_date`, since a
  malformed value makes `<input type="date">` render blank.
- **Keyboard shortcuts** (`static/app.js`): `n` new note, `t` Tasks
  (Today view, whose quick-add input has `autofocus`), `/` focuses
  `#global-search`. Guarded against firing while typing in a field or with
  a modifier key held — don't add a new single-key shortcut without the
  same guard.
- **Reading a note is its own layout, not a generic page.** Notes are the
  core of the app but were the one surface with no container: body text ran
  the full 920px of `.main` while lesser things (a task row, a stat tile)
  sat in cards. `notes/detail.html` is now an `.note-article` capped at
  `68ch` (past ~75 characters a line is measurably harder to track back
  from, and this is the one page meant for reading rather than scanning),
  with the body in a `.note-sheet` surface card. Don't widen it to match
  the other pages — the narrowness is the point.
- **A note's own checkboxes are the live ones** (`static/note-checkboxes.js`).
  `pymdownx.tasklist` renders `- [ ]` as a *disabled* checkbox, so the note
  page used to list every action item a second time underneath (as real
  task rows) purely to have something clickable — the same items twice on
  one screen. Instead `notes.detail_view` splits `tasks_for_note` using
  `task_extraction.checkbox_line_texts`: tasks whose `source_line_text`
  is a checkbox line in the body are passed as a `body_tasks` map (keyed on
  that text, exactly how `db._sync_note_checkbox` matches server-side) and
  the script un-disables and wires those checkboxes; everything else
  (`TODO:` lines, AI-suggested tasks — no checkbox of their own) still gets
  a row under "Linked tasks". The script posts to `/tasks/<id>/move`, which
  returns 204 and reuses `db.set_task_status`, so ticking in the note also
  rewrites `- [ ]` to `- [x]` in the stored Markdown; `/tasks/<id>/toggle`
  would have returned an HTML row meant for an htmx swap we don't want
  here. The `body_tasks` attribute is single-quoted in the template on
  purpose: `tojson` emits double quotes and escapes `'`, so a
  double-quoted attribute ends at the first key.
- **`.task-row` wraps rather than squeezing.** The same row renders
  full-width on the dashboard and inside a one-third-width Today column;
  a flex item can't shrink below its longest word, so without
  `flex-wrap: wrap` on the row and `flex: 1 1 40%; min-width: 0` on the
  title, a narrow column collapsed the title to one word per line while
  the priority/due/Edit items kept their space. Keep both if you restyle it.
- **The Dashboard is forward-looking: greeting, countdown, Coming up,
  Today's tasks, Overdue, Recent notes.** "Completed this week" was
  removed — it's a backward-looking list, and the page is for what's next
  (`db.list_tasks_completed_this_week` still exists and is still used by
  the weekly review). The primary button says "+ Quick note", not "New
  note": from here it's a capture action rather than a filing one.
- **The Dashboard de-duplicates "Today" against "Overdue".** An overdue
  task in the `today` bucket satisfies both queries and the two lists sit
  one above the other, so `dashboard.index` filters the overdue ids out of
  the today list. Overdue wins: more urgent framing, and it's the section
  further down the page. **Overdue therefore has to keep its own section**
  — because the today list has those ids filtered out, dropping the
  section would make an overdue task vanish from the Dashboard entirely
  rather than merely be listed twice.
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
  - Toolbar buttons (`.md-toolbar` + `data-md-action`) call
    `document.execCommand` (`bold`/`italic`/`strikeThrough`/
    `insertUnorderedList`/`insertOrderedList`/`formatBlock`/`indent`/
    `outdent`/`createLink`/`removeFormat`) instead of manipulating textarea
    text. They're wrapped in `.md-group` spans (divider + wrap at narrow
    widths) grouped by what they do: block style, inline formatting, lists,
    then quote/link/clear. Checklist items insert the *exact* HTML
    `pymdownx.tasklist` renders server-side (`markdown_utils.py`) —
    matching it exactly is what lets a checklist item round-trip to
    `- [ ] `/`- [x] ` either direction; `buildChecklistControl(checked)`
    is the single place that markup is constructed, shared with the paste
    path below.
  - **Every toolbar action must round-trip to Markdown**, which is what
    decides whether a button exists at all. Inline `<code>` has no
    execCommand, so `wrapInlineCode()` does it by hand; strikethrough
    needs *both* a Turndown rule (`<del>` → `~~`, since Turndown core's
    is in the GFM plugin we don't vendor) and `pymdownx.tilde` server-side
    to come back as `<del>`. Conversely **there is no font-size control
    and no underline**: Markdown has neither, so "size" is heading level
    (¶/H1/H2/H3) and Ctrl+U is explicitly swallowed rather than inserting
    a `<u>` that would silently vanish on save. Don't add a button whose
    formatting the stored Markdown can't express.
  - **Pasted HTML is rebuilt from an allowlist** (`sanitizePastedHtml`),
    because Word/Google Docs/web pages carry `<span style="font-family">`,
    `<font>`, `MsoNormal` classes and nested divs that either make Turndown
    emit odd output or show formatting the saved note won't have. Three
    categories: `PASTE_ALLOWED` tags are kept (attributes dropped except a
    link's `href`); `PASTE_DROPPED` tags go entirely, contents and all
    (`<script>`/`<style>`/form controls — unwrapping those dumped a
    stylesheet into the note); `PASTE_AS_PARAGRAPH` block wrappers become
    `<p>` so a `<div>`-based source keeps its paragraph breaks instead of
    running together. Everything else is unwrapped, keeping its text.
    `<input type="checkbox">` is special-cased through
    `buildChecklistControl` so a checklist copied from inside the app
    survives. Tables have no Turndown rule, so cells unwrap with a
    separating space rather than running together. The paste uses
    `execCommand("insertHTML")` to stay on the browser's undo stack.
    `notes/form.html` tells the user this in one line under the editor.
  - **Reading size (A−/A+) is a display preference, not note content.**
    `stepSize` writes `localStorage["filofax-note-size"]` and `applySize`
    toggles `.note-size-s/m/l/xl` on both `.rich-editor` and `.note-body`,
    so a note reads at the size it was written at. The classes set a
    `--note-size` *custom property* which the shared
    `.rich-editor, .note-body` rule consumes — setting `font-size`
    directly would lose on source order to that rule. The same A−/A+
    buttons appear in the editor toolbar and in `notes/detail.html`'s
    header actions; both just carry `data-note-size="-1"/"1"`.
  - **Four load-bearing DOM fix-ups in `rich-editor.js`, found by actually
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
    - `ensureTopLevelBlock` — text typed into a *wholly empty* editor (a
      new note whose type has no template) lands as a bare text node with
      no block wrapper; `defaultParagraphSeparator` only governs what
      Enter creates, not the first line. execCommand then has no block to
      work on: `insertUnorderedList` rebuilds the node and resets the
      selection to the editor's start, so the next Enter inserted *above*
      the line just typed — which cascaded into the whole note collapsing
      into one garbled item on save. Promotes that bare run to a `<p>`
      with `formatBlock` (which preserves the caret), on `input`, on Tab
      and before every toolbar action. The check is deliberately narrow —
      only when the caret itself is in a direct text child of the editor —
      so it can never reformat a list item or heading. The editor is left
      genuinely empty until something is typed, because the
      `.rich-editor:empty::before` placeholder depends on it; don't
      pre-seed a `<p>` to "fix" this.
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
    any plain items Markdown merged into the same list. Hiding the marker
    frees the gutter but doesn't fill it, so in such a merged list the
    checkbox started at the *content* edge and its text sat ~17px right of
    its plain neighbours'; the control is given exactly the gutter's width
    (`width: 1.5em; margin-left: -1.5em`) so the checkbox sits where the
    bullet would be and every item's text lines up. That also widens the
    click target, which `note-checkboxes.js` relies on.
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
python run.py         # http://127.0.0.1:5000 -- applies any pending migration on startup

python -m pytest tests/ -v

export FLASK_APP=run.py
flask backup-db       # copies data/daybook.db to data/backups/daybook-<timestamp>.db
flask outlook-login   # Graph calendar path only; Outlook desktop needs no sign-in
flask outlook-check   # why the Dashboard's "Coming up" card is empty

# Same two, without needing FLASK_APP set or `flask` on PATH -- prefer these
# when telling a user what to run, since the things they diagnose (a wrong
# interpreter, a missing Scripts dir) are exactly what breaks `flask`:
python run.py --check-outlook
python run.py --outlook-login
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
- **Phase 3 (done, partly since removed):** skills tracker (level history
  + evidence tagged from a note or task), weekly review (auto-summary +
  reflection fields, prev/next week nav, Markdown export). The activity
  log and wins log shipped here too and have since had their UI removed —
  see the convention bullet above; their tables and data remain.
- **Phase 4 (done):** optional AI features via the Anthropic API, off by
  default (`ANTHROPIC_API_KEY` in `.env` + Settings toggle) — summarize a
  note, suggest action items from a note (approved before creating tasks),
  draft a weekly review's reflection fields from that week's summary.
- **Phase 5 (done):** export everything as a zip (JSON + per-note
  Markdown), `flask backup-db` CLI command, keyboard shortcuts (n/t//),
  dark mode (CSS custom properties + localStorage), responsive layout
  (stacked sidebar, single/double-column grids below 760px).

All five phases from the original spec are complete.

Beyond the spec (added since):
- **Removed from the spec:** the Activity Log and Wins pages (UI only —
  data kept). See the convention bullet above.
- **Outlook "Coming up" on the Dashboard** — upcoming events read from
  classic Outlook desktop (COM, nothing to register) or Graph, lazy-loaded
  via htmx, with "Take notes" prefilling a note from the meeting. See the
  convention bullet above.
