from flask import Blueprint, render_template

from .. import config, date_utils, db, greetings, internship

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    recent_notes = db.list_notes()[:8]
    overdue_tasks = db.list_overdue_tasks()
    # An overdue task in the "today" bucket satisfies both queries, and the
    # dashboard shows the two lists one above the other -- so it would
    # otherwise appear twice on the same screen. Overdue wins: it's the
    # more urgent framing, and it's the section further down the page.
    # Overdue stays on the Dashboard even though "Completed this week" was
    # dropped: the filter below removes overdue tasks from the today list,
    # so without its own section an overdue task would vanish from the page
    # entirely rather than merely being listed twice.
    overdue_ids = {task["id"] for task in overdue_tasks}
    today_tasks = [t for t in db.list_today_flagged_tasks() if t["id"] not in overdue_ids]
    return render_template(
        "dashboard.html",
        recent_notes=recent_notes,
        today_tasks=today_tasks,
        overdue_tasks=overdue_tasks,
        greeting=greetings.greeting_message(config.DISPLAY_NAME),
        quote=greetings.random_quote(),
        internship_week=internship.week_number(config.INTERNSHIP_START_DATE),
        internship_days_left=internship.days_remaining(config.INTERNSHIP_END_DATE),
        internship_end_date_display=date_utils.human_date(config.INTERNSHIP_END_DATE),
    )
