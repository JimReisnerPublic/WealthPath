from __future__ import annotations

from pydantic import BaseModel, Field

from wealthpath.models.household import FinancialGoal, HouseholdProfile


class Scenario(BaseModel):
    label: str = Field("baseline", description="Scenario name")
    annual_savings_rate: float = Field(0.10, ge=0, le=1)
    real_return_mean: float = Field(0.05, description="Expected real return")
    real_return_std: float = Field(0.12, description="Return volatility")
    income_growth_rate: float = Field(0.02)
    inflation_rate: float = Field(0.03)


class ProjectionRequest(BaseModel):
    household: HouseholdProfile
    goals: list[FinancialGoal] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=lambda: [Scenario()])
    num_simulations: int = Field(1_000, ge=100, le=100_000)
    projection_years: int = Field(30, ge=1, le=60)


class PercentileTrajectory(BaseModel):
    percentile: int
    values: list[float]


class ScenarioResult(BaseModel):
    scenario_label: str
    trajectories: list[PercentileTrajectory]
    median_final_wealth: float
    goal_probabilities: dict[str, float] = Field(default_factory=dict)


class ProjectionResponse(BaseModel):
    years: list[int]
    results: list[ScenarioResult]
