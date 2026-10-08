from flask import Flask

from . import config, db
from .calendar_utils import format_time_range, note_prefill
from .date_utils import human_date, human_date_range
from .markdown_utils import render_markdown


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)

    @app.template_filter("markdown")
    def markdown_filter(text):
        return render_markdown(text)

    app.add_template_filter(human_date, "human_date")
    app.add_template_filter(human_date_range, "human_date_range")
    app.add_template_filter(format_time_range, "time_range")
    app.add_template_filter(note_prefill, "note_prefill")

    from .blueprints import (
        calendar, dashboard, notes, people, projects, skills, tasks, topics,
        search, settings, weekly_review,
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
    app.register_blueprint(weekly_review.bp)
    app.register_blueprint(calendar.bp)
    app.cli.add_command(calendar.outlook_login_command)
    app.cli.add_command(calendar.outlook_check_command)

    return app
