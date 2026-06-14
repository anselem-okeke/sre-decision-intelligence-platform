from fastapi.testclient import TestClient

from app.api.v1 import incidents
from app.main import app

client = TestClient(app)


def test_live_normalized_signals_endpoint_returns_normalized_signals(monkeypatch):
    def fake_collect_signals():
        return {
            "probe_success": 0.0,
            "frontend_availability_5m": 0.6,
            "alert_state": "pending",
            "frontend_endpoints": "none",
            "frontend_pod_ready": True,
            "frontend_pod_status": "1/1 Running",
            "frontend_logs": "mostly INFO",
            "frontend_error_log_count": 13,
        }

    monkeypatch.setattr(
        incidents,
        "collect_frontend_availability_live_signals",
        fake_collect_signals,
    )

    response = client.get(
        "/api/v1/incidents/frontend-availability/live/signals/normalized"
    )

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)
    assert len(body) >= 1

    probe_signal = next(signal for signal in body if signal["name"] == "probe_success")
    endpoint_signal = next(
        signal for signal in body if signal["name"] == "frontend_endpoints"
    )

    assert probe_signal["domain"] == "workload"
    assert probe_signal["source"] == "prometheus"
    assert probe_signal["severity"] == "critical"

    assert endpoint_signal["domain"] == "platform"
    assert endpoint_signal["source"] == "kubernetes"
    assert endpoint_signal["severity"] == "critical"
