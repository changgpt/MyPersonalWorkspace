from flask import Flask

from . import config, db
from .markdown_utils import render_markdown


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)

    @app.template_filter("markdown")
    def markdown_filter(text):
        return render_markdown(text)

    from .blueprints import (
        activity, dashboard, notes, people, projects, skills, tasks, topics,
        search, settings, weekly_review, wins,
    )

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(notes.bp)
    app.register_blueprint(people.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(tasks.bp)
    app.register_blueprint(topics.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(skills.bp)
    app.register_blueprint(wins.bp)
    app.register_blueprint(activity.bp)
    app.register_blueprint(weekly_review.bp)

    return app
