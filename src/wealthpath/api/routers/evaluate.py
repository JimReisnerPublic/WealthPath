from __future__ import annotations

from fastapi import APIRouter, Depends

from wealthpath.dependencies import get_simulation_engine, get_surrogate_model_service
from wealthpath.models.evaluate import EvaluationRequest, EvaluationResponse, FeatureDriver
from wealthpath.services.surrogate_model_service import SurrogateModelService
from wealthpath.services.simulation_engine import SimulationEngine

router = APIRouter(prefix="/api/v1/plan", tags=["evaluate"])


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_plan(
    request: EvaluationRequest,
    surrogate: SurrogateModelService = Depends(get_surrogate_model_service),
    simulation: SimulationEngine = Depends(get_simulation_engine),
) -> EvaluationResponse:
    """
    Evaluate a retirement plan and return a success probability with SHAP-driven explanations.

    Primary path:  XGBoost surrogate model (~1ms, with SHAP feature attribution)
    Fallback path: Monte Carlo simulation (~200ms, used when model is not yet trained)

    This endpoint is what makes WealthPath fast enough for real-time what-if scenarios —
    sliders in the UI call this endpoint on every change without perceptible delay.
    """
    # Try the fast surrogate model first
    result = surrogate.predict(request)
    if result is not None:
        return result

    # Fallback: run Monte Carlo directly (same engine used to generate training data)
    return _monte_carlo_fallback(request, simulation)


def _monte_carlo_fallback(
    request: EvaluationRequest,
    simulation: SimulationEngine,
) -> EvaluationResponse:
    """
    Fall back to the Monte Carlo SimulationEngine when the surrogate model isn't trained yet.
    Returns the same EvaluationResponse shape so the frontend doesn't need to know which path ran.
    """
    from wealthpath.models.projection import ProjectionRequest, Scenario
    from wealthpath.models.household import FinancialGoal
    import datetime

    target_year = datetime.date.today().year + max(
        request.life_expectancy - request.household.age, 1
    )
    goal = FinancialGoal(
        name="retirement_success",
        target_amount=1.0,   # any positive amount — we measure "not zero" as success
        target_year=min(target_year, 2100),
    )

    proj_request = ProjectionRequest(
        household=request.household,
        goals=[goal],
        scenarios=[
            Scenario(
                annual_savings_rate=request.savings_rate,
                real_return_mean=(
                    request.equity_fraction * 0.07 + (1 - request.equity_fraction) * 0.02
                ),
                real_return_std=(
                    request.equity_fraction * 0.16 + (1 - request.equity_fraction) * 0.05
                ),
            )
        ],
        num_simulations=1_000,
        projection_years=max(request.life_expectancy - request.household.age, 1),
    )

    response = simulation.run(proj_request)
    prob = response.results[0].goal_probabilities.get("retirement_success", 0.5)

    return EvaluationResponse(
        success_probability=round(prob, 4),
        success_label=_label(prob),
        top_drivers=[
            FeatureDriver(
                feature="model_not_trained",
                display_name="Surrogate model not yet trained",
                shap_value=0.0,
                direction="positive",
            )
        ],
        data_source="monte_carlo_fallback",
        model_metrics=None,
    )


def _label(prob: float) -> str:
    if prob >= 0.80:
        return "on track"
    if prob >= 0.60:
        return "at risk"
    return "critical"
