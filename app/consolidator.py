"""Consolidation engine for packaging search results into exportable files.

Supports markdown, JSON, and plain text output formats.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import ConsolidationJob, File


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def consolidate_markdown(files: list[File], name: str) -> str:
    """Generate a markdown consolidation report.

    Args:
        files: List of File model instances.
        name: Name/label for the consolidation.

    Returns:
        Markdown-formatted string.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# Consolidation: {name}",
        "",
        f"**Generated:** {now}  ",
        f"**File count:** {len(files)}  ",
        "",
        "---",
        "",
    ]

    # Group files by corpus section
    sections: dict[str, list[File]] = {}
    for f in files:
        section = f.corpus_section or "(root)"
        sections.setdefault(section, []).append(f)

    for section_name in sorted(sections.keys()):
        section_files = sections[section_name]
        lines.append(f"## {section_name}")
        lines.append("")
        for f in sorted(section_files, key=lambda x: x.file_path):
            modified = f.modified_at.strftime("%Y-%m-%d") if f.modified_at else "unknown"
            size = _format_size(f.file_size_bytes)
            lines.append(f"- **{f.file_name}**")
            lines.append(f"  - Path: `{f.file_path}`")
            lines.append(f"  - Type: `{f.file_extension}` | Size: {size} | Modified: {modified}")
        lines.append("")

    return "\n".join(lines)


def consolidate_json(files: list[File], name: str) -> str:
    """Generate a JSON consolidation report.

    Args:
        files: List of File model instances.
        name: Name/label for the consolidation.

    Returns:
        JSON-formatted string.
    """
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "consolidation": {
            "name": name,
            "generated_at": now,
            "file_count": len(files),
        },
        "files": [f.to_dict() for f in files],
    }
    return json.dumps(data, indent=2, default=str)


def consolidate_text(files: list[File], name: str) -> str:
    """Generate a plain text file manifest.

    Args:
        files: List of File model instances.
        name: Name/label for the consolidation.

    Returns:
        Plain text string with file paths and dates.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"Consolidation: {name}",
        f"Generated: {now}",
        f"File count: {len(files)}",
        "=" * 60,
        "",
    ]

    for f in sorted(files, key=lambda x: x.file_path):
        modified = f.modified_at.strftime("%Y-%m-%d %H:%M") if f.modified_at else "unknown"
        lines.append(f"{f.file_path}  [{modified}]  ({_format_size(f.file_size_bytes)})")

    return "\n".join(lines)


FORMAT_HANDLERS = {
    "markdown": (consolidate_markdown, ".md"),
    "json": (consolidate_json, ".json"),
    "text": (consolidate_text, ".txt"),
}


def consolidate_files(
    file_ids: list[int],
    output_format: str,
    name: str,
    db_session: Session,
    output_dir: str,
    query_params_json: str = "{}",
) -> ConsolidationJob:
    """Run a consolidation job: query files, generate output, save to disk.

    Args:
        file_ids: List of File record IDs to include.
        output_format: One of "markdown", "json", "text".
        name: User-provided label for this job.
        db_session: SQLAlchemy database session.
        output_dir: Directory where output files are written.
        query_params_json: JSON string of the search criteria used.

    Returns:
        The created ConsolidationJob instance.

    Raises:
        ValueError: If output_format is not supported.
    """
    if output_format not in FORMAT_HANDLERS:
        raise ValueError(f"Unsupported format: {output_format}. Choose from: {list(FORMAT_HANDLERS.keys())}")

    files = db_session.query(File).filter(File.id.in_(file_ids)).all()

    handler, extension = FORMAT_HANDLERS[output_format]
    content = handler(files, name)

    # Ensure output directory exists
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()
    safe_name = safe_name.replace(" ", "_")
    filename = f"{timestamp}_{safe_name}{extension}"
    output_path = out_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Record the job
    job = ConsolidationJob(
        name=name,
        query_params=query_params_json,
        output_path=str(output_path),
        output_format=output_format,
        created_at=datetime.now(timezone.utc),
        file_count=len(files),
    )
    db_session.add(job)
    db_session.commit()

    return job
