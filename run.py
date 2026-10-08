import sys

from daybook import create_app, db, seed

app = create_app()

if __name__ == "__main__":
    # `python run.py --check-outlook` reports why the Dashboard's "Coming
    # up" card is empty. It lives here, rather than only as `flask
    # outlook-check`, because the problems it diagnoses are environment
    # ones: on Windows `flask` is often not on PATH for the same reason
    # pywin32 lands in a different interpreter than the app, and needing
    # FLASK_APP set first is more plumbing in the way of an answer.
    # `python run.py` is the one command already known to work.
    if "--check-outlook" in sys.argv:
        from daybook import calendar_sources

        calendar_sources.diagnose()
        raise SystemExit(0)

    # Same reasoning: pointing someone at `flask outlook-login` is no use
    # when `flask` isn't on their PATH, which is the situation this whole
    # Graph path exists for in the first place.
    if "--outlook-login" in sys.argv:
        from daybook import calendar_sources

        try:
            calendar_sources.GraphSource().sign_in()
        except calendar_sources.CalendarError as exc:
            print(f"Sign-in failed: {exc}")
            raise SystemExit(1)
        print("Signed in. The Dashboard's Coming up card will use Microsoft Graph.")
        raise SystemExit(0)

    # Equivalent to running `flask init-db` first -- idempotent (creates
    # tables/columns that don't exist yet, seeds note types only if empty),
    # so running it on every startup means a schema change (like adding a
    # column) never needs a separate manual migration step before the app
    # will start without erroring.
    with app.app_context():
        db.init_db()
        seed.seed_note_types(db.get_db())
        seed.migrate_default_templates(db.get_db())

    # Bound to 127.0.0.1 only: this app is local-only, never exposed on the network.
    app.run(host="127.0.0.1", port=5000, debug=True)
