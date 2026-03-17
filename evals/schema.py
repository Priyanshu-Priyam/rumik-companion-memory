from __future__ import annotations
from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    id: str
    category: str
    tags: list[str] = Field(default_factory=list)
    severity: str
    user_profile: str
    memory_state: list[dict] = Field(default_factory=list)
    history: list[dict] = Field(default_factory=list)
    user_message: str
    expected_checks: list[str] = Field(default_factory=list)
    disallowed_behaviors: list[str] = Field(default_factory=list)
    scoring: str


class EvalResult(BaseModel):
    case_id: str
    category: str
    severity: str
    passed: bool
    score: float = 0.0
    response: str = ""
    rule_checks: dict | None = None
    judge_assessment: dict | None = None
    debug: dict | None = None
    error: str | None = None
