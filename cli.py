"""CLI commands for Knowledge Corpus Manager.

Provides terminal-based access to indexing, search, and consolidation.
"""

import json
import sys

import click

from app import create_app
from app.models import File, db
from app.indexer import index_corpus, reindex_changed
from app.search import SearchParams, execute_search
from app.consolidator import consolidate_files


@click.group()
def cli():
    """Knowledge Corpus Manager - CLI tools."""
    pass


@cli.command()
@click.option("--incremental", is_flag=True, help="Only process new or changed files.")
def index(incremental: bool):
    """Index the knowledge corpus directory."""
    app = create_app()
    with app.app_context():
        corpus_root = app.config["KCM"]["corpus"]["root_path"]
        if not corpus_root:
            click.echo("Error: Corpus root path is not configured.", err=True)
            click.echo("Set KCM_CORPUS_ROOT environment variable or update config.yaml.", err=True)
            sys.exit(1)

        indexer_config = app.config["KCM"].get("indexer", {})
        skip_patterns = indexer_config.get("skip_patterns")
        supported_extensions = indexer_config.get("supported_extensions")

        if incremental:
            click.echo(f"Running incremental reindex of: {corpus_root}")
            stats = reindex_changed(
                root_path=corpus_root,
                db_session=db.session,
                skip_patterns=skip_patterns,
                supported_extensions=supported_extensions,
            )
        else:
            click.echo(f"Running full index of: {corpus_root}")
            stats = index_corpus(
                root_path=corpus_root,
                db_session=db.session,
                skip_patterns=skip_patterns,
                supported_extensions=supported_extensions,
            )

        click.echo(f"\nIndex complete:")
        for key, value in stats.items():
            click.echo(f"  {key}: {value}")


@cli.command()
def stats():
    """Show index statistics."""
    app = create_app()
    with app.app_context():
        from sqlalchemy import func

        total = db.session.query(func.count(File.id)).scalar() or 0
        total_size = db.session.query(func.sum(File.file_size_bytes)).scalar() or 0
        last_indexed = db.session.query(func.max(File.indexed_at)).scalar()

        click.echo(f"Total indexed files: {total}")
        click.echo(f"Total size: {total_size:,} bytes")
        click.echo(f"Last indexed: {last_indexed or 'never'}")

        # Extension breakdown
        ext_counts = (
            db.session.query(File.file_extension, func.count(File.id))
            .group_by(File.file_extension)
            .order_by(func.count(File.id).desc())
            .all()
        )
        if ext_counts:
            click.echo("\nFiles by extension:")
            for ext, count in ext_counts:
                click.echo(f"  {ext}: {count}")

        # Section breakdown
        section_counts = (
            db.session.query(File.corpus_section, func.count(File.id))
            .group_by(File.corpus_section)
            .order_by(func.count(File.id).desc())
            .all()
        )
        if section_counts:
            click.echo("\nFiles by section:")
            for section, count in section_counts:
                click.echo(f"  {section or '(root)'}: {count}")


@cli.command()
@click.option("--name", default="", help="Filter by filename substring.")
@click.option("--ext", default="", help="Filter by file extension (e.g. .xlsx).")
@click.option("--section", default="", help="Filter by corpus section.")
@click.option("--after", default="", help="Only files modified after this date (YYYY-MM-DD).")
@click.option("--before", default="", help="Only files modified before this date (YYYY-MM-DD).")
@click.option("--limit", default=25, help="Max results to show.")
def search(name: str, ext: str, section: str, after: str, before: str, limit: int):
    """Search indexed files from the terminal."""
    app = create_app()
    with app.app_context():
        from datetime import datetime

        params = SearchParams(
            filename=name,
            extensions=[ext] if ext else [],
            sections=[section] if section else [],
            per_page=limit,
        )

        if after:
            try:
                params.date_from = datetime.fromisoformat(after)
            except ValueError:
                click.echo(f"Invalid date format for --after: {after}", err=True)
                sys.exit(1)

        if before:
            try:
                params.date_to = datetime.fromisoformat(before)
            except ValueError:
                click.echo(f"Invalid date format for --before: {before}", err=True)
                sys.exit(1)

        results = execute_search(params)

        if not results["files"]:
            click.echo("No matching files found.")
            return

        click.echo(f"Found {results['total']} files (showing {len(results['items'])}):\n")
        for f in results["files"]:
            modified = f.modified_at.strftime("%Y-%m-%d") if f.modified_at else "unknown"
            click.echo(f"  [{f.file_extension}] {f.file_path}  ({modified})")


@cli.command()
@click.option("--name", required=True, help="Label for the consolidation.")
@click.option("--section", default="", help="Filter files by corpus section.")
@click.option("--ext", default="", help="Filter files by extension.")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json", "text"]))
def consolidate(name: str, section: str, ext: str, output_format: str):
    """Consolidate search results into an export file."""
    app = create_app()
    with app.app_context():
        query = File.query
        if section:
            query = query.filter(File.corpus_section == section)
        if ext:
            query = query.filter(File.file_extension == ext)

        files = query.all()
        if not files:
            click.echo("No matching files found.")
            return

        file_ids = [f.id for f in files]
        output_dir = app.config["KCM"]["consolidation"]["output_dir"]

        query_params = {"section": section, "ext": ext, "source": "cli"}
        job = consolidate_files(
            file_ids=file_ids,
            output_format=output_format,
            name=name,
            db_session=db.session,
            output_dir=output_dir,
            query_params_json=json.dumps(query_params),
        )

        click.echo(f"Consolidation complete:")
        click.echo(f"  Files included: {job.file_count}")
        click.echo(f"  Format: {job.output_format}")
        click.echo(f"  Output: {job.output_path}")


if __name__ == "__main__":
    cli()
