from __future__ import annotations

import numpy as np

from wealthpath.models.projection import (
    PercentileTrajectory,
    ProjectionRequest,
    ProjectionResponse,
    ScenarioResult,
)


class SimulationEngine:
    """Monte Carlo wealth projection engine."""

    PERCENTILES = (10, 25, 50, 75, 90)

    def run(self, request: ProjectionRequest) -> ProjectionResponse:
        years = list(
            range(
                0,
                request.projection_years + 1,
            )
        )
        results: list[ScenarioResult] = []

        for scenario in request.scenarios:
            wealth_matrix = self._simulate(
                initial_wealth=request.household.net_worth,
                annual_income=request.household.income,
                savings_rate=scenario.annual_savings_rate,
                return_mean=scenario.real_return_mean,
                return_std=scenario.real_return_std,
                income_growth=scenario.income_growth_rate,
                n_years=request.projection_years,
                n_sims=request.num_simulations,
            )

            trajectories = [
                PercentileTrajectory(
                    percentile=p,
                    values=np.percentile(wealth_matrix, p, axis=0).tolist(),
                )
                for p in self.PERCENTILES
            ]

            median_final = float(np.median(wealth_matrix[:, -1]))

            goal_probs: dict[str, float] = {}
            for goal in request.goals:
                goal_year_idx = min(
                    goal.target_year - goal.target_year + request.projection_years,
                    request.projection_years,
                )
                goal_year_idx = min(
                    max(goal_year_idx, 0), request.projection_years
                )
                prob = float(
                    np.mean(wealth_matrix[:, goal_year_idx] >= goal.target_amount)
                )
                goal_probs[goal.name] = round(prob, 4)

            results.append(
                ScenarioResult(
                    scenario_label=scenario.label,
                    trajectories=trajectories,
                    median_final_wealth=median_final,
                    goal_probabilities=goal_probs,
                )
            )

        return ProjectionResponse(years=years, results=results)

    @staticmethod
    def _simulate(
        *,
        initial_wealth: float,
        annual_income: float,
        savings_rate: float,
        return_mean: float,
        return_std: float,
        income_growth: float,
        n_years: int,
        n_sims: int,
    ) -> np.ndarray:
        """Return an (n_sims, n_years+1) matrix of wealth trajectories."""
        rng = np.random.default_rng()
        returns = rng.normal(return_mean, return_std, size=(n_sims, n_years))

        wealth = np.zeros((n_sims, n_years + 1))
        wealth[:, 0] = initial_wealth

        income = annual_income
        for t in range(n_years):
            savings = income * savings_rate
            wealth[:, t + 1] = wealth[:, t] * (1 + returns[:, t]) + savings
            income *= 1 + income_growth

        return wealth
