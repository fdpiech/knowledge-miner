"""File system indexer for the knowledge corpus.

Walks the corpus directory, extracts metadata, and upserts records
into the database. Supports both full and incremental indexing.
"""

import fnmatch
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from sqlalchemy.orm import Session

from app.models import File

logger = logging.getLogger(__name__)

# Default patterns to skip
DEFAULT_SKIP_PATTERNS = ["~$*", "*.tmp", "Thumbs.db", ".DS_Store"]
DEFAULT_SUPPORTED_EXTENSIONS = [".md", ".docx", ".xlsx", ".pdf", ".vsdx", ".txt", ".csv"]


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file's contents.

    Args:
        file_path: Path to the file.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _should_skip(name: str, skip_patterns: list[str]) -> bool:
    """Check if a file or directory name matches any skip pattern."""
    for pattern in skip_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def determine_corpus_section(relative_path: str) -> str | None:
    """Map a file's relative path to a corpus section label.

    The section is derived from the top-level directory name within
    the corpus root.

    Args:
        relative_path: File path relative to the corpus root.

    Returns:
        Section label string, or None if the file is at the root level.
    """
    parts = Path(relative_path).parts
    if len(parts) <= 1:
        return None
    return parts[0]


def walk_corpus(
    root_path: Path,
    skip_patterns: list[str] | None = None,
    supported_extensions: list[str] | None = None,
) -> Generator[dict, None, None]:
    """Walk the corpus directory and yield metadata dicts for each eligible file.

    Args:
        root_path: Absolute path to the corpus root directory.
        skip_patterns: Glob patterns for files/dirs to skip.
        supported_extensions: File extensions to include (with leading dot).

    Yields:
        Dictionary with file metadata keys.
    """
    if skip_patterns is None:
        skip_patterns = DEFAULT_SKIP_PATTERNS
    if supported_extensions is None:
        supported_extensions = DEFAULT_SUPPORTED_EXTENSIONS

    root = Path(root_path)
    if not root.is_dir():
        logger.error("Corpus root does not exist or is not a directory: %s", root)
        return

    for item in sorted(root.rglob("*")):
        # Skip directories themselves (we only index files)
        if item.is_dir():
            continue

        # Skip hidden files and directories
        parts = item.relative_to(root).parts
        if any(part.startswith(".") for part in parts):
            continue

        # Skip noise files
        if _should_skip(item.name, skip_patterns):
            continue

        # Filter by extension
        ext = item.suffix.lower()
        if ext not in supported_extensions:
            continue

        relative_path = str(item.relative_to(root))
        stat = item.stat()

        yield {
            "file_path": relative_path,
            "file_name": item.name,
            "file_extension": ext,
            "file_size_bytes": stat.st_size,
            "parent_dir": str(item.parent.relative_to(root)) if item.parent != root else "",
            "corpus_section": determine_corpus_section(relative_path),
            "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            "absolute_path": str(item),
        }


