from sqlalchemy.orm import Session, selectinload
from datetime import datetime, timezone
from uuid import UUID

from app.db.models import Decision, EvidenceItem, Incident, RuleEvaluation, Signal, IncidentEvent
from app.schemas.decision import DecisionResponse



def save_decision_response(
    db: Session,
    decision_response: DecisionResponse,
    input_signals: dict,
    rule_id: str,
    rule_matched: bool = True,
) -> Incident:
    incident = Incident(
        incident_id=decision_response.incident_id,
        service=decision_response.service,
        namespace=decision_response.namespace,
        severity=decision_response.severity,
        status=decision_response.status,
        scenario=decision_response.metadata.scenario,
    )

    db.add(incident)
    db.flush()

    add_incident_event(
        db=db,
        incident=incident,
        event_type="incident_detected",
        summary=f"Incident detected for service {decision_response.service}",
        source="decision-engine",
        payload={
            "incident_id": decision_response.incident_id,
            "service": decision_response.service,
            "namespace": decision_response.namespace,
            "severity": decision_response.severity,
            "status": decision_response.status,
        },
    )

    add_incident_event(
        db=db,
        incident=incident,
        event_type="signals_collected",
        summary="Signals collected and normalized for incident evaluation",
        source="collectors",
        payload=input_signals,
    )

    add_incident_event(
        db=db,
        incident=incident,
        event_type="rule_matched" if rule_matched else "rule_not_matched",
        summary=f"Rule evaluation completed for {rule_id}",
        source="rule-engine",
        payload={
            "rule_id": rule_id,
            "matched": rule_matched,
            "confidence": decision_response.likely_root_cause.confidence,
        },
    )

    add_incident_event(
        db=db,
        incident=incident,
        event_type="decision_created",
        summary="Incident decision created with root cause and safe action",
        source="decision-engine",
        payload={
            "root_cause": decision_response.likely_root_cause.summary,
            "category": decision_response.likely_root_cause.category,
            "safe_action": decision_response.safe_action.summary,
            "risk": decision_response.safe_action.risk,
        },
    )


    _save_signals(db, incident, decision_response)
    _save_evidence(db, incident, decision_response)
    _save_decision(db, incident, decision_response)
    _save_rule_evaluation(
        db=db,
        incident=incident,
        decision_response=decision_response,
        input_signals=input_signals,
        rule_id=rule_id,
        rule_matched=rule_matched,
    )

    db.commit()
    db.refresh(incident)

    return incident


def add_incident_event(
    *,
    db: Session,
    incident: Incident,
    event_type: str,
    summary: str,
    source: str,
    payload: dict | list | str | int | float | bool | None = None,
) -> IncidentEvent:
    event = IncidentEvent(
        incident=incident,
        event_type=event_type,
        summary=summary,
        source=source,
        payload=payload,
    )

    db.add(event)
    return event


def _save_signals(
    db: Session,
    incident: Incident,
    decision_response: DecisionResponse,
) -> None:
    signal_groups = decision_response.signals.model_dump()

    for source, signals in signal_groups.items():
        for signal in signals:
            db.add(
                Signal(
                    incident_pk=incident.id,
                    source=source,
                    name=signal["name"],
                    value=signal["value"],
                    meaning=signal["meaning"],
                )
            )


def _save_evidence(
    db: Session,
    incident: Incident,
    decision_response: DecisionResponse,
) -> None:
    for evidence_summary in decision_response.evidence:
        db.add(
            EvidenceItem(
                incident_pk=incident.id,
                source="decision-engine",
                category="correlation",
                summary=evidence_summary,
                payload={"summary": evidence_summary},
            )
        )


def _save_decision(
    db: Session,
    incident: Incident,
    decision_response: DecisionResponse,
) -> None:
    db.add(
        Decision(
            incident_pk=incident.id,
            impact_summary=decision_response.impact.summary,
            user_impact=decision_response.impact.user_impact,
            likely_root_cause=decision_response.likely_root_cause.summary,
            root_cause_category=decision_response.likely_root_cause.category,
            confidence=decision_response.likely_root_cause.confidence,
            safe_action_summary=decision_response.safe_action.summary,
            safe_action_command=decision_response.safe_action.command,
            decision_payload=decision_response.model_dump(mode="json"),
        )
    )


