"""Two CSS rules whose breakage is invisible to every other test.

Neither is a style preference: each one shipped, broke a control outright,
and was reported by the user. A string check over the stylesheet is crude,
but it's the only place to catch a re-introduction short of driving a
browser, and both bugs are a single property.
"""
import re
from pathlib import Path

STYLE = (Path(__file__).resolve().parent.parent / "daybook" / "static" / "style.css").read_text()


def _rule(selector):
    """The declaration block for `selector { ... }`, as written."""
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", STYLE)
    assert match, f"{selector} is gone from style.css"
    return match.group(1)


def test_compose_pills_never_clip_their_dropdown():
    # A pill holds a custom <select> whose panel is an absolutely
    # positioned child. `overflow: hidden` on the pill clipped the open
    # dropdown out of existence -- the Priority/Category/Level controls
    # looked simply broken -- and made the pill scroll sideways, chopping
    # its own label off. The round ends come from the controls' own
    # border-radius instead.
    for selector in (".compose-pill", ".compose-pills"):
        assert "overflow" not in _rule(selector), selector


def test_the_compose_title_override_is_qualified_by_its_element():
    # The base control rule (`input[type="text"], ...`) is (0,1,1), so a
    # bare `.compose-title` class loses to it however late it appears --
    # which once left the note title boxed at 14px. Tying on specificity
    # with the element name is what makes it win on source order.
    assert "input.compose-title {" in STYLE
