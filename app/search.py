"""Search query builder and executor for the knowledge corpus.

Constructs SQLAlchemy queries from search parameters with support
for filtering, pagination, and sorting.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import asc, desc
from sqlalchemy.orm import Query

from app.models import File


@dataclass
class SearchParams:
    """Container for search filter parameters."""

    filename: str = ""
    extensions: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    path_contains: str = ""
    min_size: int | None = None
    max_size: int | None = None
    sort_by: str = "file_name"
    sort_dir: str = "asc"
    page: int = 1
    per_page: int = 25


VALID_SORT_COLUMNS = {
    "file_name": File.file_name,
    "modified_at": File.modified_at,
    "file_size_bytes": File.file_size_bytes,
    "file_path": File.file_path,
    "file_extension": File.file_extension,
    "corpus_section": File.corpus_section,
}


def build_query(params: SearchParams) -> Query:
    """Build a SQLAlchemy query from search parameters.

    Args:
        params: SearchParams instance with filter criteria.

    Returns:
        SQLAlchemy Query object (not yet executed).
    """
    query = File.query

    if params.filename:
        query = query.filter(File.file_name.ilike(f"%{params.filename}%"))

    if params.extensions:
        query = query.filter(File.file_extension.in_(params.extensions))

    if params.sections:
        query = query.filter(File.corpus_section.in_(params.sections))

    if params.date_from:
        query = query.filter(File.modified_at >= params.date_from)

    if params.date_to:
        query = query.filter(File.modified_at <= params.date_to)

    if params.path_contains:
        query = query.filter(File.file_path.ilike(f"%{params.path_contains}%"))

    if params.min_size is not None:
        query = query.filter(File.file_size_bytes >= params.min_size)

    if params.max_size is not None:
        query = query.filter(File.file_size_bytes <= params.max_size)

    # Apply sorting
    sort_column = VALID_SORT_COLUMNS.get(params.sort_by, File.file_name)
    if params.sort_dir == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    return query


def execute_search(params: SearchParams) -> dict:
    """Execute a search and return paginated results.

    Args:
        params: SearchParams instance with filter criteria.

    Returns:
        Dictionary with keys: items (list of File), total, page, per_page,
        pages (total number of pages).
    """
    query = build_query(params)
    total = query.count()
    pages = max(1, (total + params.per_page - 1) // params.per_page)
    page = min(params.page, pages)

    files = query.offset((page - 1) * params.per_page).limit(params.per_page).all()

    return {
        "files": files,
        "total": total,
        "page": page,
        "per_page": params.per_page,
        "pages": pages,
    }


def parse_search_params(args: dict) -> SearchParams:
    """Parse search parameters from a request args dict.

    Args:
        args: Dictionary of query string parameters (e.g. from request.args).

    Returns:
        Populated SearchParams instance.
    """
    params = SearchParams()

    params.filename = args.get("filename", "").strip()
    params.path_contains = args.get("path_contains", "").strip()

    extensions = args.getlist("extension") if hasattr(args, "getlist") else args.get("extension", [])
    if isinstance(extensions, str):
        extensions = [extensions] if extensions else []
    params.extensions = [e for e in extensions if e]

    sections = args.getlist("section") if hasattr(args, "getlist") else args.get("section", [])
    if isinstance(sections, str):
        sections = [sections] if sections else []
    params.sections = [s for s in sections if s]

    date_from = args.get("date_from", "").strip()
    if date_from:
        try:
            params.date_from = datetime.fromisoformat(date_from)
        except ValueError:
            pass

    date_to = args.get("date_to", "").strip()
    if date_to:
        try:
            params.date_to = datetime.fromisoformat(date_to)
        except ValueError:
            pass

    min_size = args.get("min_size", "").strip()
    if min_size:
        try:
            params.min_size = int(min_size)
        except ValueError:
            pass

    max_size = args.get("max_size", "").strip()
    if max_size:
        try:
            params.max_size = int(max_size)
        except ValueError:
            pass

    params.sort_by = args.get("sort_by", "file_name")
    if params.sort_by not in VALID_SORT_COLUMNS:
        params.sort_by = "file_name"

    params.sort_dir = args.get("sort_dir", "asc")
    if params.sort_dir not in ("asc", "desc"):
        params.sort_dir = "asc"

    try:
        params.page = max(1, int(args.get("page", 1)))
    except (ValueError, TypeError):
        params.page = 1

    try:
        params.per_page = min(100, max(1, int(args.get("per_page", 25))))
    except (ValueError, TypeError):
        params.per_page = 25

    return params
