from __future__ import annotations

from fastapi import APIRouter, Depends

from wealthpath.dependencies import get_simulation_engine
from wealthpath.models.projection import ProjectionRequest, ProjectionResponse
from wealthpath.services.simulation_engine import SimulationEngine

router = APIRouter(prefix="/api/v1/projections", tags=["projections"])


@router.post("/", response_model=ProjectionResponse)
async def create_projection(
    request: ProjectionRequest,
    engine: SimulationEngine = Depends(get_simulation_engine),
) -> ProjectionResponse:
    return engine.run(request)
