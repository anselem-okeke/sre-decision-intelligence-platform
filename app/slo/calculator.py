from app.slo.models import ErrorBudgetEvaluation, SloDefinition, SloStatus


def calculate_error_budget(
    slo: SloDefinition,
    current_value: float,
) -> ErrorBudgetEvaluation:
    allowed_failure_ratio = 1.0 - slo.target
    current_failure_ratio = max(0.0, 1.0 - current_value)

    if allowed_failure_ratio <= 0:
        budget_consumed_ratio = 1.0
    else:
        budget_consumed_ratio = current_failure_ratio / allowed_failure_ratio

    budget_remaining_ratio = max(0.0, 1.0 - budget_consumed_ratio)

    status = classify_budget_status(
        budget_consumed_ratio=budget_consumed_ratio,
        warning_threshold=slo.warning_threshold,
        critical_threshold=slo.critical_threshold,
    )

    summary = build_budget_summary(
        slo=slo,
        current_value=current_value,
        budget_consumed_ratio=budget_consumed_ratio,
        budget_remaining_ratio=budget_remaining_ratio,
        status=status,
    )

    return ErrorBudgetEvaluation(
        slo_id=slo.id,
        slo_name=slo.name,
        service=slo.sli.service,
        sli_id=slo.sli.id,
        sli_name=slo.sli.name,
        target=slo.target,
        current_value=current_value,
        window=slo.window,
        allowed_failure_ratio=allowed_failure_ratio,
        current_failure_ratio=current_failure_ratio,
        budget_consumed_ratio=budget_consumed_ratio,
        budget_remaining_ratio=budget_remaining_ratio,
        status=status,
        summary=summary,
    )


def classify_budget_status(
    budget_consumed_ratio: float,
    warning_threshold: float,
    critical_threshold: float,
) -> SloStatus:
    if budget_consumed_ratio >= 1.0:
        return SloStatus.EXHAUSTED

    if budget_consumed_ratio >= critical_threshold:
        return SloStatus.BURNING_FAST

    if budget_consumed_ratio >= warning_threshold:
        return SloStatus.WARNING

    return SloStatus.HEALTHY


def build_budget_summary(
    slo: SloDefinition,
    current_value: float,
    budget_consumed_ratio: float,
    budget_remaining_ratio: float,
    status: SloStatus,
) -> str:
    consumed_percent = round(budget_consumed_ratio * 100, 2)
    remaining_percent = round(budget_remaining_ratio * 100, 2)
    current_percent = round(current_value * 100, 3)
    target_percent = round(slo.target * 100, 3)

    return (
        f"{slo.name}: current value is {current_percent}% against target "
        f"{target_percent}%. Error budget consumed: {consumed_percent}%. "
        f"Remaining budget: {remaining_percent}%. Status: {status.value}."
    )
