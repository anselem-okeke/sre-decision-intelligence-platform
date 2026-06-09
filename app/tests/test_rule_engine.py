from pathlib import Path

import pytest

from app.engine.decision_engine import RuleEngine
from app.engine.sample_signals import get_frontend_availability_sample_signals

RULE_PATH = Path("app/rules/frontend_availability_breach.yaml")


def test_rule_engine_detects_frontend_service_selector_mismatch():
    signals = get_frontend_availability_sample_signals()
    engine = RuleEngine(RULE_PATH)

    decision = engine.evaluate(signals)

    assert decision.incident_id == "frontend-availability-breach"
    assert decision.service == "frontend"
    assert decision.namespace == "fintech-workload"
    assert decision.severity == "warning"

    assert decision.impact.slo_affected == "frontend-availability"
    assert decision.likely_root_cause.category == "service-routing"
    assert decision.likely_root_cause.confidence == "high"
    assert decision.safe_action.risk == "low"


def test_rule_engine_does_not_match_when_probe_is_successful():
    signals = get_frontend_availability_sample_signals()
    signals["probe_success"] = 1

    engine = RuleEngine(RULE_PATH)

    with pytest.raises(ValueError, match="No matching rule found"):
        engine.evaluate(signals)


def test_rule_engine_does_not_match_when_endpoints_exist():
    signals = get_frontend_availability_sample_signals()
    signals["frontend_endpoints"] = "10.244.8.229:8080"

    engine = RuleEngine(RULE_PATH)

    with pytest.raises(ValueError, match="No matching rule found"):
        engine.evaluate(signals)


def test_rule_engine_does_not_match_when_pod_is_not_ready():
    signals = get_frontend_availability_sample_signals()
    signals["frontend_pod_ready"] = False

    engine = RuleEngine(RULE_PATH)

    with pytest.raises(ValueError, match="No matching rule found"):
        engine.evaluate(signals)
