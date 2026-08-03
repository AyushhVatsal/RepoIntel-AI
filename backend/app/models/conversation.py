from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.repository import Repository
    from app.models.user import User


class Conversation(Base):
    __tablename__ = "conversations"

    id: orm.Mapped[int] = orm.mapped_column(
        primary_key=True,
        index=True,
    )

    title: orm.Mapped[str] = orm.mapped_column(
        sa.String(255),
        nullable=False,
    )

    user_id: orm.Mapped[int] = orm.mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    repository_id: orm.Mapped[int] = orm.mapped_column(
        sa.ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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

    user: orm.Mapped["User"] = orm.relationship(
        back_populates="conversations",
    )

    repository: orm.Mapped["Repository"] = orm.relationship(
        back_populates="conversations",
    )

    messages: orm.Mapped[list["Message"]] = orm.relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )