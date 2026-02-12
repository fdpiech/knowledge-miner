"""Dashboard and navigation routes."""

from flask import Blueprint, render_template, current_app
from sqlalchemy import func

from app.models import File, ConsolidationJob, db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def dashboard():
    """Render the main dashboard with corpus statistics."""
    total_files = db.session.query(func.count(File.id)).scalar() or 0
    total_size = db.session.query(func.sum(File.file_size_bytes)).scalar() or 0

    # Files by extension
    ext_counts = (
        db.session.query(File.file_extension, func.count(File.id))
        .group_by(File.file_extension)
        .order_by(func.count(File.id).desc())
        .all()
    )

    # Files by section
    section_counts = (
        db.session.query(File.corpus_section, func.count(File.id))
        .group_by(File.corpus_section)
        .order_by(func.count(File.id).desc())
        .all()
    )

    # Last index time
    last_indexed = db.session.query(func.max(File.indexed_at)).scalar()

    # Recent files (last 10 modified)
    recent_files = (
        File.query.order_by(File.modified_at.desc()).limit(10).all()
    )

    # Total consolidation jobs
    total_jobs = db.session.query(func.count(ConsolidationJob.id)).scalar() or 0

    corpus_root = current_app.config["KCM"]["corpus"]["root_path"]

    return render_template(
        "dashboard.html",
        total_files=total_files,
        total_size=total_size,
        ext_counts=ext_counts,
        section_counts=section_counts,
        last_indexed=last_indexed,
        recent_files=recent_files,
        total_jobs=total_jobs,
        corpus_root=corpus_root,
    )
