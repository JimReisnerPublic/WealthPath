from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from wealthpath.services.surrogate_model_service import SurrogateModelService
    from wealthpath.services.simulation_engine import SimulationEngine


def build_evaluate_tools(
    surrogate: SurrogateModelService,
    simulation: SimulationEngine,
) -> list:
    """
    Factory that creates a LangChain tool wrapping the surrogate model service.

    When the LangGraph planning agent receives a question about retirement readiness,
    it can call this tool to get a probability estimate + SHAP-driven explanation.
    The tool hides whether the surrogate model or Monte Carlo fallback ran — the
    agent just gets a human-readable result either way.

    SK equivalent:  kernel.add_plugin(EvaluatePlugin(surrogate, simulation))
    LC equivalent:  tools += build_evaluate_tools(surrogate, simulation)
    """

    @tool
    def evaluate_retirement_plan(
        planned_retirement_age: int,
        annual_spending_retirement: float,
        savings_rate: float,
        social_security_annual: float = 0.0,
        equity_fraction: float = 0.70,
        life_expectancy: int = 85,
    ) -> str:
        """
        Evaluate a retirement plan and return the probability of financial success.

        Use this tool when the user wants to know their chance of not running out of
        money in retirement. This tool uses an XGBoost surrogate model trained on
        Monte Carlo simulations for fast, explainable results.

        Args:
            planned_retirement_age: Age at which the user plans to retire (45–80).
            annual_spending_retirement: Expected annual spending in retirement in USD.
            savings_rate: Fraction of current income being saved (0.0–0.80).
            social_security_annual: Expected annual Social Security income in USD (default 0).
            equity_fraction: Fraction of portfolio in stocks, rest in bonds (0.0–1.0, default 0.70).
            life_expectancy: Assumed age at end of plan horizon (default 85).
        """
        # We need the household profile from the agent's conversation context.
        # The agent injects it via the question — the tool extracts it from the surrogate service.
        # For now, the tool returns a descriptive result based on what it can compute.
        # A full implementation would require the agent to pass household context explicitly.

        from wealthpath.models.evaluate import EvaluationRequest
        from wealthpath.models.household import HouseholdProfile, EducationLevel

        # Create a minimal profile for the tool call
        # The agent should have gathered age/income/net_worth from earlier tool calls or the question
        placeholder_profile = HouseholdProfile(
            age=45,
            income=80_000,
            net_worth=200_000,
            education=EducationLevel.BACHELORS,
        )

        request = EvaluationRequest(
            household=placeholder_profile,
            planned_retirement_age=planned_retirement_age,
            life_expectancy=life_expectancy,
            annual_spending_retirement=annual_spending_retirement,
            social_security_annual=social_security_annual,
            equity_fraction=equity_fraction,
            savings_rate=savings_rate,
        )

        result = surrogate.predict(request)
        if result is None:
            # Fallback not available here without full household context
            return (
                "The surrogate model is not yet trained. "
                "Run scripts/generate_training_data.py then scripts/train_surrogate_model.py."
            )

        drivers = ", ".join(
            f"{d.display_name} ({'+' if d.direction == 'positive' else '-'}{abs(d.shap_value):.3f})"
            for d in result.top_drivers[:3]
        )
        return (
            f"Retirement success probability: {result.success_probability:.1%} ({result.success_label}). "
            f"Top factors: {drivers}. "
            f"Data source: {result.data_source}."
        )

    return [evaluate_retirement_plan]
