from __future__ import annotations

from pydantic import BaseModel, Field

from wealthpath.models.household import HouseholdProfile


class EvaluationRequest(BaseModel):
    household: HouseholdProfile
    planned_retirement_age: int = Field(..., ge=45, le=80)
    life_expectancy: int = Field(85, ge=70, le=100)
    annual_spending_retirement: float = Field(..., gt=0, description="Expected annual spending in retirement (USD)")
    social_security_annual: float = Field(0.0, ge=0, description="Expected annual Social Security income (USD)")
    equity_fraction: float = Field(0.70, ge=0.0, le=1.0, description="Stock allocation (0=all bonds, 1=all stocks)")
    savings_rate: float = Field(0.10, ge=0.0, le=0.80, description="Fraction of income saved annually")


class FeatureDriver(BaseModel):
    feature: str
    display_name: str
    shap_value: float = Field(description="Positive = raises success probability; negative = lowers it")
    direction: str = Field(description="'positive' or 'negative'")


class EvaluationResponse(BaseModel):
    success_probability: float = Field(description="Probability of not running out of money (0–1)")
    success_label: str = Field(description="'on track', 'at risk', or 'critical'")
    top_drivers: list[FeatureDriver] = Field(description="Top factors driving this result (from SHAP)")
    data_source: str = Field(description="'surrogate_model' or 'monte_carlo_fallback'")
    model_metrics: dict | None = Field(None, description="Training metrics — R², MAE — for transparency")
