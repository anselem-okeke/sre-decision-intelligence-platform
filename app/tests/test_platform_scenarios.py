from pathlib import Path

from app.engine.decision_engine import MultiRuleEngine
from app.scenarios.registry import scenario_registry

RULES_DIR = Path("app/rules")


def base_signals() -> dict:
    return {
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


def test_frontend_image_pull_backoff_rule_matches():
    signals = base_signals()
    signals["frontend_pod_ready"] = False
    signals["frontend_pod_status"] = "ImagePullBackOff"

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "image-pull-failure"


def test_failed_scheduling_rule_matches():
    signals = base_signals()
    signals["failed_scheduling"] = True

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "scheduling-failure"


def test_node_not_ready_rule_matches():
    signals = base_signals()
    signals["node_not_ready"] = True

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "node-health"


def test_oom_killed_rule_matches():
    signals = base_signals()
    signals["oom_killed"] = True

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "memory-pressure"


def test_pvc_mount_failure_rule_matches():
    signals = base_signals()
    signals["pvc_mount_failure"] = True

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "storage-mount-failure"


def test_cilium_drop_spike_rule_matches():
    signals = base_signals()
    signals["cilium_drop_count"] = 25

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "network-drops"


def test_longhorn_volume_degraded_rule_matches():
    signals = base_signals()
    signals["longhorn_volume_degraded"] = True

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "storage-degradation"


def test_argocd_sync_drift_rule_matches():
    signals = base_signals()
    signals["argocd_sync_status"] = "OutOfSync"

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "gitops-drift"


def test_platform_scenarios_are_registered():
    scenario_ids = {
        scenario.id for scenario in scenario_registry.list_scenarios()
    }

    assert "frontend-image-pull-backoff" in scenario_ids
    assert "frontend-failed-scheduling" in scenario_ids
    assert "node-not-ready" in scenario_ids
    assert "frontend-oom-killed" in scenario_ids
    assert "pvc-mount-failure" in scenario_ids
    assert "cilium-drop-spike" in scenario_ids
    assert "longhorn-volume-degraded" in scenario_ids
    assert "argocd-sync-drift" in scenario_ids
