from pathlib import Path

from app.engine.decision_engine import MultiRuleEngine
from app.scenarios.registry import scenario_registry

RULES_DIR = Path("app/rules")


def test_frontend_high_5xx_rule_matches():
    signals = {
        "probe_success": 0,
        "frontend_availability_5m": 0.8,
        "alert_state": "pending",
        "frontend_endpoints": "10.244.8.229:8080",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "ERROR 500 response",
        "frontend_error_log_count": 40,
        "frontend_5xx_rate": 0.12,
        "frontend_latency_p95_ms": 200,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
    }

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "application-errors"


def test_frontend_high_latency_rule_matches():
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
        "frontend_latency_p95_ms": 1500,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
    }

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "latency-degradation"


def test_transaction_error_spike_rule_matches():
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
        "frontend_latency_p95_ms": 200,
        "transaction_error_rate": 0.10,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
    }

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "transaction-failure"


def test_backend_timeout_spike_rule_matches():
    signals = {
        "probe_success": 1,
        "frontend_availability_5m": 1.0,
        "alert_state": "inactive",
        "frontend_endpoints": "10.244.8.229:8080",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "timeout to backend",
        "frontend_error_log_count": 0,
        "frontend_5xx_rate": 0.0,
        "frontend_latency_p95_ms": 200,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 25,
        "ledger_database_error_count": 0,
    }

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "dependency-timeout"


def test_ledger_database_error_spike_rule_matches():
    signals = {
        "probe_success": 1,
        "frontend_availability_5m": 1.0,
        "alert_state": "inactive",
        "frontend_endpoints": "10.244.8.229:8080",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "ledger database error",
        "frontend_error_log_count": 0,
        "frontend_5xx_rate": 0.0,
        "frontend_latency_p95_ms": 200,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 15,
    }

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "database-errors"


def test_workload_scenarios_are_registered():
    scenario_ids = {
        scenario.id for scenario in scenario_registry.list_scenarios()
    }

    assert "frontend-high-5xx-rate" in scenario_ids
    assert "frontend-high-latency" in scenario_ids
    assert "transaction-error-spike" in scenario_ids
    assert "backend-timeout-spike" in scenario_ids
    assert "ledger-database-error-spike" in scenario_ids
