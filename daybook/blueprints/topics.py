from flask import Blueprint, abort, flash, redirect, render_template, url_for

from .. import db

bp = Blueprint("topics", __name__, url_prefix="/topics")


@bp.route("")
def list_view():
    return render_template("topics/list.html", topics=db.list_topics())


@bp.route("/<int:topic_id>")
def detail_view(topic_id):
    topic = db.get_topic(topic_id)
    if topic is None:
        abort(404)
    notes = db.notes_for_topic(topic_id)
    return render_template("topics/detail.html", topic=topic, notes=notes)


@bp.route("/<int:topic_id>/delete", methods=["POST"])
def delete_view(topic_id):
    topic = db.get_topic(topic_id)
    if topic is None:
        abort(404)
    db.delete_topic(topic_id)
    flash(f"Deleted {topic['name']}.")
    return redirect(url_for("topics.list_view"))
