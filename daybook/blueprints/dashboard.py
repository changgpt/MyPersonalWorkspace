from flask import Blueprint, render_template

from .. import db

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    recent_notes = db.list_notes()[:8]
    return render_template("dashboard.html", recent_notes=recent_notes)
