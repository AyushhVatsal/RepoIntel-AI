from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.repository import Repository

class FileCategory(str, Enum):
    SOURCE = "source"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    BINARY = "binary"
    IGNORED = "ignored"


class LanguageSupportTier(str, Enum):
    TIER_1 = "tier_1"
    TIER_0 = "tier_0"
    NONE = "none"


class RepositoryFile(Base):
    __tablename__ = "repository_files"

    id: Mapped[int] = mapped_column(primary_key=True)

    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    relative_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    extension: Mapped[str | None] = mapped_column(
        String(20),
    )

    language: Mapped[str | None] = mapped_column(
        String(50),
    )

    category: Mapped[FileCategory] = mapped_column(
        SqlEnum(FileCategory),
        nullable=False,
    )

    support_tier: Mapped[LanguageSupportTier] = mapped_column(
        SqlEnum(LanguageSupportTier),
        nullable=False,
        default=LanguageSupportTier.NONE,
    )

    size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    sha256_hash: Mapped[str | None] = mapped_column(
        String(64),
    )

    is_binary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    last_modified: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="files",
    )

    __table_args__ = (
        Index(
            "ix_repository_files_repository_relative_path",
            "repository_id",
            "relative_path",
            unique=True,
        ),
        Index(
            "ix_repository_files_language",
            "language",
        ),
        Index(
            "ix_repository_files_category",
            "category",
        ),
    )