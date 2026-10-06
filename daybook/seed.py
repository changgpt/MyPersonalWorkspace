"""Default note types, inserted once on first run (see `flask init-db`)."""

DEFAULT_NOTE_TYPES = [
    {
        "name": "Meeting note",
        "color": "clay",
        "template_markdown": (
            "**Attendees**\n\n\n"
            "**Purpose**\n\n\n"
            "**Discussion**\n\n\n"
            "**Decisions**\n\n\n"
            "**Actions**\n\n- [ ] \n"
        ),
    },
    {
        "name": "Catch-up",
        "color": "sage",
        "template_markdown": (
            "**With**\n\n\n"
            "**Updates**\n\n\n"
            "**Asks**\n\n\n"
            "**Actions**\n\n- [ ] \n"
        ),
    },
    {
        "name": "CD Academy",
        "color": "ochre",
        "template_markdown": (
            "**Session**\n\n\n"
            "**Speaker**\n\n\n"
            "**Key takeaways**\n\n\n"
            "**How it applies to my work**\n\n\n"
            "**Follow-ups**\n\n- [ ] \n"
        ),
    },
    {
        "name": "1:1",
        "color": "dustyblue",
        "template_markdown": (
            "**Topics**\n\n\n"
            "**Feedback received**\n\n\n"
            "**Actions**\n\n- [ ] \n"
        ),
    },
    {
        "name": "LP query",
        "color": "plum",
        "template_markdown": (
            "**LP**\n\n\n"
            "**Question**\n\n\n"
            "**Sources checked**\n\n\n"
            "**Answer**\n\n\n"
            "**Reviewed by**\n\n\n"
            "**Actions**\n\n- [ ] \n"
        ),
    },
    {
        "name": "Reading / learning",
        "color": "slate",
        "template_markdown": (
            "**Source**\n\n\n"
            "**Summary**\n\n\n"
            "**Key ideas**\n\n\n"
            "**Skills touched**\n\n\n"
        ),
    },
    {
        "name": "Idea",
        "color": "moss",
        "template_markdown": (
            "**Idea**\n\n\n"
            "**Why it matters**\n\n\n"
            "**Next step**\n\n\n"
        ),
    },
]

# Frozen snapshot of the very first default templates (before the "##"
# section headers were dropped in favour of plain bold labels). Used only
# by migrate_default_templates, below -- never add to this, it's history.
_LEGACY_V1_TEMPLATES = {
    "Meeting note": (
        "## Attendees\n\n\n## Purpose\n\n\n## Discussion\n\n\n"
        "## Decisions\n\n\n## Actions\n\n- [ ] \n"
    ),
    "Catch-up": (
        "## With\n\n\n## Updates\n\n\n## Asks\n\n\n## Actions\n\n- [ ] \n"
    ),
    "CD Academy": (
        "## Session\n\n\n## Speaker\n\n\n## Key takeaways\n\n\n"
        "## How it applies to my work\n\n\n## Follow-ups\n\n- [ ] \n"
    ),
    "1:1": (
        "## Topics\n\n\n## Feedback received\n\n\n## Actions\n\n- [ ] \n"
    ),
    "LP query": (
        "## LP\n\n\n## Question\n\n\n## Sources checked\n\n\n"
        "## Answer\n\n\n## Reviewed by\n\n\n## Actions\n\n- [ ] \n"
    ),
    "Reading / learning": (
        "## Source\n\n\n## Summary\n\n\n## Key ideas\n\n\n## Skills touched\n\n\n"
    ),
    "Idea": (
        "## Idea\n\n\n## Why it matters\n\n\n## Next step\n\n\n"
    ),
}


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


def migrate_default_templates(db):
    """One-time cleanup for databases seeded before the "##" headers were
    dropped: updates a note type's template only if it still has the
    *exact* original text (i.e. was never hand-edited), to the current
    default. No-op once migrated, and never touches a customized template."""
    current_by_name = {nt["name"]: nt["template_markdown"] for nt in DEFAULT_NOTE_TYPES}
    for name, legacy_template in _LEGACY_V1_TEMPLATES.items():
        new_template = current_by_name.get(name)
        if new_template is None:
            continue
        db.execute(
            "UPDATE note_type SET template_markdown = ? WHERE name = ? AND template_markdown = ?",
            (new_template, name, legacy_template),
        )
    db.commit()
