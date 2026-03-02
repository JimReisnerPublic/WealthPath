from __future__ import annotations

from fastapi import APIRouter, Depends

from wealthpath.dependencies import get_scf_service
from wealthpath.services.scf_data_service import SCFDataService

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(
    scf: SCFDataService = Depends(get_scf_service),
) -> dict[str, str]:
    if scf.df.empty:
        return {"status": "degraded", "reason": "SCF data not loaded"}
    return {"status": "ok"}
