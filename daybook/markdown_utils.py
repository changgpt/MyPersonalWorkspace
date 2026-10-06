"""Markdown -> HTML rendering for note bodies.

Uses python-markdown with a couple of extensions:
- fenced_code / tables: common Markdown conveniences
- sane_lists: more predictable list parsing
- nl2br: a single line break in the source becomes a <br>, instead of
  standard Markdown's behaviour of collapsing it into the same paragraph
  as the next line -- without this, typed-out spacing within a paragraph
  is silently lost on render
- pymdownx.tasklist: renders "- [ ] foo" as a checkbox, which also sets up
  Phase 2 (where checked boxes become linked tasks) visually from day one
"""
import markdown

_MD = markdown.Markdown(
    extensions=[
        "fenced_code",
        "tables",
        "sane_lists",
        "nl2br",
        "pymdownx.tasklist",
    ],
    extension_configs={
        "pymdownx.tasklist": {"custom_checkbox": True},
    },
)


def render_markdown(text):
    _MD.reset()
    return _MD.convert(text or "")
