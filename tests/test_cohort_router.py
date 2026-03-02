from __future__ import annotations

from fastapi.testclient import TestClient


def test_compare_cohort(client: TestClient) -> None:
    payload = {
        "household": {
            "age": 40,
            "income": 70000,
            "net_worth": 150000,
            "education": "bachelors",
        },
        "compare_fields": ["income", "net_worth"],
    }
    resp = client.post("/api/v1/cohort/compare", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["cohort_size"] > 0
    assert len(data["stats"]) == 2
    for stat in data["stats"]:
        assert stat["cohort_median"] > 0
        assert 0 <= stat["percentile_rank"] <= 100
