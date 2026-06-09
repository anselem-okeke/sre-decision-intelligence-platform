from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_frontend_availability_incident_returns_decision_context():
    response = client.get("/api/v1/incidents/frontend-availability")

    assert response.status_code == 200

    body = response.json()

    assert body["incident_id"] == "frontend-availability-breach"
    assert body["service"] == "frontend"
    assert body["namespace"] == "fintech-workload"

    assert body["impact"]["slo_affected"] == "frontend-availability"
    assert body["likely_root_cause"]["category"] == "service-routing"
    assert body["likely_root_cause"]["confidence"] == "high"
    assert body["safe_action"]["risk"] == "low"

    assert "probe_success dropped to 0" in body["evidence"]
    assert "frontend Service endpoints became empty" in body["evidence"]
    assert "frontend pod remained 1/1 Running" in body["evidence"]
