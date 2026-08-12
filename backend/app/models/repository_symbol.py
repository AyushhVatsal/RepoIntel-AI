from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RepositorySymbol(Base):
    """Parsed symbols from repository files."""

    __tablename__ = "repository_symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Symbol identity
    symbol_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualified_name: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Location in source code
    location: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Language-specific metadata (stored as symbol_metadata to avoid SQLAlchemy conflict)
    symbol_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "file_id",
            "symbol_type",
            "qualified_name",
            name="uq_file_symbol",
        ),
        Index("idx_symbols_repo_type", "repository_id", "symbol_type"),
        Index("idx_symbols_file", "file_id"),
    )
