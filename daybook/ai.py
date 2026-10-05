"""Optional AI features (Phase 4) -- summarize a note, suggest action items,
draft a weekly review. Off by default: see is_ai_enabled().

Only `_complete` touches the network; everything else here is pure text
processing, kept separate so the parsing logic is testable without
mocking an API call. Uses the Anthropic Python SDK (`anthropic` package),
never raw HTTP.
"""
import re

import anthropic
from flask import current_app

from . import db

EFFORT = "low"  # these are short, simple calls -- summarize, extract, draft


class AIError(Exception):
    """Raised when a call to the Anthropic API fails or AI features are off."""


def api_key_configured():
    return bool(current_app.config.get("ANTHROPIC_API_KEY"))


def is_ai_enabled():
    return api_key_configured() and db.get_setting("ai_features_enabled") == "1"


def _client():
    return anthropic.Anthropic(api_key=current_app.config["ANTHROPIC_API_KEY"])


def _complete(prompt, max_tokens=1024):
    if not is_ai_enabled():
        raise AIError("AI features are not enabled.")
    try:
        response = _client().messages.create(
            model=current_app.config["ANTHROPIC_MODEL"],
            max_tokens=max_tokens,
            output_config={"effort": EFFORT},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        raise AIError(f"Anthropic API request failed: {exc}") from exc
    return "".join(block.text for block in response.content if block.type == "text")


# --- Pure parsing helpers (no network, easy to unit test) ------------------

def parse_bullet_list(text):
    items = []
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif line.startswith("-"):
            items.append(line[1:].strip())
    return [item for item in items if item]


def parse_weekly_draft(text):
    match = re.search(
        r"WENT WELL:(.*?)TO IMPROVE:(.*?)FOCUS NEXT WEEK:(.*)",
        text or "", re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return {"went_well": (text or "").strip(), "to_improve": "", "focus_next_week": ""}
    return {
        "went_well": match.group(1).strip(),
        "to_improve": match.group(2).strip(),
        "focus_next_week": match.group(3).strip(),
    }


def _summary_digest(summary):
    def join(rows, key):
        values = [row[key] for row in rows]
        return ", ".join(values) if values else "none"

    return "\n".join([
        "Notes by type: " + join(summary["notes_by_type"], "type_name"),
        "Tasks completed: " + join(summary["tasks_completed"], "title"),
        "Tasks still open or overdue: " + join(summary["tasks_open_or_overdue"], "title"),
        "Skills touched: " + join(summary["skills_touched"], "name"),
        "Wins: " + join(summary["wins"], "title"),
    ])


# --- The three AI features --------------------------------------------------

def summarize_note(body_markdown):
    prompt = (
        "Summarize the following work note in 2-3 concise sentences. "
        "Return only the summary text, nothing else.\n\nNOTE:\n" + body_markdown
    )
    return _complete(prompt, max_tokens=256).strip()


def suggest_action_items(body_markdown):
    prompt = (
        "Read the following work note and propose concrete follow-up action items. "
        "Return ONLY a bullet list, one item per line, each starting with '- '. "
        "If there are no clear action items, return nothing.\n\nNOTE:\n" + body_markdown
    )
    return parse_bullet_list(_complete(prompt, max_tokens=512))


def draft_weekly_review(summary):
    prompt = (
        "Here is a summary of this week's work activity:\n\n"
        + _summary_digest(summary)
        + "\n\nBased on this, draft a brief weekly reflection in exactly this format "
        "(replace the bracketed text, keep the labels on their own lines):\n"
        "WENT WELL: [1-2 sentences]\n"
        "TO IMPROVE: [1-2 sentences]\n"
        "FOCUS NEXT WEEK: [1-2 sentences]"
    )
    return parse_weekly_draft(_complete(prompt, max_tokens=512))