def index_corpus(
    root_path: str,
    db_session: Session,
    skip_patterns: list[str] | None = None,
    supported_extensions: list[str] | None = None,
) -> dict[str, int]:
    """Run a full index of the corpus directory.

    Walks the entire tree, upserts file records, and removes records
    for files that no longer exist on disk.

    Args:
        root_path: Path to the corpus root directory.
        db_session: SQLAlchemy database session.
        skip_patterns: Glob patterns for files/dirs to skip.
        supported_extensions: File extensions to include.

    Returns:
        Stats dict with keys: new, updated, unchanged, deleted, total.
    """
    root = Path(root_path)
    stats = {"new": 0, "updated": 0, "unchanged": 0, "deleted": 0, "total": 0}
    seen_paths: set[str] = set()

    for meta in walk_corpus(root, skip_patterns, supported_extensions):
        stats["total"] += 1
        rel_path = meta["file_path"]
        seen_paths.add(rel_path)

        try:
            file_hash = compute_file_hash(Path(meta["absolute_path"]))
        except (OSError, PermissionError) as e:
            logger.warning("Could not hash file %s: %s", rel_path, e)
            continue

        existing = db_session.query(File).filter_by(file_path=rel_path).first()

        if existing:
            if existing.file_hash == file_hash:
                stats["unchanged"] += 1
                continue

            # Update existing record
            existing.file_name = meta["file_name"]
            existing.file_extension = meta["file_extension"]
            existing.file_size_bytes = meta["file_size_bytes"]
            existing.parent_dir = meta["parent_dir"]
            existing.corpus_section = meta["corpus_section"]
            existing.created_at = meta["created_at"]
            existing.modified_at = meta["modified_at"]
            existing.indexed_at = datetime.now(timezone.utc)
            existing.file_hash = file_hash
            stats["updated"] += 1
        else:
            # Create new record
            new_file = File(
                file_path=rel_path,
                file_name=meta["file_name"],
                file_extension=meta["file_extension"],
                file_size_bytes=meta["file_size_bytes"],
                parent_dir=meta["parent_dir"],
                corpus_section=meta["corpus_section"],
                created_at=meta["created_at"],
                modified_at=meta["modified_at"],
                indexed_at=datetime.now(timezone.utc),
                file_hash=file_hash,
            )
            db_session.add(new_file)
            stats["new"] += 1

    # Remove records for files that no longer exist
    all_indexed = db_session.query(File).all()
    for record in all_indexed:
        if record.file_path not in seen_paths:
            db_session.delete(record)
            stats["deleted"] += 1

    db_session.commit()
    return stats


def reindex_changed(
    root_path: str,
    db_session: Session,
    skip_patterns: list[str] | None = None,
    supported_extensions: list[str] | None = None,
) -> dict[str, int]:
    """Incremental reindex: only process new or changed files.

    Compares file hashes to detect changes. Does not remove deleted files
    (use full index_corpus for that).

    Args:
        root_path: Path to the corpus root directory.
        db_session: SQLAlchemy database session.
        skip_patterns: Glob patterns for files/dirs to skip.
        supported_extensions: File extensions to include.

    Returns:
        Stats dict with keys: new, updated, unchanged, total.
    """
    root = Path(root_path)
    stats = {"new": 0, "updated": 0, "unchanged": 0, "total": 0}

    for meta in walk_corpus(root, skip_patterns, supported_extensions):
        stats["total"] += 1
        rel_path = meta["file_path"]

        try:
            file_hash = compute_file_hash(Path(meta["absolute_path"]))
        except (OSError, PermissionError) as e:
            logger.warning("Could not hash file %s: %s", rel_path, e)
            continue

        existing = db_session.query(File).filter_by(file_path=rel_path).first()

        if existing:
            if existing.file_hash == file_hash:
                stats["unchanged"] += 1
                continue

            existing.file_name = meta["file_name"]
            existing.file_extension = meta["file_extension"]
            existing.file_size_bytes = meta["file_size_bytes"]
            existing.parent_dir = meta["parent_dir"]
            existing.corpus_section = meta["corpus_section"]
            existing.created_at = meta["created_at"]
            existing.modified_at = meta["modified_at"]
            existing.indexed_at = datetime.now(timezone.utc)
            existing.file_hash = file_hash
            stats["updated"] += 1
        else:
            new_file = File(
                file_path=rel_path,
                file_name=meta["file_name"],
                file_extension=meta["file_extension"],
                file_size_bytes=meta["file_size_bytes"],
                parent_dir=meta["parent_dir"],
                corpus_section=meta["corpus_section"],
                created_at=meta["created_at"],
                modified_at=meta["modified_at"],
                indexed_at=datetime.now(timezone.utc),
                file_hash=file_hash,
            )
            db_session.add(new_file)
            stats["new"] += 1

    db_session.commit()
    return stats
