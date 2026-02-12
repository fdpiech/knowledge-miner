"""Directory tree browsing routes."""

from pathlib import PurePosixPath

from flask import Blueprint, render_template, current_app, abort
from sqlalchemy import func

from app.models import File, db

browse_bp = Blueprint("browse", __name__, url_prefix="/browse")


def _get_tree_entries(parent_dir: str) -> dict:
    """Get directories and files under a given parent directory.

    Args:
        parent_dir: The parent directory path (relative to corpus root).

    Returns:
        Dict with 'directories' (list of dicts) and 'files' (list of File objects).
    """
    # Find all distinct subdirectories at this level
    if parent_dir:
        prefix = parent_dir + "/"
        # Get files directly in this directory
        files = (
            File.query.filter(File.parent_dir == parent_dir)
            .order_by(File.file_name)
            .all()
        )
        # Get unique child directory names
        child_dirs_query = (
            db.session.query(File.parent_dir)
            .filter(File.parent_dir.like(f"{prefix}%"))
            .distinct()
            .all()
        )
    else:
        # Root level
        files = (
            File.query.filter(File.parent_dir == "")
            .order_by(File.file_name)
            .all()
        )
        child_dirs_query = (
            db.session.query(File.parent_dir)
            .filter(File.parent_dir != "")
            .distinct()
            .all()
        )

    # Extract immediate child directory names
    child_dir_names: set[str] = set()
    for (dir_path,) in child_dirs_query:
        if parent_dir:
            # Remove the prefix and get the first component
            relative = dir_path[len(parent_dir) + 1:]
        else:
            relative = dir_path

        if relative:
            first_component = relative.split("/")[0]
            child_dir_names.add(first_component)

    directories = []
    for name in sorted(child_dir_names):
        full_path = f"{parent_dir}/{name}" if parent_dir else name
        # Count files under this directory
        count = (
            db.session.query(func.count(File.id))
            .filter(
                (File.parent_dir == full_path) | (File.parent_dir.like(f"{full_path}/%"))
            )
            .scalar()
        )
        directories.append({"name": name, "path": full_path, "file_count": count})

    return {"directories": directories, "files": files}


@browse_bp.route("/")
def browse_root():
    """Show the top-level corpus directory structure."""
    entries = _get_tree_entries("")
    return render_template(
        "browse.html",
        entries=entries,
        current_path="",
        breadcrumbs=[],
    )


@browse_bp.route("/<path:dir_path>")
def browse_dir(dir_path: str):
    """Show contents of a specific directory.

    Args:
        dir_path: Relative directory path within the corpus.
    """
    entries = _get_tree_entries(dir_path)

    # Build breadcrumbs
    parts = PurePosixPath(dir_path).parts
    breadcrumbs = []
    for i, part in enumerate(parts):
        breadcrumbs.append({
            "name": part,
            "path": "/".join(parts[: i + 1]),
        })

    return render_template(
        "browse.html",
        entries=entries,
        current_path=dir_path,
        breadcrumbs=breadcrumbs,
    )


@browse_bp.route("/partial/<path:dir_path>")
def browse_partial(dir_path: str):
    """Return a partial HTML fragment for htmx lazy-loading of subdirectories."""
    entries = _get_tree_entries(dir_path)
    return render_template("_browse_entries.html", entries=entries, current_path=dir_path)


@browse_bp.route("/file/<int:file_id>")
def file_detail(file_id: int):
    """Show metadata detail for a single file."""
    file = File.query.get_or_404(file_id)

    # Build breadcrumbs from file path
    parts = PurePosixPath(file.parent_dir).parts if file.parent_dir else ()
    breadcrumbs = []
    for i, part in enumerate(parts):
        breadcrumbs.append({
            "name": part,
            "path": "/".join(parts[: i + 1]),
        })

    corpus_root = current_app.config["KCM"]["corpus"]["root_path"]

    return render_template(
        "file_detail.html",
        file=file,
        breadcrumbs=breadcrumbs,
        corpus_root=corpus_root,
    )
