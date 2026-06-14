from typing import Any

from app.slo.calculator import calculate_error_budget
from app.slo.models import ErrorBudgetEvaluation
from app.slo.registry import slo_registry


SLO_BY_AFFECTED_SLO_NAME = {
    "frontend-availability": "frontend-availability-30d",
    "frontend-latency": "frontend-latency-30d",
    "transaction-success-rate": "transaction-success-30d",
    "transaction-success": "transaction-success-30d",
}


SIGNAL_BY_SLO_ID = {
    "frontend-availability-30d": "frontend_availability_5m",
    "frontend-availability-5m": "frontend_availability_5m",
    "frontend-latency-30d": "frontend_latency_good_event_ratio",
    "transaction-success-30d": "transaction_success_rate",
}


def evaluate_slo_for_decision(
    slo_affected: str | None,
    signals: dict[str, Any],
) -> ErrorBudgetEvaluation | None:
    if not slo_affected:
        return None

    slo_id = SLO_BY_AFFECTED_SLO_NAME.get(slo_affected)

    if slo_id is None:
        return None

    slo = slo_registry.get_slo(slo_id)

    if slo is None:
        return None

    signal_name = SIGNAL_BY_SLO_ID.get(slo_id)

    if signal_name is None:
        return None

    current_value = signals.get(signal_name)

    if current_value is None:
        return None

    try:
        current_value_float = float(current_value)
    except (TypeError, ValueError):
        return None

    return calculate_error_budget(
        slo=slo,
        current_value=current_value_float,
    )
