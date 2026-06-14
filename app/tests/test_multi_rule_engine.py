from pathlib import Path

import pytest

from app.engine.decision_engine import MultiRuleEngine

RULES_DIR = Path("app/rules")


def test_multi_rule_engine_matches_service_selector_rule():
    signals = {
        "probe_success": 0,
        "frontend_availability_5m": 0.6,
        "alert_state": "pending",
        "frontend_endpoints": "none",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 13,
    }

    engine = MultiRuleEngine(RULES_DIR)
    decision = engine.evaluate(signals)

    assert decision.incident_id == "frontend-availability-breach"
    assert decision.likely_root_cause.category == "service-routing"


def test_multi_rule_engine_matches_crashloop_rule():
    signals = {
        "probe_success": 0,
        "frontend_availability_5m": 0.5,
        "alert_state": "pending",
        "frontend_endpoints": "none",
        "frontend_pod_ready": False,
        "frontend_pod_status": "CrashLoopBackOff",
        "frontend_logs": "ERROR application failed to start",
        "frontend_error_log_count": 55,
    }

    engine = MultiRuleEngine(RULES_DIR)
    decision = engine.evaluate(signals)

    assert decision.incident_id == "frontend-availability-breach"
    assert decision.likely_root_cause.category == "workload-crash"


def test_multi_rule_engine_returns_all_rule_evaluations():
    signals = {
        "probe_success": 1,
        "frontend_availability_5m": 1.0,
        "alert_state": "inactive",
        "frontend_endpoints": "10.244.8.229:8080",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 0,
    }

    engine = MultiRuleEngine(RULES_DIR)
    evaluations = engine.evaluate_all(signals)

    rule_ids = {evaluation["rule_id"] for evaluation in evaluations}

    assert "frontend-service-selector-mismatch" in rule_ids
    assert "frontend-pod-crashloop" in rule_ids

    assert all(evaluation["matched"] is False for evaluation in evaluations)


def test_multi_rule_engine_raises_when_no_rule_matches():
    signals = {
        "probe_success": 1,
        "frontend_availability_5m": 1.0,
        "alert_state": "inactive",
        "frontend_endpoints": "10.244.8.229:8080",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 0,
    }

    engine = MultiRuleEngine(RULES_DIR)

    with pytest.raises(ValueError, match="No matching rule found"):
        engine.evaluate(signals)
