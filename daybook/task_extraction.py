"""Finds action-item lines in a note's Markdown body.

A line starting with "- [ ]" or "TODO:" becomes a task (see
db.sync_tasks_from_note). This module only extracts the text; it doesn't
touch the database, so it's trivial to unit test.
"""
import re

_CHECKBOX_RE = re.compile(r"^\s*-\s*\[\s\]\s*(.+?)\s*$")
_TODO_RE = re.compile(r"^\s*TODO:\s*(.+?)\s*$", re.IGNORECASE)


_ANY_CHECKBOX_RE = re.compile(r"^\s*-\s*\[[ xX]\]\s*(.+?)\s*$")


def extract_action_items(body_markdown):
    """Return the text of every unchecked action-item line, in order."""
    items = []
    for line in (body_markdown or "").splitlines():
        match = _CHECKBOX_RE.match(line) or _TODO_RE.match(line)
        if match:
            items.append(match.group(1))
    return items


def checkbox_line_texts(body_markdown):
    """Text of every checkbox line, ticked or not -- i.e. exactly the lines
    the renderer turns into a visible checkbox. "TODO:" lines are excluded:
    they become tasks too, but render as plain prose, so (unlike these)
    they aren't already on screen as something tickable."""
    texts = []
    for line in (body_markdown or "").splitlines():
        match = _ANY_CHECKBOX_RE.match(line)
        if match:
            texts.append(match.group(1))
    return texts
