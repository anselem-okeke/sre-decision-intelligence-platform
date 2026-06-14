from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.collectors.frontend_availability import collect_frontend_availability_live_signals
from app.db.repository import (
    get_latest_open_incident,
    resolve_incident_with_evidence,
    save_decision_response,
)
from app.engine.decision_engine import MultiRuleEngine, RuleEngine
from app.engine.sample_signals import get_frontend_availability_sample_signals
from app.schemas.decision import DecisionResponse
from app.signals.frontend_availability import normalize_frontend_availability_signals

RULE_PATH = Path("app/rules/frontend_service_selector_mismatch.yaml")
RULES_DIR = Path("app/rules")


def get_frontend_sample_decision() -> DecisionResponse:
    signals = get_frontend_availability_sample_signals()
    return RuleEngine(RULE_PATH).evaluate(signals)


def get_frontend_live_signals() -> dict[str, Any]:
    return collect_frontend_availability_live_signals()


def get_frontend_live_normalized_signals() -> list[dict[str, Any]]:
    raw_signals = collect_frontend_availability_live_signals()
    normalized_signals = normalize_frontend_availability_signals(raw_signals)

    return [signal.model_dump(mode="json") for signal in normalized_signals]


def get_frontend_live_rule_evaluations() -> list[dict[str, Any]]:
    signals = collect_frontend_availability_live_signals()
    engine = MultiRuleEngine(RULES_DIR)

    return engine.evaluate_all(signals)


def evaluate_frontend_live_incident() -> DecisionResponse:
    signals = collect_frontend_availability_live_signals()
    return RuleEngine(RULE_PATH).evaluate(signals)


def persist_frontend_sample_incident(db: Session):
    signals = get_frontend_availability_sample_signals()
    decision = RuleEngine(RULE_PATH).evaluate(signals)

    return save_decision_response(
        db=db,
        decision_response=decision,
        input_signals=signals,
        rule_id="frontend-service-selector-mismatch",
        rule_matched=True,
    )


def persist_frontend_live_incident(db: Session):
    signals = collect_frontend_availability_live_signals()
    decision = RuleEngine(RULE_PATH).evaluate(signals)

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
        }

    incident = save_decision_response(
        db=db,
        decision_response=decision,
        input_signals=signals,
        rule_id="frontend-service-selector-mismatch",
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
    }


def resolve_frontend_live_incident(db: Session) -> dict[str, Any]:
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
        return {
            "resolved": False,
            "message": "Frontend service is not recovered yet.",
            "signals": signals,
        }

    open_incident = get_latest_open_incident(
        db=db,
        incident_id="frontend-availability-breach",
        service="frontend",
        namespace="fintech-workload",
    )

    if open_incident is None:
        return {
            "resolved": False,
            "message": "No open frontend availability incident found.",
            "signals": signals,
        }

    resolved_incident = resolve_incident_with_evidence(
        db=db,
        incident=open_incident,
        recovery_signals=signals,
    )

    return {
        "resolved": True,
        "status": resolved_incident.status,
        "incident_id": resolved_incident.incident_id,
        "service": resolved_incident.service,
        "namespace": resolved_incident.namespace,
        "resolved_at": resolved_incident.resolved_at,
        "signals": signals,
    }
