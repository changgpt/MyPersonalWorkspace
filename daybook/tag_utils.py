"""Shared helpers for the "comma-separated text field + datalist" tagging
pattern used by notes and wins (see CLAUDE.md: Tag-like entities)."""


def parse_tag_names(raw):
    if not raw:
        return []
    return [name.strip() for name in raw.split(",") if name.strip()]


def tag_names_to_ids(raw, find_or_create):
    return [find_or_create(name) for name in parse_tag_names(raw)]


def tag_names_as_text(rows):
    return ", ".join(row["name"] for row in rows)
