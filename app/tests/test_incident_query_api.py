from fastapi.testclient import TestClient

from app.db.repository import save_decision_response
from app.db.session import SessionLocal
from app.engine.decision_engine import RuleEngine
from app.engine.sample_signals import get_frontend_availability_sample_signals
from app.main import app
from app.tests.db_cleanup import clean_decision_tables

client = TestClient(app)

RULE_PATH = "app/rules/frontend_availability_breach.yaml"


def test_get_incident_history_returns_persisted_incident():
    clean_decision_tables()

    signals = get_frontend_availability_sample_signals()
    decision = RuleEngine(RULE_PATH).evaluate(signals)

    db = SessionLocal()

    try:
        save_decision_response(
            db=db,
            decision_response=decision,
            input_signals=signals,
            rule_id="frontend-service-selector-mismatch",
            rule_matched=True,
        )

        response = client.get("/api/v1/incidents/history")

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1
        assert body[0]["incident_id"] == "frontend-availability-breach"
        assert body[0]["status"] == "detected"

    finally:
        db.close()
        clean_decision_tables()


def test_get_open_and_resolved_incidents_are_separated():
    clean_decision_tables()

    signals = get_frontend_availability_sample_signals()
    decision = RuleEngine(RULE_PATH).evaluate(signals)

    db = SessionLocal()

    try:
        save_decision_response(
            db=db,
            decision_response=decision,
            input_signals=signals,
            rule_id="frontend-service-selector-mismatch",
            rule_matched=True,
        )

        open_response = client.get("/api/v1/incidents/open")
        resolved_response = client.get("/api/v1/incidents/resolved")

        assert open_response.status_code == 200
        assert resolved_response.status_code == 200

        assert len(open_response.json()) == 1
        assert resolved_response.json() == []

    finally:
        db.close()
        clean_decision_tables()


def test_get_incident_detail_returns_signals_decisions_and_evidence():
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

        response = client.get(f"/api/v1/incidents/{incident.id}")

        assert response.status_code == 200

        body = response.json()

        assert body["incident_id"] == "frontend-availability-breach"
        assert len(body["signals"]) >= 1
        assert len(body["evidence"]) >= 1
        assert len(body["decisions"]) == 1
        assert len(body["rule_evaluations"]) == 1

    finally:
        db.close()
        clean_decision_tables()
