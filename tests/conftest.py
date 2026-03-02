from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wealthpath.config import Settings
from wealthpath.dependencies import get_scf_service, get_settings
from wealthpath.main import app
from wealthpath.services.scf_data_service import SCFDataService

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "src" / "wealthpath" / "data" / "scf_sample.csv"


@pytest.fixture()
def settings() -> Settings:
    return Settings(scf_data_path=SAMPLE_CSV)


@pytest.fixture()
def scf_service(settings: Settings) -> SCFDataService:
    svc = SCFDataService(settings.scf_data_path)
    svc.load()
    return svc


@pytest.fixture()
def client(settings: Settings, scf_service: SCFDataService) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_scf_service] = lambda: scf_service
    yield TestClient(app)
    app.dependency_overrides.clear()
