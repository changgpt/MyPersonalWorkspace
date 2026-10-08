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
- pymdownx.tilde: "~~struck~~" -> <del>, so the editor's strikethrough
  button has something to round-trip to. Subscript (its other half) is
  switched off: a single "~" is ordinary punctuation in a note, and
  silently turning it into <sub> would be a nasty surprise
"""
import markdown

_MD = markdown.Markdown(
    extensions=[
        "fenced_code",
        "tables",
        "sane_lists",
        "nl2br",
        "pymdownx.tasklist",
        "pymdownx.tilde",
    ],
    extension_configs={
        "pymdownx.tasklist": {"custom_checkbox": True},
        "pymdownx.tilde": {"subscript": False},
    },
)


def render_markdown(text):
    _MD.reset()
    return _MD.convert(text or "")
