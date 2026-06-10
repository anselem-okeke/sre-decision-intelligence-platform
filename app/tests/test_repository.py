from pathlib import Path

from app.db.base import Base
from app.db.models import Decision, EvidenceItem, Incident, RuleEvaluation, Signal
from app.db.repository import save_decision_response
from app.db.session import SessionLocal, engine
from app.engine.decision_engine import RuleEngine
from app.engine.sample_signals import get_frontend_availability_sample_signals

RULE_PATH = Path("app/rules/frontend_availability_breach.yaml")


def test_save_decision_response_persists_incident_decision_and_evidence():
    Base.metadata.create_all(bind=engine)

    signals = get_frontend_availability_sample_signals()
    engine_instance = RuleEngine(RULE_PATH)
    decision_response = engine_instance.evaluate(signals)

    db = SessionLocal()

    try:
        incident = save_decision_response(
            db=db,
            decision_response=decision_response,
            input_signals=signals,
            rule_id="frontend-service-selector-mismatch",
            rule_matched=True,
        )

        saved_incident = db.query(Incident).filter(Incident.id == incident.id).one()
        saved_signals = db.query(Signal).filter(Signal.incident_pk == incident.id).all()
        saved_evidence = db.query(EvidenceItem).filter(EvidenceItem.incident_pk == incident.id).all()
        saved_decisions = db.query(Decision).filter(Decision.incident_pk == incident.id).all()
        saved_rule_evaluations = (
            db.query(RuleEvaluation)
            .filter(RuleEvaluation.incident_pk == incident.id)
            .all()
        )

        assert saved_incident.incident_id == "frontend-availability-breach"
        assert saved_incident.service == "frontend"
        assert saved_incident.namespace == "fintech-workload"

        assert len(saved_signals) >= 1
        assert len(saved_evidence) >= 1
        assert len(saved_decisions) == 1
        assert len(saved_rule_evaluations) == 1

        assert saved_decisions[0].root_cause_category == "service-routing"
        assert saved_rule_evaluations[0].matched is True

    finally:
        db.close()
