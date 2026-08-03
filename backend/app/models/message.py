from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    __tablename__ = "messages"

    id: orm.Mapped[int] = orm.mapped_column(
        primary_key=True,
        index=True,
    )

    conversation_id: orm.Mapped[int] = orm.mapped_column(
        sa.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: orm.Mapped[MessageRole] = orm.mapped_column(
        sa.Enum(MessageRole),
        nullable=False,
    )

    content: orm.Mapped[str] = orm.mapped_column(
        sa.Text,
        nullable=False,
    )

    created_at: orm.Mapped[datetime] = orm.mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )

    conversation: orm.Mapped["Conversation"] = orm.relationship(
        back_populates="messages",
    )