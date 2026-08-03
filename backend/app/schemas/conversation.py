from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )


class ConversationUpdate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )


class ConversationResponse(BaseModel):
    id: int
    title: str
    repository_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }