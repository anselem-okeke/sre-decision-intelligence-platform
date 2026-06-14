from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.decision import DecisionResponse
from app.schemas.generic_incidents import (
    GenericEvaluateRequest,
    GenericEvaluateResponse,
    GenericPersistRequest,
    GenericPersistResponse,
    GenericResolveRequest,
    GenericResolveResponse,
)
from app.schemas.incident_history import (
    IncidentDetailResponse,
    IncidentSummaryResponse,
    IncidentTimelineEventResponse,
)
from app.services.frontend_incident_service import (
    evaluate_frontend_live_incident,
    get_frontend_live_normalized_signals,
    get_frontend_live_rule_evaluations,
    get_frontend_live_signals,
    get_frontend_sample_decision,
    persist_frontend_live_incident,
    persist_frontend_sample_incident,
    resolve_frontend_live_incident,
)
from app.services.generic_incident_service import (
    evaluate_live_signals,
    evaluate_signals,
    persist_evaluated_incident,
    persist_live_incident,
    resolve_incident_by_id,
)
from app.services.incident_query_service import (
    get_incident_detail_response,
    get_incident_history_response,
    get_incident_timeline_response,
    get_open_incidents_response,
    get_resolved_incidents_response,
)

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])

@router.get("/frontend-availability", response_model=DecisionResponse)
def get_frontend_availability_incident() -> DecisionResponse:
    """
    Stable sample-based endpoint.

    Uses validated Phase 10/11 signals.
    This endpoint is safe for demos and tests because it does not depend on live systems.
    """
    return get_frontend_sample_decision()


@router.get("/frontend-availability/live", response_model=DecisionResponse)
def get_frontend_availability_live_incident() -> DecisionResponse:
    """
    Live collector-based endpoint.

    Collects signals from Prometheus, Kubernetes, and OpenSearch.
    Then evaluates the same rule engine used by the stable endpoint.
    """
    try:
        return evaluate_frontend_live_incident()

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
        return get_frontend_live_signals()

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to collect live frontend availability signals.",
                "reason": str(error),
            },
        ) from error

@router.get("/frontend-availability/live/signals/normalized")
def get_frontend_availability_live_normalized_signals() -> list[dict]:
    try:
        return get_frontend_live_normalized_signals()

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to collect or normalize live frontend availability signals.",
                "reason": str(error),
            },
        ) from error

@router.get("/frontend-availability/live/evaluations")
def get_frontend_availability_live_rule_evaluations() -> list[dict]:
    try:
        return get_frontend_live_rule_evaluations()

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to evaluate frontend availability rules.",
                "reason": str(error),
            },
        ) from error

@router.post("/frontend-availability/sample/persist")
def persist_frontend_availability_sample_incident(
    db: Session = Depends(get_db),) -> dict:
    """ 
    Persist the validated sample-based frontend availability decision.

    This endpoint is for development/demo validation only.
    It does not represent the current live cluster state.
    """

    incident = persist_frontend_sample_incident(db=db)

    return {
        "persisted": True,
        "incident_db_id": str(incident.id),
        "incident_id": incident.incident_id,
        "status": incident.status,
        "service": incident.service,
        "namespace": incident.namespace,
    }


@router.post("/frontend-availability/live/persist")
def persist_frontend_availability_live_incident(
    db: Session = Depends(get_db),) -> dict:   
    """
    Persist a live frontend availability incident only when the current live
    signals match the rule engine.

    If the cluster is healthy, no database record is created.
    """
    try:
        return persist_frontend_live_incident(db=db)

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
                "message": "Unable to persist live frontend availability incident.",
                "reason": str(error),
            },
        ) from error


@router.post("/frontend-availability/live/resolve")
def resolve_frontend_availability_live_incident(
    db: Session = Depends(get_db),
) -> dict:
    """
    Resolve the latest open frontend availability incident when live signals show
    the service path has recovered.
    """
    return resolve_frontend_live_incident(db=db)


@router.get("/history", response_model=list[IncidentSummaryResponse])
def get_incident_history(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    return get_incident_history_response(db=db, limit=limit)


@router.get("/open", response_model=list[IncidentSummaryResponse])
def get_open_incidents(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    return get_open_incidents_response(
        db=db,
        limit=limit,
    )


@router.get("/resolved", response_model=list[IncidentSummaryResponse])
def get_resolved_incidents(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    return get_resolved_incidents_response(
        db=db,
        limit=limit,
    )


@router.post("/evaluate", response_model=GenericEvaluateResponse)
def evaluate_incident_from_signals(
    request: GenericEvaluateRequest,
) -> dict:
    decision, evaluations = evaluate_signals(request.signals)

    if decision is None:
        return {
            "matched": False,
            "decision": None,
            "evaluations": evaluations,
            "message": "No matching rule found for provided signals.",
        }

    return {
        "matched": True,
        "decision": decision,
        "evaluations": evaluations,
        "message": "Matching rule found.",
    }


@router.post("/evaluate/live", response_model=GenericEvaluateResponse)
def evaluate_live_incident() -> dict:
    try:
        decision, evaluations, _signals = evaluate_live_signals()

        if decision is None:
            return {
                "matched": False,
                "decision": None,
                "evaluations": evaluations,
                "message": "No matching rule found for current live signals.",
            }

        return {
            "matched": True,
            "decision": decision,
            "evaluations": evaluations,
            "message": "Matching rule found for current live signals.",
        }

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to evaluate live incident signals.",
                "reason": str(error),
            },
        ) from error


@router.post("/persist", response_model=GenericPersistResponse)
def persist_incident_from_signals(
    request: GenericPersistRequest,
    db: Session = Depends(get_db),
) -> dict:
    return persist_evaluated_incident(
        db=db,
        signals=request.signals,
    )


@router.post("/live/persist", response_model=GenericPersistResponse)
def persist_current_live_incident(
    db: Session = Depends(get_db),
) -> dict:
    try:
        return persist_live_incident(db=db)

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to evaluate and persist live incident.",
                "reason": str(error),
            },
        ) from error


@router.get("/{incident_db_id}/timeline", response_model=list[IncidentTimelineEventResponse])
def get_incident_timeline(
    incident_db_id: UUID,
    db: Session = Depends(get_db),
) -> list[dict]:
    response = get_incident_timeline_response(
        db=db,
        incident_db_id=incident_db_id,
    )

    if response is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Incident not found.",
                "incident_db_id": str(incident_db_id),
            },
        )

    return response


@router.post("/{incident_db_id}/resolve", response_model=GenericResolveResponse)
def resolve_incident(
    incident_db_id: UUID,
    request: GenericResolveRequest,
    db: Session = Depends(get_db),
) -> dict:
    result = resolve_incident_by_id(
        db=db,
        incident_db_id=incident_db_id,
        recovery_signals=request.recovery_signals,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Incident not found.",
                "incident_db_id": str(incident_db_id),
            },
        )

    return result


@router.get("/{incident_db_id}", response_model=IncidentDetailResponse)
def get_incident_detail(
    incident_db_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    response = get_incident_detail_response(
        db=db,
        incident_db_id=incident_db_id,
    )

    if response is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Incident not found.",
                "incident_db_id": str(incident_db_id),
            },
        )

    return response




