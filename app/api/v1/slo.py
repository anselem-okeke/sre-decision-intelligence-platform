from fastapi import APIRouter, HTTPException

from app.schemas.slo import (
    ErrorBudgetEvaluateRequest,
    ErrorBudgetEvaluateResponse,
    SloResponse,
)
from app.slo.calculator import calculate_error_budget
from app.slo.registry import slo_registry


router = APIRouter(
    prefix="/api/v1/slo",
    tags=["slo"],
)


@router.get("", response_model=list[SloResponse])
def list_slos() -> list[dict]:
    return [
        slo.model_dump(mode="json")
        for slo in slo_registry.list_slos()
    ]


@router.get("/{slo_id}", response_model=SloResponse)
def get_slo(slo_id: str) -> dict:
    slo = slo_registry.get_slo(slo_id)

    if slo is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "SLO not found.",
                "slo_id": slo_id,
            },
        )

    return slo.model_dump(mode="json")


@router.post("/evaluate", response_model=ErrorBudgetEvaluateResponse)
def evaluate_error_budget(
    request: ErrorBudgetEvaluateRequest,
) -> ErrorBudgetEvaluateResponse:
    slo = slo_registry.get_slo(request.slo_id)

    if slo is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "SLO not found.",
                "slo_id": request.slo_id,
            },
        )

    return calculate_error_budget(
        slo=slo,
        current_value=request.current_value,
    )
