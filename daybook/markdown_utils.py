"""Markdown -> HTML rendering for note bodies.

Uses python-markdown with a couple of extensions:
- fenced_code / tables: common Markdown conveniences
- sane_lists: more predictable list parsing
- pymdownx.tasklist: renders "- [ ] foo" as a checkbox, which also sets up
  Phase 2 (where checked boxes become linked tasks) visually from day one
"""
import markdown

_MD = markdown.Markdown(
    extensions=[
        "fenced_code",
        "tables",
        "sane_lists",
        "pymdownx.tasklist",
    ],
    extension_configs={
        "pymdownx.tasklist": {"custom_checkbox": True},
    },
)


def render_markdown(text):
    _MD.reset()
    return _MD.convert(text or "")
