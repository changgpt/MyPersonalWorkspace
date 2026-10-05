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

    from .blueprints import dashboard, notes, people, projects, tasks, topics, search, settings

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(notes.bp)
    app.register_blueprint(people.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(tasks.bp)
    app.register_blueprint(topics.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(settings.bp)

    return app
