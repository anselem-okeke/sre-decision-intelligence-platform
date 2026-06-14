from pathlib import Path

from app.db.repository import (
    get_latest_open_incident,
    resolve_incident,
    save_decision_response,
)
from app.db.session import SessionLocal
from app.engine.decision_engine import RuleEngine
from app.engine.sample_signals import get_frontend_availability_sample_signals
from app.tests.db_cleanup import clean_decision_tables

RULE_PATH = Path("app/rules/frontend_service_selector_mismatch.yaml")


def test_resolve_latest_open_incident():
    clean_decision_tables()

    signals = get_frontend_availability_sample_signals()
    decision = RuleEngine(RULE_PATH).evaluate(signals)

    db = SessionLocal()

    try:
        saved_incident = save_decision_response(
            db=db,
            decision_response=decision,
            input_signals=signals,
            rule_id="frontend-service-selector-mismatch",
            rule_matched=True,
        )

        open_incident = get_latest_open_incident(
            db=db,
            incident_id=saved_incident.incident_id,
            service=saved_incident.service,
            namespace=saved_incident.namespace,
        )

        assert open_incident is not None
        assert open_incident.status != "resolved"

        resolved = resolve_incident(db=db, incident=open_incident)

        assert resolved.status == "resolved"
        assert resolved.resolved_at is not None

        no_open_incident = get_latest_open_incident(
            db=db,
            incident_id=saved_incident.incident_id,
            service=saved_incident.service,
            namespace=saved_incident.namespace,
        )

        assert no_open_incident is None

    finally:
        db.close()
        clean_decision_tables()
