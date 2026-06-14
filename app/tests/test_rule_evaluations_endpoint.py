from fastapi.testclient import TestClient

# from app.api.v1 import incidents
from app.services import frontend_incident_service
from app.main import app

client = TestClient(app)


def test_live_rule_evaluations_endpoint_returns_all_rule_results(monkeypatch):
    def fake_collect_signals():
        return {
            "probe_success": 0,
            "frontend_availability_5m": 0.6,
            "alert_state": "pending",
            "frontend_endpoints": "none",
            "frontend_pod_ready": True,
            "frontend_pod_status": "1/1 Running",
            "frontend_logs": "mostly INFO",
            "frontend_error_log_count": 13,
        }

    monkeypatch.setattr(
       frontend_incident_service,
       "collect_frontend_availability_live_signals",
       fake_collect_signals,
    )

    response = client.get(
        "/api/v1/incidents/frontend-availability/live/evaluations"
    )

    assert response.status_code == 200

    body = response.json()

    rule_ids = {item["rule_id"] for item in body}

    assert "frontend-service-selector-mismatch" in rule_ids
    assert "frontend-pod-crashloop" in rule_ids

    selector_rule = next(
        item for item in body if item["rule_id"] == "frontend-service-selector-mismatch"
    )

    assert selector_rule["matched"] is True
