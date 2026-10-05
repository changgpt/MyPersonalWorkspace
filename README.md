# Daybook

A personal, local-only web app for managing your day at work: typed notes, a
to-do list and task tracker, an activity log, a skills tracker, a wins log,
and a weekly review.

This runs entirely on your own laptop. No accounts, no hosting, no telemetry,
no network calls except the optional AI features (off by default — see
Phase 4 below, which arrives in a later phase).

## Setup

Requires Python 3.9+.

```bash
# from the project root
pip install -r requirements.txt
cp .env.example .env   # edit SECRET_KEY if you like; defaults are fine for local use
```

## Run it

```bash
export FLASK_APP=run.py   # Windows (cmd): set FLASK_APP=run.py
flask init-db             # creates data/daybook.db and seeds the default note types
                           # (safe to re-run; it won't touch existing data)
python run.py
```

Then open **http://127.0.0.1:5000** in your browser.

The app only binds to `127.0.0.1`, so it isn't reachable from other devices
on your network.

## Run the tests

```bash
python -m pytest tests/ -v
```

## What's here

**Phase 1 — notes:**
- Pick a note type (Meeting note, Catch-up, CD Academy, 1:1, LP query,
  Reading / learning, Idea), get a pre-filled Markdown template, write or
  paste content, or import a `.txt`/`.md`/`.docx` file.
- Tag notes with **people**, **projects**, and **topics** — new ones can be
  created just by typing a new name.
- **Knowledge Bank** — every topic you've tagged, each with its own page
  listing everything written about it.
- **People** and **Projects** pages — click through from any tag to see every
  note linked to that person or project.
- **Full-text search** across note titles and bodies, with highlighted
  matches.
- **Settings** — add, rename, or archive note types and edit their templates.

**Phase 2 — tasks:**
- Any `- [ ]` or `TODO:` line in a note's body automatically becomes a task,
  linked back to that note. Re-saving the note never creates duplicates.
- **Today** — a checklist of tasks flagged "today" plus anything overdue,
  with a quick-add box. Checking a task off also ticks its checkbox back in
  the original note.
- **Board** — kanban columns (To do / In progress / Blocked / Done), drag a
  card to change its status, filter by project or priority.
- The **Dashboard** now shows today's tasks, overdue tasks, and what you've
  completed this week.

The activity log, skills tracker, wins log, and weekly review are planned
for Phase 3.

## Project layout

See `CLAUDE.md` for the full layout and conventions used while building this.
