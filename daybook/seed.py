"""Default note types, inserted once on first run (see `flask init-db`)."""

DEFAULT_NOTE_TYPES = [
    {
        "name": "Meeting note",
        "color": "clay",
        "template_markdown": (
            "## Attendees\n\n\n"
            "## Purpose\n\n\n"
            "## Discussion\n\n\n"
            "## Decisions\n\n\n"
            "## Actions\n\n- [ ] \n"
        ),
    },
    {
        "name": "Catch-up",
        "color": "sage",
        "template_markdown": (
            "## With\n\n\n"
            "## Updates\n\n\n"
            "## Asks\n\n\n"
            "## Actions\n\n- [ ] \n"
        ),
    },
    {
        "name": "CD Academy",
        "color": "ochre",
        "template_markdown": (
            "## Session\n\n\n"
            "## Speaker\n\n\n"
            "## Key takeaways\n\n\n"
            "## How it applies to my work\n\n\n"
            "## Follow-ups\n\n- [ ] \n"
        ),
    },
    {
        "name": "1:1",
        "color": "dustyblue",
        "template_markdown": (
            "## Topics\n\n\n"
            "## Feedback received\n\n\n"
            "## Actions\n\n- [ ] \n"
        ),
    },
    {
        "name": "LP query",
        "color": "plum",
        "template_markdown": (
            "## LP\n\n\n"
            "## Question\n\n\n"
            "## Sources checked\n\n\n"
            "## Answer\n\n\n"
            "## Reviewed by\n\n\n"
            "## Actions\n\n- [ ] \n"
        ),
    },
    {
        "name": "Reading / learning",
        "color": "slate",
        "template_markdown": (
            "## Source\n\n\n"
            "## Summary\n\n\n"
            "## Key ideas\n\n\n"
            "## Skills touched\n\n\n"
        ),
    },
    {
        "name": "Idea",
        "color": "moss",
        "template_markdown": (
            "## Idea\n\n\n"
            "## Why it matters\n\n\n"
            "## Next step\n\n\n"
        ),
    },
]


def seed_note_types(db):
    existing = db.execute("SELECT COUNT(*) AS n FROM note_type").fetchone()["n"]
    if existing:
        return
    for nt in DEFAULT_NOTE_TYPES:
        db.execute(
            "INSERT INTO note_type (name, color, template_markdown) VALUES (?, ?, ?)",
            (nt["name"], nt["color"], nt["template_markdown"]),
        )
    db.commit()
