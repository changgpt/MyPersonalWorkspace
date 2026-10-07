from flask import Blueprint, render_template

from .. import config, db, greetings

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    recent_notes = db.list_notes()[:8]
    today_tasks = db.list_today_flagged_tasks()
    return render_template(
        "dashboard.html",
        recent_notes=recent_notes,
        today_tasks=today_tasks,
        overdue_tasks=db.list_overdue_tasks(),
        completed_this_week=db.list_tasks_completed_this_week(),
        greeting=greetings.greeting_message(config.DISPLAY_NAME),
        quote=greetings.random_quote(),
    )
