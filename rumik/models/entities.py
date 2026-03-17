from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class Entity(BaseModel):
    entity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    canonical_name: str
    entity_type: str = "unknown"
    aliases: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
