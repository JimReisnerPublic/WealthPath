from __future__ import annotations

from functools import lru_cache

from fastapi import Request

from wealthpath.config import Settings
from wealthpath.services.ai_engine import AIEngine
from wealthpath.services.scf_data_service import SCFDataService
from wealthpath.services.simulation_engine import SimulationEngine
from wealthpath.services.surrogate_model_service import SurrogateModelService


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_scf_service() -> SCFDataService:
    settings = get_settings()
    svc = SCFDataService(settings.scf_data_path)
    svc.load()
    return svc


@lru_cache
def get_simulation_engine() -> SimulationEngine:
    return SimulationEngine()


@lru_cache
def get_surrogate_model_service() -> SurrogateModelService:
    settings = get_settings()
    svc = SurrogateModelService(settings.surrogate_model_path)
    if settings.azure_storage_connection_string:
        # Production: download model from Azure Blob Storage at startup
        svc.load_from_blob(
            settings.azure_storage_connection_string,
            settings.azure_blob_container,
            settings.azure_blob_model_name,
        )
    else:
        # Local dev: load from local filesystem (no env var needed)
        svc.load()   # logs a warning and returns False if model file not found — no crash
    return svc


def get_ai_engine(request: Request) -> AIEngine:
    """
    Return the AIEngine built at startup (stored in app.state by the lifespan).

    The engine is built once during the lifespan context manager in main.py,
    which allows async initialisation of the FRED MCP server subprocess before
    the first request arrives. FastAPI injects the Request automatically.
    """
    return request.app.state.ai_engine
