from __future__ import annotations

from pydantic import BaseModel, Field

from wealthpath.models.household import HouseholdProfile


class CohortRequest(BaseModel):
    household: HouseholdProfile
    compare_fields: list[str] = Field(
        default_factory=lambda: ["income", "net_worth"],
        description="Fields to include in comparison",
    )


class CohortStats(BaseModel):
    field: str
    user_value: float
    cohort_median: float
    cohort_p25: float
    cohort_p75: float
    percentile_rank: float = Field(
        ..., ge=0, le=100, description="User's percentile within the cohort"
    )


class CohortResponse(BaseModel):
    cohort_size: int
    cohort_description: str
    stats: list[CohortStats]
