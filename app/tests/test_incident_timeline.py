from fastapi.testclient import TestClient
from pathlib import Path

from app.db.repository import get_incident_by_id, save_decision_response
from app.db.session import SessionLocal
from app.engine.decision_engine import RuleEngine
from app.engine.sample_signals import get_frontend_availability_sample_signals
from app.main import app
from app.tests.db_cleanup import clean_decision_tables

client = TestClient(app)

RULE_PATH = Path("app/rules/frontend_service_selector_mismatch.yaml")


def test_persisted_incident_contains_timeline_events():
    clean_decision_tables()

    signals = get_frontend_availability_sample_signals()
    decision = RuleEngine(RULE_PATH).evaluate(signals)

    db = SessionLocal()

    try:
        incident = save_decision_response(
            db=db,
            decision_response=decision,
            input_signals=signals,
            rule_id="frontend-service-selector-mismatch",
            rule_matched=True,
        )

        saved_incident = get_incident_by_id(db=db, incident_db_id=incident.id)

        event_types = [event.event_type for event in saved_incident.events]

        assert "incident_detected" in event_types
        assert "signals_collected" in event_types
        assert "rule_matched" in event_types
        assert "decision_created" in event_types

    finally:
        db.close()
        clean_decision_tables()


def test_timeline_endpoint_returns_events_in_order():
    clean_decision_tables()

    signals = get_frontend_availability_sample_signals()
    decision = RuleEngine(RULE_PATH).evaluate(signals)

    db = SessionLocal()

    try:
        incident = save_decision_response(
            db=db,
            decision_response=decision,
            input_signals=signals,
            rule_id="frontend-service-selector-mismatch",
            rule_matched=True,
        )

        response = client.get(f"/api/v1/incidents/{incident.id}/timeline")

        assert response.status_code == 200

        body = response.json()
        event_types = [event["event_type"] for event in body]

        assert event_types[0] == "incident_detected"
        assert "signals_collected" in event_types
        assert "rule_matched" in event_types
        assert "decision_created" in event_types

    finally:
        db.close()
        clean_decision_tables()
