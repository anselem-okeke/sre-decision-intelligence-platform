from app.slo.decision_mapping import evaluate_slo_for_decision
from app.slo.models import SloStatus


def test_slo_mapping_attaches_frontend_availability_budget_evaluation():
    signals = {
        "frontend_availability_5m": 0.990,
    }

    result = evaluate_slo_for_decision(
        slo_affected="frontend-availability",
        signals=signals,
    )

    assert result is not None
    assert result.slo_id == "frontend-availability-30d"
    assert result.target == 0.995
    assert result.current_value == 0.990
    assert result.status == SloStatus.EXHAUSTED


def test_slo_mapping_returns_none_for_unknown_slo_name():
    signals = {
        "frontend_availability_5m": 0.990,
    }

    result = evaluate_slo_for_decision(
        slo_affected="unknown-slo",
        signals=signals,
    )

    assert result is None


def test_slo_mapping_returns_none_when_signal_missing():
    result = evaluate_slo_for_decision(
        slo_affected="frontend-availability",
        signals={},
    )

    assert result is None
