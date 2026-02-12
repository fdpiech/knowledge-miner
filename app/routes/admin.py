"""Admin routes for index management and settings."""

import logging

from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from sqlalchemy import func

from app.models import File, db
from app.indexer import index_corpus, reindex_changed

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
def admin_page():
    """Show index management and settings page."""
    total_files = db.session.query(func.count(File.id)).scalar() or 0
    last_indexed = db.session.query(func.max(File.indexed_at)).scalar()
    corpus_root = current_app.config["KCM"]["corpus"]["root_path"]

    return render_template(
        "admin.html",
        total_files=total_files,
        last_indexed=last_indexed,
        corpus_root=corpus_root,
    )


@admin_bp.route("/reindex", methods=["POST"])
def reindex():
    """Trigger a full reindex of the corpus."""
    corpus_root = current_app.config["KCM"]["corpus"]["root_path"]
    if not corpus_root:
        flash("Corpus root path is not configured. Set KCM_CORPUS_ROOT or update config.yaml.", "danger")
        return redirect(url_for("admin.admin_page"))

    indexer_config = current_app.config["KCM"].get("indexer", {})
    skip_patterns = indexer_config.get("skip_patterns")
    supported_extensions = indexer_config.get("supported_extensions")

    try:
        stats = index_corpus(
            root_path=corpus_root,
            db_session=db.session,
            skip_patterns=skip_patterns,
            supported_extensions=supported_extensions,
        )
        flash(
            f"Full reindex complete. "
            f"New: {stats['new']}, Updated: {stats['updated']}, "
            f"Unchanged: {stats['unchanged']}, Deleted: {stats['deleted']}, "
            f"Total scanned: {stats['total']}",
            "success",
        )
    except Exception as e:
        logger.exception("Reindex failed")
        flash(f"Reindex failed: {e}", "danger")

    return redirect(url_for("admin.admin_page"))


@admin_bp.route("/reindex-incremental", methods=["POST"])
def reindex_incremental():
    """Trigger an incremental reindex (only changed files)."""
    corpus_root = current_app.config["KCM"]["corpus"]["root_path"]
    if not corpus_root:
        flash("Corpus root path is not configured. Set KCM_CORPUS_ROOT or update config.yaml.", "danger")
        return redirect(url_for("admin.admin_page"))

    indexer_config = current_app.config["KCM"].get("indexer", {})
    skip_patterns = indexer_config.get("skip_patterns")
    supported_extensions = indexer_config.get("supported_extensions")

    try:
        stats = reindex_changed(
            root_path=corpus_root,
            db_session=db.session,
            skip_patterns=skip_patterns,
            supported_extensions=supported_extensions,
        )
        flash(
            f"Incremental reindex complete. "
            f"New: {stats['new']}, Updated: {stats['updated']}, "
            f"Unchanged: {stats['unchanged']}, "
            f"Total scanned: {stats['total']}",
            "success",
        )
    except Exception as e:
        logger.exception("Incremental reindex failed")
        flash(f"Incremental reindex failed: {e}", "danger")

    return redirect(url_for("admin.admin_page"))
