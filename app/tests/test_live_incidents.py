from fastapi.testclient import TestClient

from app.main import app
from app.services import frontend_incident_service

client = TestClient(app)


def test_live_frontend_availability_endpoint_returns_decision_context(monkeypatch):
    def mock_collect_live_signals():
        return {
            "probe_success": 0,
            "frontend_availability_5m": 0.7,
            "alert_state": "pending",
            "frontend_endpoints": "none",
            "frontend_pod_ready": True,
            "frontend_pod_status": "1/1 Running",
            "frontend_logs": "mostly INFO",
            "frontend_error_log_count": 10,
        }

    monkeypatch.setattr(
        frontend_incident_service,
        "collect_frontend_availability_live_signals",
        mock_collect_live_signals,
    )

    response = client.get("/api/v1/incidents/frontend-availability/live")

    assert response.status_code == 200

    body = response.json()

    assert body["incident_id"] == "frontend-availability-breach"
    assert body["service"] == "frontend"
    assert body["namespace"] == "fintech-workload"
    assert body["likely_root_cause"]["category"] == "service-routing"
    assert body["safe_action"]["risk"] == "low"


def test_live_frontend_availability_endpoint_returns_404_when_no_rule_matches(monkeypatch):
    def mock_collect_live_signals():
        return {
            "probe_success": 1,
            "frontend_availability_5m": 1.0,
            "alert_state": "inactive",
            "frontend_endpoints": "10.244.8.229:8080",
            "frontend_pod_ready": True,
            "frontend_pod_status": "1/1 Running",
            "frontend_logs": "mostly INFO",
            "frontend_error_log_count": 0,
        }

    monkeypatch.setattr(
        frontend_incident_service,
        "collect_frontend_availability_live_signals",
        mock_collect_live_signals,
    )

    response = client.get("/api/v1/incidents/frontend-availability/live")

    assert response.status_code == 404

    body = response.json()

    assert body["detail"]["message"] == (
        "No matching incident rule found for current live signals."
    )


def test_live_frontend_availability_endpoint_returns_503_when_collection_fails(monkeypatch):
    def mock_collect_live_signals():
        raise RuntimeError("Prometheus unavailable")

    monkeypatch.setattr(
        frontend_incident_service,
        "collect_frontend_availability_live_signals",
        mock_collect_live_signals,
    )

    response = client.get("/api/v1/incidents/frontend-availability/live")

    assert response.status_code == 503

    body = response.json()

    assert body["detail"]["message"] == (
        "Unable to collect live frontend availability signals."
   )
    assert "Prometheus unavailable" in body["detail"]["reason"]
