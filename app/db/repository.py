from sqlalchemy.orm import Session

from app.db.models import Decision, EvidenceItem, Incident, RuleEvaluation, Signal
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
