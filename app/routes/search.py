"""Search interface and results routes."""

from flask import Blueprint, render_template, request
from sqlalchemy import func

from app.models import File, db
from app.search import parse_search_params, execute_search

search_bp = Blueprint("search", __name__, url_prefix="/search")


@search_bp.route("/")
def search_page():
    """Render the search form with filter options."""
    # Get available extensions and sections for filter dropdowns
    extensions = (
        db.session.query(File.file_extension)
        .distinct()
        .order_by(File.file_extension)
        .all()
    )
    sections = (
        db.session.query(File.corpus_section)
        .filter(File.corpus_section.isnot(None))
        .distinct()
        .order_by(File.corpus_section)
        .all()
    )

    return render_template(
        "search.html",
        extensions=[e[0] for e in extensions],
        sections=[s[0] for s in sections],
    )


@search_bp.route("/results")
def search_results():
    """Execute search and return results (htmx partial or full page)."""
    params = parse_search_params(request.args)
    results = execute_search(params)

    # Get available extensions and sections for the form
    extensions = (
        db.session.query(File.file_extension)
        .distinct()
        .order_by(File.file_extension)
        .all()
    )
    sections = (
        db.session.query(File.corpus_section)
        .filter(File.corpus_section.isnot(None))
        .distinct()
        .order_by(File.corpus_section)
        .all()
    )

    # Check if this is an htmx request
    is_htmx = request.headers.get("HX-Request") == "true"

    if is_htmx:
        return render_template(
            "_search_results.html",
            results=results,
            params=params,
        )

    return render_template(
        "search.html",
        extensions=[e[0] for e in extensions],
        sections=[s[0] for s in sections],
        results=results,
        params=params,
    )
