from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generic_evaluate_matches_frontend_selector_mismatch():
    signals = {
        "probe_success": 0,
        "frontend_availability_5m": 0.6,
        "alert_state": "pending",
        "frontend_endpoints": "none",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 13,
        "frontend_5xx_rate": 0.0,
        "frontend_latency_p95_ms": 120,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
        "pod_crashloop": False,
        "image_pull_backoff": False,
        "failed_scheduling": False,
        "node_not_ready": False,
        "oom_killed": False,
        "pvc_mount_failure": False,
        "cilium_drop_count": 0,
        "longhorn_volume_degraded": False,
        "argocd_sync_status": "Synced",
    }

    response = client.post(
        "/api/v1/incidents/evaluate",
        json={"signals": signals},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["matched"] is True
    assert body["decision"]["incident_id"] == "frontend-availability-breach"
    assert body["decision"]["likely_root_cause"]["category"] == "service-routing"


def test_generic_evaluate_returns_no_match_for_healthy_signals():
    signals = {
        "probe_success": 1,
        "frontend_availability_5m": 1.0,
        "alert_state": "inactive",
        "frontend_endpoints": "10.244.8.229:8080",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 0,
        "frontend_5xx_rate": 0.0,
        "frontend_latency_p95_ms": 120,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
        "pod_crashloop": False,
        "image_pull_backoff": False,
        "failed_scheduling": False,
        "node_not_ready": False,
        "oom_killed": False,
        "pvc_mount_failure": False,
        "cilium_drop_count": 0,
        "longhorn_volume_degraded": False,
        "argocd_sync_status": "Synced",
    }

    response = client.post(
        "/api/v1/incidents/evaluate",
        json={"signals": signals},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["matched"] is False
    assert body["decision"] is None
    assert body["message"] == "No matching rule found for provided signals."


def test_generic_evaluate_matches_platform_node_not_ready():
    signals = {
        "probe_success": 1,
        "frontend_availability_5m": 1.0,
        "alert_state": "inactive",
        "frontend_endpoints": "10.244.8.229:8080",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 0,
        "frontend_5xx_rate": 0.0,
        "frontend_latency_p95_ms": 120,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
        "pod_crashloop": False,
        "image_pull_backoff": False,
        "failed_scheduling": False,
        "node_not_ready": True,
        "oom_killed": False,
        "pvc_mount_failure": False,
        "cilium_drop_count": 0,
        "longhorn_volume_degraded": False,
        "argocd_sync_status": "Synced",
    }

    response = client.post(
        "/api/v1/incidents/evaluate",
        json={"signals": signals},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["matched"] is True
    assert body["decision"]["likely_root_cause"]["category"] == "node-health"


def test_generic_persist_creates_incident_for_matching_signals():
    from app.tests.db_cleanup import clean_decision_tables

    clean_decision_tables()

    signals = {
        "probe_success": 0,
        "frontend_availability_5m": 0.6,
        "alert_state": "pending",
        "frontend_endpoints": "none",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 13,
        "frontend_5xx_rate": 0.0,
        "frontend_latency_p95_ms": 120,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
        "pod_crashloop": False,
        "image_pull_backoff": False,
        "failed_scheduling": False,
        "node_not_ready": False,
        "oom_killed": False,
        "pvc_mount_failure": False,
        "cilium_drop_count": 0,
        "longhorn_volume_degraded": False,
        "argocd_sync_status": "Synced",
    }

    response = client.post(
        "/api/v1/incidents/persist",
        json={"signals": signals},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["persisted"] is True
    assert body["incident_id"] == "frontend-availability-breach"
    assert body["status"] == "detected"
    assert body["incident_db_id"] is not None

    clean_decision_tables()
