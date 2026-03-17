from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class FactSource(str, Enum):
    USER_STATED = "user_stated"
    INFERRED = "inferred"
    GUESSED = "guessed"


class FactStatus(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    CORRECTED = "corrected"
    RETRACTED = "retracted"


class Sensitivity(str, Enum):
    NONE = "none"
    MODERATE = "moderate"
    HIGH = "high"
    INTIMATE = "intimate"


class MemoryForm(str, Enum):
    ATOMIC = "atomic"
    SUMMARY = "summary"


class Fact(BaseModel):
    fact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    entity_id: str | None = None
    predicate: str
    value: str
    source: FactSource = FactSource.USER_STATED
    status: FactStatus = FactStatus.CURRENT
    confidence: float = 1.0
    sensitivity: Sensitivity = Sensitivity.NONE
    memory_form: MemoryForm = MemoryForm.ATOMIC
    supersedes: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    context_summary: str | None = None
    conversation_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationTurn(BaseModel):
    role: str
    content: str


class MemoryStateItem(BaseModel):
    key: str
    value: str
    confidence: str = "high"
    source: str = "user_stated"
    sensitive: bool = False
