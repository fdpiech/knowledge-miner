"""Database initialization script for Knowledge Corpus Manager.

Creates the SQLite database and all required tables.
"""

from pathlib import Path

from app import create_app
from app.models import db


def setup_database() -> None:
    """Create the database file and all tables."""
    app = create_app()

    with app.app_context():
        # Ensure the database directory exists
        db_path = Path(app.config["KCM"]["database"]["path"])
        db_path.parent.mkdir(parents=True, exist_ok=True)

        db.create_all()
        print(f"Database created at: {db_path}")
        print("All tables initialized successfully.")


if __name__ == "__main__":
    setup_database()
