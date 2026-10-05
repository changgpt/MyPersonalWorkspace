from types import SimpleNamespace
from unittest.mock import patch

import pytest

from daybook import ai
from daybook import db as db_module


def _fake_response(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


# --- Pure parsing helpers: no network, no app context needed ---------------

def test_parse_bullet_list_strips_dash_prefix():
    text = "- First item\n- Second item\n"
    assert ai.parse_bullet_list(text) == ["First item", "Second item"]


def test_parse_bullet_list_ignores_non_bullet_lines():
    text = "Here are some ideas:\n- Real item\nJust a sentence\n"
    assert ai.parse_bullet_list(text) == ["Real item"]


def test_parse_bullet_list_empty_input():
    assert ai.parse_bullet_list("") == []
    assert ai.parse_bullet_list(None) == []


def test_parse_weekly_draft_well_formed():
    text = (
        "WENT WELL: Shipped the migration.\n"
        "TO IMPROVE: Start testing earlier.\n"
        "FOCUS NEXT WEEK: Kick off Q4 planning."
    )
    result = ai.parse_weekly_draft(text)
    assert result["went_well"] == "Shipped the migration."
    assert result["to_improve"] == "Start testing earlier."
    assert result["focus_next_week"] == "Kick off Q4 planning."


def test_parse_weekly_draft_falls_back_when_labels_missing():
    result = ai.parse_weekly_draft("Just some free text with no labels.")
    assert result["went_well"] == "Just some free text with no labels."
    assert result["to_improve"] == ""
    assert result["focus_next_week"] == ""


# --- Enablement checks: need an app context (config + settings table) ------

def test_is_ai_enabled_requires_both_key_and_toggle(app, db):
    with app.app_context():
        app.config["ANTHROPIC_API_KEY"] = ""
        assert ai.api_key_configured() is False
        assert ai.is_ai_enabled() is False

        app.config["ANTHROPIC_API_KEY"] = "sk-test-key"
        assert ai.api_key_configured() is True
        assert ai.is_ai_enabled() is False  # toggle still off

        db_module.set_setting("ai_features_enabled", "1")
        assert ai.is_ai_enabled() is True

        db_module.set_setting("ai_features_enabled", "0")
        assert ai.is_ai_enabled() is False


def test_complete_raises_when_ai_disabled(app, db):
    with app.app_context():
        app.config["ANTHROPIC_API_KEY"] = ""
        with pytest.raises(ai.AIError):
            ai._complete("irrelevant prompt")


# --- The three features, with the network call mocked out -----------------

def test_summarize_note_calls_api_and_returns_text(app, db):
    with app.app_context():
        app.config["ANTHROPIC_API_KEY"] = "sk-test-key"
        db_module.set_setting("ai_features_enabled", "1")

        fake_client = SimpleNamespace(
            messages=SimpleNamespace(create=lambda **kwargs: _fake_response("A short summary."))
        )
        with patch("daybook.ai._client", return_value=fake_client):
            result = ai.summarize_note("Some note body with lots of detail.")
        assert result == "A short summary."


def test_suggest_action_items_parses_bullets(app, db):
    with app.app_context():
        app.config["ANTHROPIC_API_KEY"] = "sk-test-key"
        db_module.set_setting("ai_features_enabled", "1")

        fake_client = SimpleNamespace(
            messages=SimpleNamespace(
                create=lambda **kwargs: _fake_response("- Call the vendor\n- Send the invoice")
            )
        )
        with patch("daybook.ai._client", return_value=fake_client):
            result = ai.suggest_action_items("Note mentioning a vendor call and an invoice.")
        assert result == ["Call the vendor", "Send the invoice"]


def test_draft_weekly_review_parses_sections(app, db):
    with app.app_context():
        app.config["ANTHROPIC_API_KEY"] = "sk-test-key"
        db_module.set_setting("ai_features_enabled", "1")

        draft_text = "WENT WELL: Good week.\nTO IMPROVE: Fewer meetings.\nFOCUS NEXT WEEK: Planning."
        fake_client = SimpleNamespace(
            messages=SimpleNamespace(create=lambda **kwargs: _fake_response(draft_text))
        )
        summary = dict(
            notes_by_type=[], tasks_completed=[], tasks_open_or_overdue=[],
            skills_touched=[], wins=[],
        )
        with patch("daybook.ai._client", return_value=fake_client):
            result = ai.draft_weekly_review(summary)
        assert result["went_well"] == "Good week."
        assert result["focus_next_week"] == "Planning."


def test_complete_wraps_api_errors(app, db):
    with app.app_context():
        app.config["ANTHROPIC_API_KEY"] = "sk-test-key"
        db_module.set_setting("ai_features_enabled", "1")

        import anthropic

        def raise_error(**kwargs):
            raise anthropic.APIConnectionError(request=SimpleNamespace())

        fake_client = SimpleNamespace(messages=SimpleNamespace(create=raise_error))
        with patch("daybook.ai._client", return_value=fake_client):
            with pytest.raises(ai.AIError):
                ai.summarize_note("Body text")
