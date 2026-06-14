from pathlib import Path
from typing import Any
from uuid import UUID

from app.schemas.incident_history import (
    IncidentDetailResponse,
    IncidentResolveResponse,
    IncidentSummaryResponse,
    IncidentTimelineEventResponse,
)

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.repository import (
    get_incident_by_id,
    get_latest_open_incident,
    list_incidents,
    resolve_incident_with_evidence,
    save_decision_response,
)
from app.db.session import get_db

from app.collectors.frontend_availability import collect_frontend_availability_live_signals
from app.signals.frontend_availability import normalize_frontend_availability_signals
from app.engine.decision_engine import RuleEngine, MultiRuleEngine
from app.engine.sample_signals import get_frontend_availability_sample_signals
from app.schemas.decision import DecisionResponse
from app.api.v1.incident_presenters import (
    incident_timeline_to_response,
    incident_to_detail,
    incident_to_summary,
)

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])

RULE_PATH = Path("app/rules/frontend_service_selector_mismatch.yaml")
RULES_DIR = Path("app/rules")


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

@router.get("/frontend-availability/live/signals/normalized")
def get_frontend_availability_live_normalized_signals() -> list[dict]:
    try:
        raw_signals = collect_frontend_availability_live_signals()
        normalized_signals = normalize_frontend_availability_signals(raw_signals)

        return [
            signal.model_dump(mode="json")
            for signal in normalized_signals
        ]

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
        signals = collect_frontend_availability_live_signals()
        engine = MultiRuleEngine(RULES_DIR)

        return engine.evaluate_all(signals)

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to evaluate frontend availability rules.",
                "reason": str(error),
            },
        ) from error

@router.post("/frontend-availability/sample/persist", response_model=DecisionResponse)
def persist_frontend_availability_sample_incident(
    db: Session = Depends(get_db),
) -> DecisionResponse:
    """
    Persist the validated sample-based frontend availability decision.

    This endpoint is for development/demo validation only.
    It does not represent the current live cluster state.
    """
    signals = get_frontend_availability_sample_signals()
    engine = RuleEngine(RULE_PATH)
    decision = engine.evaluate(signals)

    save_decision_response(
        db=db,
        decision_response=decision,
        input_signals=signals,
        rule_id="frontend-service-selector-mismatch",
        rule_matched=True,
    )

    return decision

@router.post("/frontend-availability/live/persist", response_model=DecisionResponse)
def persist_frontend_availability_live_incident(
    db: Session = Depends(get_db),
) -> DecisionResponse:
    """
    Persist a live frontend availability incident only when the current live
    signals match the rule engine.

    If the cluster is healthy, no database record is created.
    """
    try:
        signals = collect_frontend_availability_live_signals()
        engine = RuleEngine(RULE_PATH)
        decision = engine.evaluate(signals)

        save_decision_response(
            db=db,
            decision_response=decision,
            input_signals=signals,
            rule_id="frontend-service-selector-mismatch",
            rule_matched=True,
        )

        return decision

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "No matching live incident rule found. Nothing was persisted.",
                "reason": str(error),
            },
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to collect or persist live frontend availability signals.",
                "reason": str(error),
            },
        ) from error

@router.post(
    "/frontend-availability/live/resolve",
     response_model=IncidentResolveResponse
)
def resolve_frontend_availability_live_incident(
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Resolve the latest open frontend availability incident when live signals show
    the service path has recovered.
    """
    try:
        signals = collect_frontend_availability_live_signals()

        probe_success = signals.get("probe_success")
        frontend_endpoints = signals.get("frontend_endpoints")
        frontend_pod_ready = signals.get("frontend_pod_ready")

        service_recovered = (
            probe_success == 1.0
            and frontend_endpoints != "none"
            and frontend_pod_ready is True
        )

        if not service_recovered:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Frontend service has not recovered yet. Incident was not resolved.",
                    "signals": signals,
                },
            )

        incident = get_latest_open_incident(
            db=db,
            incident_id="frontend-availability-breach",
            service="frontend",
            namespace="fintech-workload",
        )

        if incident is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "No open frontend availability incident found to resolve.",
                },
            )

        resolved_incident = resolve_incident_with_evidence(
            db=db,
            incident=incident,
            recovery_signals=signals,
        )

        return {
            "status": "resolved",
            "incident_id": resolved_incident.incident_id,
            "service": resolved_incident.service,
            "namespace": resolved_incident.namespace,
            "resolved_at": resolved_incident.resolved_at,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to evaluate or resolve live frontend availability incident.",
                "reason": str(error),
            },
        ) from error


@router.get("/history", response_model=list[IncidentSummaryResponse])
def get_incident_history(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    incidents = list_incidents(
        db=db,
        limit=limit,
    )

    return [incident_to_summary(incident) for incident in incidents]


@router.get("/open", response_model=list[IncidentSummaryResponse])
def get_open_incidents(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    incidents = list_incidents(
        db=db,
        status="detected",
        limit=limit,
    )

    return [incident_to_summary(incident) for incident in incidents]


@router.get("/resolved", response_model=list[IncidentSummaryResponse])
def get_resolved_incidents(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    incidents = list_incidents(
        db=db,
        status="resolved",
        limit=limit,
    )

    return [incident_to_summary(incident) for incident in incidents]
    

@router.get("/{incident_db_id}/timeline", response_model=list[IncidentTimelineEventResponse])
def get_incident_timeline(
    incident_db_id: UUID,
    db: Session = Depends(get_db),
) -> list[dict]:
    incident = get_incident_by_id(
        db=db,
        incident_db_id=incident_db_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Incident not found.",
                "incident_db_id": str(incident_db_id),
            },
        )

    return incident_timeline_to_response(incident)


@router.get("/{incident_db_id}", response_model=IncidentDetailResponse)
def get_incident_detail(
    incident_db_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    incident = get_incident_by_id(
        db=db,
        incident_db_id=incident_db_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Incident not found.",
                "incident_db_id": str(incident_db_id),
            },
        )

    return incident_to_detail(incident)




