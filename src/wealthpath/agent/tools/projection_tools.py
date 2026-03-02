from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from wealthpath.services.simulation_engine import SimulationEngine


def build_projection_tools(simulation_engine: SimulationEngine) -> list:
    """
    Factory that creates LangChain tools wrapping the Monte Carlo simulation engine.

    Replaces Semantic Kernel's ProjectionPlugin / @kernel_function.
    """

    @tool
    def get_median_projection(
        initial_wealth: float,
        annual_income: float,
        savings_rate: float,
        years: int,
    ) -> str:
        """
        Run a Monte Carlo wealth projection and return the median outcome.

        Args:
            initial_wealth: Current net worth in USD.
            annual_income: Annual income in USD.
            savings_rate: Fraction of income saved annually (0.0 to 1.0).
            years: Projection horizon in years.
        """
        from wealthpath.models.household import HouseholdProfile
        from wealthpath.models.projection import ProjectionRequest, Scenario

        profile = HouseholdProfile(age=30, income=annual_income, net_worth=initial_wealth)
        request = ProjectionRequest(
            household=profile,
            scenarios=[Scenario(annual_savings_rate=savings_rate)],
            num_simulations=500,
            projection_years=years,
        )
        response = simulation_engine.run(request)
        median = response.results[0].median_final_wealth
        return f"Median projected wealth after {years} years: ${median:,.0f}"

    return [get_median_projection]
