from fastapi.testclient import TestClient
from app.tests.db_cleanup import clean_decision_tables

from app.db.models import Decision, Incident
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def test_persist_frontend_availability_incident_endpoint_stores_decision():
    # Base.metadata.create_all(bind=engine)
    clean_decision_tables()

    # response = client.post("/api/v1/incidents/frontend-availability/persist")
    response = client.post("/api/v1/incidents/frontend-availability/sample/persist")

    assert response.status_code == 200

    body = response.json()

    assert body["incident_id"] == "frontend-availability-breach"
    assert body["likely_root_cause"]["category"] == "service-routing"

    db = SessionLocal()

    try:
        saved_incident = (
            db.query(Incident)
            .filter(Incident.incident_id == "frontend-availability-breach")
            .order_by(Incident.created_at.desc())
            .first()
        )

        assert saved_incident is not None

        saved_decision = (
            db.query(Decision)
            .filter(Decision.incident_pk == saved_incident.id)
            .first()
        )

        assert saved_decision is not None
        assert saved_decision.root_cause_category == "service-routing"

    finally:
        db.close()
        clean_decision_tables()
