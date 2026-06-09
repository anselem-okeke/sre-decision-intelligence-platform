from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.collectors.frontend_availability import collect_frontend_availability_live_signals
from app.engine.decision_engine import RuleEngine
from app.engine.sample_signals import get_frontend_availability_sample_signals
from app.schemas.decision import DecisionResponse

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])

RULE_PATH = Path("app/rules/frontend_availability_breach.yaml")


@router.get("/frontend-availability", response_model=DecisionResponse)
def get_frontend_availability_incident() -> DecisionResponse:
    """
    Stable sample-based endpoint.

    Uses validated Phase 10/11 signals.
    This endpoint is safe for demos and tests because it does not depend on live systems.
    """
    signals = get_frontend_availability_sample_signals()
    engine = RuleEngine(RULE_PATH)

    return engine.evaluate(signals)


@router.get("/frontend-availability/live", response_model=DecisionResponse)
def get_frontend_availability_live_incident() -> DecisionResponse:
    """
    Live collector-based endpoint.

    Collects signals from Prometheus, Kubernetes, and OpenSearch.
    Then evaluates the same rule engine used by the stable endpoint.
    """
    try:
        signals = collect_frontend_availability_live_signals()
        engine = RuleEngine(RULE_PATH)

        return engine.evaluate(signals)

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "No matching incident rule found for current live signals.",
                "reason": str(error),
            },
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to collect live frontend availability signals.",
                "reason": str(error),
            },
        ) from error

@router.get("/frontend-availability/live/signals")
def get_frontend_availability_live_signals() -> dict[str, Any]:
    """
    Debug endpoint.

    Returns raw normalized live signals before rule evaluation.
    Useful for validating collector output.
    """
    try:
        return collect_frontend_availability_live_signals()

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to collect live frontend availability signals.",
                "reason": str(error),
            },
        ) from error
