from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from app.db.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.repository_file import RepositoryFile
    from app.models.user import User
    from app.models.conversation import Conversation


class RepositoryStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    SCANNING = "scanning"
    PARSING = "parsing"
    INDEXED = "indexed"
    FAILED = "failed"


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    github_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        unique=True,
    )

    clone_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    default_branch: Mapped[str | None] = mapped_column(
        String(100),
    )

    status: Mapped[RepositoryStatus] = mapped_column(
        SqlEnum(RepositoryStatus),
        nullable=False,
        default=RepositoryStatus.PENDING,
    )

    primary_language: Mapped[str | None] = mapped_column(
        String(100),
    )

    primary_framework: Mapped[str | None] = mapped_column(
        String(100),
    )

    total_files: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    supported_files: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    skipped_files: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    repository_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="repositories",
    )

    files: Mapped[list["RepositoryFile"]] = relationship(
        "RepositoryFile",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="repository",
        cascade="all, delete-orphan",
    )   