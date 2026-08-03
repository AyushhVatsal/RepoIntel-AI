from datetime import datetime

from pydantic import BaseModel, Field

from app.models.message import MessageRole


class MessageCreate(BaseModel):
    content: str = Field(
        min_length=1,
    )


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: MessageRole
    content: str
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }