from daybook import create_app, db, seed

app = create_app()

if __name__ == "__main__":
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
