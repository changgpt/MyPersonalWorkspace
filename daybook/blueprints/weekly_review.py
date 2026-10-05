from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from .. import ai, db

bp = Blueprint("weekly_review", __name__, url_prefix="/weekly-review")


@bp.route("")
def current_view():
    return redirect(url_for("weekly_review.detail_view", week_str=db.current_week_str()))


@bp.route("/<week_str>")
def detail_view(week_str):
    review = db.get_weekly_review(week_str)
    return render_template(
        "weekly_review/detail.html",
        week_str=week_str,
        review=review,
        summary=db.weekly_review_summary(week_str),
        prev_week=db.adjacent_week_str(week_str, -1),
        next_week=db.adjacent_week_str(week_str, 1),
        ai_enabled=ai.is_ai_enabled(),
    )


@bp.route("/<week_str>/ai-draft", methods=["POST"])
def ai_draft_view(week_str):
    try:
        draft = ai.draft_weekly_review(db.weekly_review_summary(week_str))
        db.save_weekly_review(week_str, **draft)
    except ai.AIError as exc:
        flash(str(exc))
    return redirect(url_for("weekly_review.detail_view", week_str=week_str))


@bp.route("/<week_str>", methods=["POST"])
def save_view(week_str):
    form = request.form
    db.save_weekly_review(
        week_str,
        went_well=form.get("went_well", ""),
        to_improve=form.get("to_improve", ""),
        focus_next_week=form.get("focus_next_week", ""),
    )
    return redirect(url_for("weekly_review.detail_view", week_str=week_str))


@bp.route("/<week_str>/export")
def export_view(week_str):
    review = db.get_weekly_review(week_str)
    summary = db.weekly_review_summary(week_str)
    lines = [f"# Weekly review — {week_str}\n", f"{summary['week_start']} to {summary['week_end']}\n"]

    lines.append("## Notes by type")
    for row in summary["notes_by_type"]:
        lines.append(f"- {row['type_name']}: {row['count']}")

    lines.append("\n## Tasks completed")
    for task in summary["tasks_completed"]:
        lines.append(f"- {task['title']}")

    lines.append("\n## Tasks still open or overdue")
    for task in summary["tasks_open_or_overdue"]:
        lines.append(f"- {task['title']} ({task['status']})")

    lines.append("\n## Skills touched")
    for skill in summary["skills_touched"]:
        lines.append(f"- {skill['name']}")

    lines.append("\n## Wins")
    for win in summary["wins"]:
        lines.append(f"- {win['title']}")

    if review:
        lines.append("\n## Went well")
        lines.append(review["went_well"] or "")
        lines.append("\n## To improve")
        lines.append(review["to_improve"] or "")
        lines.append("\n## Focus for next week")
        lines.append(review["focus_next_week"] or "")

    markdown_text = "\n".join(lines)
    return Response(
        markdown_text,
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=weekly-review-{week_str}.md"},
    )
