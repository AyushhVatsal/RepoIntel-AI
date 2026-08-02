from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.repository import Repository


class User(Base):
    __tablename__ = "users"

    id: orm.Mapped[int] = orm.mapped_column(
        primary_key=True,
        index=True,
    )

    username: orm.Mapped[str] = orm.mapped_column(
        sa.String(100),
        nullable=False,
    )

    email: orm.Mapped[str] = orm.mapped_column(
        sa.String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: orm.Mapped[str] = orm.mapped_column(
        sa.String(255),
        nullable=False,
    )

    is_active: orm.Mapped[bool] = orm.mapped_column(
        sa.Boolean,
        default=True,
        nullable=False,
    )

    created_at: orm.Mapped[datetime] = orm.mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )

    updated_at: orm.Mapped[datetime] = orm.mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    repositories: orm.Mapped[list["Repository"]] = orm.relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    conversations: orm.Mapped[list["Conversation"]] = orm.relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )