from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class EducationLevel(str, Enum):
    NO_HIGH_SCHOOL = "no_high_school"
    HIGH_SCHOOL = "high_school"
    SOME_COLLEGE = "some_college"
    BACHELORS = "bachelors"
    GRADUATE = "graduate"


class HouseholdProfile(BaseModel):
    age: int = Field(..., ge=18, le=100, description="Age of household head")
    income: float = Field(..., ge=0, description="Annual household income in USD")
    net_worth: float = Field(..., description="Current net worth in USD (total assets minus liabilities)")
    investable_savings: float = Field(0, ge=0, description="Liquid/investable assets excluding home equity (USD)")
    education: EducationLevel = EducationLevel.BACHELORS
    household_size: int = Field(1, ge=1, le=20)
    home_equity: float = Field(0, ge=0)
    debt: float = Field(0, ge=0)


class FinancialGoal(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    target_amount: float = Field(..., gt=0)
    target_year: int = Field(..., ge=2025, le=2100)
    priority: int = Field(1, ge=1, le=5, description="1 = highest priority")
