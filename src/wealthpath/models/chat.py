from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from wealthpath.models.household import HouseholdProfile


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    household: HouseholdProfile
    # Full conversation history; last entry is the current user question.
    # Replaces the old `question: str` field to enable multi-turn chat.
    # The complete list is sent by the client on every request — server stays stateless.
    # SK equivalent: ChatHistory passed into kernel.invoke(); LC equivalent: list[BaseMessage]
    messages: list[ChatMessage] = Field(..., min_length=1)
    context: dict | None = Field(
        None,
        description="Optional prior evaluation result for grounding (success_probability, top_drivers, etc.)",
    )


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(
        default_factory=list,
        description="Data sources referenced in the answer",
    )
