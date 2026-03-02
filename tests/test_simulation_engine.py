from __future__ import annotations

from wealthpath.models.household import HouseholdProfile
from wealthpath.models.projection import ProjectionRequest, Scenario
from wealthpath.services.simulation_engine import SimulationEngine


def test_simulation_returns_correct_shape() -> None:
    engine = SimulationEngine()
    profile = HouseholdProfile(age=35, income=75000, net_worth=100000)
    request = ProjectionRequest(
        household=profile,
        num_simulations=100,
        projection_years=10,
    )
    response = engine.run(request)
    assert len(response.years) == 11
    assert response.years[0] == 0
    assert response.years[-1] == 10
    assert len(response.results) == 1
    for traj in response.results[0].trajectories:
        assert len(traj.values) == 11


def test_simulation_wealth_grows_on_average() -> None:
    engine = SimulationEngine()
    profile = HouseholdProfile(age=30, income=60000, net_worth=50000)
    request = ProjectionRequest(
        household=profile,
        scenarios=[Scenario(annual_savings_rate=0.15, real_return_mean=0.06)],
        num_simulations=500,
        projection_years=20,
    )
    response = engine.run(request)
    median = response.results[0].median_final_wealth
    assert median > profile.net_worth


def test_multiple_scenarios() -> None:
    engine = SimulationEngine()
    profile = HouseholdProfile(age=40, income=80000, net_worth=200000)
    request = ProjectionRequest(
        household=profile,
        scenarios=[
            Scenario(label="conservative", real_return_mean=0.03, real_return_std=0.08),
            Scenario(label="aggressive", real_return_mean=0.08, real_return_std=0.18),
        ],
        num_simulations=200,
        projection_years=15,
    )
    response = engine.run(request)
    assert len(response.results) == 2
    assert response.results[0].scenario_label == "conservative"
    assert response.results[1].scenario_label == "aggressive"
