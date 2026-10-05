from flask import Blueprint, render_template, request

from .. import db

bp = Blueprint("search", __name__, url_prefix="/search")


@bp.route("")
def search_view():
    query_text = request.args.get("q", "")
    results = db.search_notes(query_text) if query_text.strip() else []
    return render_template("search/results.html", query_text=query_text, results=results)
