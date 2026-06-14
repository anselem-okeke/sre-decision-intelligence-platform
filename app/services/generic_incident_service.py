from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.collectors.frontend_availability import collect_frontend_availability_live_signals
from app.db.repository import (
    get_incident_by_id,
    get_latest_open_incident,
    resolve_incident_with_evidence,
    save_decision_response,
)
from app.engine.decision_engine import MultiRuleEngine
from app.schemas.decision import DecisionResponse

RULES_DIR = Path("app/rules")


def evaluate_signals(signals: dict[str, Any]) -> tuple[DecisionResponse | None, list[dict[str, Any]]]:
    engine = MultiRuleEngine(RULES_DIR)
    evaluations = engine.evaluate_all(signals)

    try:
        decision = engine.evaluate(signals)
    except ValueError:
        return None, evaluations

    return decision, evaluations


def evaluate_live_signals() -> tuple[DecisionResponse | None, list[dict[str, Any]], dict[str, Any]]:
    signals = collect_frontend_availability_live_signals()
    decision, evaluations = evaluate_signals(signals)

    return decision, evaluations, signals


def persist_evaluated_incident(
    db: Session,
    signals: dict[str, Any],
) -> dict[str, Any]:
    decision, evaluations = evaluate_signals(signals)

    if decision is None:
        return {
            "persisted": False,
            "incident_db_id": None,
            "incident_id": None,
            "status": None,
            "service": None,
            "namespace": None,
            "message": "No matching rule found. Incident was not persisted.",
            "evaluations": evaluations,
        }

    existing_incident = get_latest_open_incident(
        db=db,
        incident_id=decision.incident_id,
        service=decision.service,
        namespace=decision.namespace,
    )

    if existing_incident is not None:
        return {
            "persisted": False,
            "incident_db_id": str(existing_incident.id),
            "incident_id": existing_incident.incident_id,
            "status": existing_incident.status,
            "service": existing_incident.service,
            "namespace": existing_incident.namespace,
            "message": "Open incident already exists. Duplicate incident was not created.",
            "evaluations": evaluations,
        }

    matched_evaluation = next(
        evaluation for evaluation in evaluations if evaluation["matched"] is True
    )

    incident = save_decision_response(
        db=db,
        decision_response=decision,
        input_signals=signals,
        rule_id=matched_evaluation["rule_id"],
        rule_matched=True,
    )

    return {
        "persisted": True,
        "incident_db_id": str(incident.id),
        "incident_id": incident.incident_id,
        "status": incident.status,
        "service": incident.service,
        "namespace": incident.namespace,
        "message": "Incident persisted successfully.",
        "evaluations": evaluations,
    }


def persist_live_incident(db: Session) -> dict[str, Any]:
    signals = collect_frontend_availability_live_signals()
    return persist_evaluated_incident(db=db, signals=signals)


def resolve_incident_by_id(
    db: Session,
    incident_db_id: UUID,
    recovery_signals: dict[str, Any],
) -> dict[str, Any] | None:
    incident = get_incident_by_id(
        db=db,
        incident_db_id=incident_db_id,
    )

    if incident is None:
        return None

    resolved_incident = resolve_incident_with_evidence(
        db=db,
        incident=incident,
        recovery_signals=recovery_signals,
    )

    return {
        "status": resolved_incident.status,
        "incident_db_id": str(resolved_incident.id),
        "incident_id": resolved_incident.incident_id,
        "service": resolved_incident.service,
        "namespace": resolved_incident.namespace,
        "message": "Incident resolved successfully.",
    }
