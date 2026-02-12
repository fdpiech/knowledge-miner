"""SQLAlchemy models for Knowledge Corpus Manager."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# Association table for many-to-many file<->tag relationship
file_tags = Table(
    "file_tags",
    db.Model.metadata,
    Column("file_id", Integer, ForeignKey("files.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class File(db.Model):  # type: ignore[name-defined]
    """Represents an indexed file in the knowledge corpus."""

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(Text, nullable=False, unique=True, index=True)
    file_name = Column(Text, nullable=False)
    file_extension = Column(Text, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    parent_dir = Column(Text, nullable=False)
    corpus_section = Column(Text, index=True)
    created_at = Column(DateTime)
    modified_at = Column(DateTime, index=True)
    indexed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    content_text = Column(Text)
    file_hash = Column(Text)

    tags = db.relationship("Tag", secondary=file_tags, back_populates="files")

    def __repr__(self) -> str:
        return f"<File {self.file_path}>"

    def to_dict(self) -> dict:
        """Convert file record to a dictionary."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_extension": self.file_extension,
            "file_size_bytes": self.file_size_bytes,
            "parent_dir": self.parent_dir,
            "corpus_section": self.corpus_section,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "file_hash": self.file_hash,
        }


class Tag(db.Model):  # type: ignore[name-defined]
    """A tag for categorizing files."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False, unique=True)

    files = db.relationship("File", secondary=file_tags, back_populates="tags")

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"


class ConsolidationJob(db.Model):  # type: ignore[name-defined]
    """Tracks consolidation/export jobs."""

    __tablename__ = "consolidation_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    query_params = Column(Text, nullable=False)
    output_path = Column(Text)
    output_format = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    file_count = Column(Integer)

    def __repr__(self) -> str:
        return f"<ConsolidationJob {self.name}>"
