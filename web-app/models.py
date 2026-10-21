from datetime import date

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class Note(db.Model):
    """One Markdown note from the knowledge base, identified by its source path."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # The note's single `# heading`, or its file name when it has none.
    title: Mapped[str] = mapped_column(String(255))

    # Directory of the note relative to the knowledge base root, e.g. "tools/git".
    # The path is the classification: moving a file reclassifies it.
    category: Mapped[str] = mapped_column(String(1024))

    # Source path relative to the knowledge base root, e.g. "tools/git/commands.md".
    file_path: Mapped[str] = mapped_column(String(1024), unique=True)

    # `RolloutDate` from front matter: when the owner says the note was written.
    rollout_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Date of the last commit that touched the file, when git history is available.
    updated_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Hash of the renderer version and source, used to skip unchanged notes.
    content_hash: Mapped[str] = mapped_column(String(64))

    def __repr__(self):
        return f"<Note {self.file_path}>"
