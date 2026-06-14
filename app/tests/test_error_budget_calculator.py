from app.slo.calculator import calculate_error_budget
from app.slo.models import SloStatus
from app.slo.registry import slo_registry


def test_error_budget_is_healthy_when_current_value_meets_target():
    slo = slo_registry.require_slo("frontend-availability-30d")

    result = calculate_error_budget(
        slo=slo,
        current_value=0.999,
    )

    assert result.status == SloStatus.HEALTHY
    assert result.budget_consumed_ratio < slo.warning_threshold
    assert result.budget_remaining_ratio > 0


def test_error_budget_warning_when_budget_consumed_crosses_warning_threshold():
    slo = slo_registry.require_slo("frontend-availability-30d")

    result = calculate_error_budget(
        slo=slo,
        current_value=0.997,
    )

    assert result.status == SloStatus.WARNING


def test_error_budget_burning_fast_when_budget_consumed_crosses_critical_threshold():
    slo = slo_registry.require_slo("frontend-availability-30d")

    result = calculate_error_budget(
        slo=slo,
        current_value=0.9954,
    )

    # target 0.995 -> allowed failure 0.005
    # current 0.9954 -> current failure 0.0046
    # consumed = 0.0046 / 0.005 = 0.92
    assert result.status == SloStatus.BURNING_FAST


def test_error_budget_exhausted_when_current_value_below_allowed_budget():
    slo = slo_registry.require_slo("frontend-availability-30d")

    result = calculate_error_budget(
        slo=slo,
        current_value=0.990,
    )

    assert result.status == SloStatus.EXHAUSTED
    assert result.budget_consumed_ratio >= 1.0
    assert result.budget_remaining_ratio == 0.0


def test_budget_calculation_values_are_correct_for_frontend_availability():
    slo = slo_registry.require_slo("frontend-availability-30d")

    result = calculate_error_budget(
        slo=slo,
        current_value=0.9925,
    )

    # target 0.995 -> allowed failure 0.005
    # current 0.9925 -> current failure 0.0075
    # consumed = 0.0075 / 0.005 = 1.5
    assert round(result.allowed_failure_ratio, 4) == 0.005
    assert round(result.current_failure_ratio, 4) == 0.0075
    assert round(result.budget_consumed_ratio, 2) == 1.5
    assert result.status == SloStatus.EXHAUSTED
