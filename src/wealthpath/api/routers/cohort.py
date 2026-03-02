from __future__ import annotations

from fastapi import APIRouter, Depends

from wealthpath.dependencies import get_scf_service
from wealthpath.models.cohort import CohortRequest, CohortResponse
from wealthpath.services.scf_data_service import SCFDataService

router = APIRouter(prefix="/api/v1/cohort", tags=["cohort"])


@router.post("/compare", response_model=CohortResponse)
async def compare_cohort(
    request: CohortRequest,
    scf: SCFDataService = Depends(get_scf_service),
) -> CohortResponse:
    return scf.compare(request)
