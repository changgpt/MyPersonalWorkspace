from flask import Blueprint, render_template

from .. import config, db, greetings, internship

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
        internship_week=internship.week_number(config.INTERNSHIP_START_DATE),
        internship_days_left=internship.days_remaining(config.INTERNSHIP_END_DATE),
        # Built manually rather than with strftime("%b %-d, %Y") -- "%-d"
        # (no leading zero) is a glibc/macOS extension, not available on
        # Windows' C runtime, and this app needs to run there too.
        internship_end_date_display=(
            f"{config.INTERNSHIP_END_DATE:%B} {config.INTERNSHIP_END_DATE.day}, "
            f"{config.INTERNSHIP_END_DATE:%Y}"
        ),
    )
