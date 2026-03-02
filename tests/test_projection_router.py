from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_projection(client: TestClient) -> None:
    payload = {
        "household": {
            "age": 35,
            "income": 75000,
            "net_worth": 120000,
            "education": "bachelors",
        },
        "num_simulations": 200,
        "projection_years": 10,
    }
    resp = client.post("/api/v1/projections/", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "years" in data
    assert len(data["years"]) == 11  # 0..10
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["scenario_label"] == "baseline"
    assert result["median_final_wealth"] > 0
    assert len(result["trajectories"]) == 5  # 10, 25, 50, 75, 90


def test_projection_with_goals(client: TestClient) -> None:
    payload = {
        "household": {
            "age": 30,
            "income": 60000,
            "net_worth": 50000,
        },
        "goals": [
            {
                "name": "Retirement",
                "target_amount": 1000000,
                "target_year": 2060,
            }
        ],
        "num_simulations": 200,
        "projection_years": 30,
    }
    resp = client.post("/api/v1/projections/", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    probs = data["results"][0]["goal_probabilities"]
    assert "Retirement" in probs
    assert 0 <= probs["Retirement"] <= 1