def _save_rule_evaluation(
    db: Session,
    incident: Incident,
    decision_response: DecisionResponse,
    input_signals: dict,
    rule_id: str,
    rule_matched: bool,
) -> None:
    db.add(
        RuleEvaluation(
            incident_pk=incident.id,
            rule_id=rule_id,
            matched=rule_matched,
            confidence=decision_response.likely_root_cause.confidence,
            reason=(
                "Rule matched and produced decision: "
                f"{decision_response.likely_root_cause.summary}"
            ),
            input_signals=input_signals,
        )
    )

def get_latest_open_incident(
    db: Session,
    incident_id: str,
    service: str,
    namespace: str,
) -> Incident | None:
    return (
        db.query(Incident)
        .filter(Incident.incident_id == incident_id)
        .filter(Incident.service == service)
        .filter(Incident.namespace == namespace)
        .filter(Incident.status != "resolved")
        .order_by(Incident.created_at.desc())
        .first()
    )


def resolve_incident(
    db: Session,
    incident: Incident,
) -> Incident:
    incident.status = "resolved"
    incident.resolved_at = datetime.now(timezone.utc)

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident

def add_resolution_evidence(
    db: Session,
    incident: Incident,
    recovery_signals: dict,
) -> None:
    db.add(
        EvidenceItem(
            incident_pk=incident.id,
            source="live-collector",
            category="resolution",
            summary="Frontend service recovery confirmed from live signals",
            payload={
                "probe_success": recovery_signals.get("probe_success"),
                "frontend_endpoints": recovery_signals.get("frontend_endpoints"),
                "frontend_pod_ready": recovery_signals.get("frontend_pod_ready"),
                "frontend_pod_status": recovery_signals.get("frontend_pod_status"),
                "frontend_availability_5m": recovery_signals.get("frontend_availability_5m"),
                "alert_state": recovery_signals.get("alert_state"),
            },
        )
    )


def resolve_incident_with_evidence(
    db: Session,
    incident: Incident,
    recovery_signals: dict,
) -> Incident:
    incident.status = "resolved"
    incident.resolved_at = datetime.now(timezone.utc)

    add_resolution_evidence(
        db=db,
        incident=incident,
        recovery_signals=recovery_signals,
    )

    add_incident_event(
        db=db,
        incident=incident,
        event_type="recovery_observed",
        summary="Frontend service recovery observed from live signals",
        source="live-collector",
        payload=recovery_signals,
    )

    add_incident_event(
        db=db,
        incident=incident,
        event_type="incident_resolved",
        summary="Incident marked as resolved after recovery validation",
        source="decision-api",
        payload={
            "incident_id": incident.incident_id,
            "service": incident.service,
            "namespace": incident.namespace,
            "resolved_at": str(incident.resolved_at),
        },
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident



def list_incidents(
    db: Session,
    status: str | None = None,
    limit: int = 20,
) -> list[Incident]:
    query = (
        db.query(Incident)
        .options(
            selectinload(Incident.signals),
            selectinload(Incident.evidence_items),
            selectinload(Incident.decisions),
            selectinload(Incident.rule_evaluations),
            selectinload(Incident.events),
        )
        .order_by(Incident.created_at.desc())
    )

    if status is not None:
        query = query.filter(Incident.status == status)

    return query.limit(limit).all()


def get_incident_by_id(
    db: Session,
    incident_db_id: UUID,
) -> Incident | None:
    return (
        db.query(Incident)
        .options(
            selectinload(Incident.decisions),
            selectinload(Incident.signals),
            selectinload(Incident.evidence_items),
            selectinload(Incident.rule_evaluations),
            selectinload(Incident.events),
        )
        .filter(Incident.id == incident_db_id)
        .first()
    )


