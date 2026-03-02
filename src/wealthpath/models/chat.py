from __future__ import annotations

from pydantic import BaseModel, Field

from wealthpath.models.household import HouseholdProfile


class ChatRequest(BaseModel):
    household: HouseholdProfile
    question: str = Field(..., min_length=1, max_length=2000)
    context: dict | None = Field(
        None, description="Optional prior projection/cohort results for grounding"
    )


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(
        default_factory=list,
        description="Data sources referenced in the answer",
    )
