from app.db.models import Incident


def incident_to_summary(incident: Incident) -> dict:
    return {
        "id": str(incident.id),
        "incident_id": incident.incident_id,
        "service": incident.service,
        "namespace": incident.namespace,
        "severity": incident.severity,
        "status": incident.status,
        "scenario": incident.scenario,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
    }


def incident_to_detail(incident: Incident) -> dict:
    return {
        **incident_to_summary(incident),
        "signals": [
            {
                "source": signal.source,
                "name": signal.name,
                "value": signal.value,
                "meaning": signal.meaning,
                "collected_at": signal.collected_at.isoformat()
                if signal.collected_at
                else None,
            }
            for signal in incident.signals
        ],
        "evidence": [
            {
                "source": evidence.source,
                "category": evidence.category,
                "summary": evidence.summary,
                "payload": evidence.payload,
                "created_at": evidence.created_at.isoformat()
                if evidence.created_at
                else None,
            }
            for evidence in incident.evidence_items
        ],
        "decisions": [
            {
                "impact_summary": decision.impact_summary,
                "user_impact": decision.user_impact,
                "likely_root_cause": decision.likely_root_cause,
                "root_cause_category": decision.root_cause_category,
                "confidence": decision.confidence,
                "safe_action_summary": decision.safe_action_summary,
                "safe_action_command": decision.safe_action_command,
                "created_at": decision.created_at.isoformat()
                if decision.created_at
                else None,
            }
            for decision in incident.decisions
        ],
        "rule_evaluations": [
            {
                "rule_id": rule.rule_id,
                "matched": rule.matched,
                "confidence": rule.confidence,
                "reason": rule.reason,
                "created_at": rule.created_at.isoformat()
                if rule.created_at
                else None,
            }
            for rule in incident.rule_evaluations
        ],
    }
