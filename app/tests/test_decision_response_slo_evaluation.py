from pathlib import Path

from app.engine.decision_engine import MultiRuleEngine

RULES_DIR = Path("app/rules")


def test_decision_response_includes_slo_evaluation_for_frontend_availability():
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

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.slo_evaluation is not None
    assert decision.slo_evaluation.slo_id == "frontend-availability-30d"
    assert decision.slo_evaluation.target == 0.995
    assert decision.slo_evaluation.current_value == 0.6
    assert decision.slo_evaluation.status == "exhausted"
    assert decision.slo_evaluation.budget_consumed_ratio > 1.0
