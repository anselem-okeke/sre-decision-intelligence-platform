from app.slo.models import SliDefinition, SliType, SloDefinition, SloWindow


FRONTEND_AVAILABILITY_SLI = SliDefinition(
    id="frontend-availability",
    name="Frontend Availability",
    description="Measures whether the Bank of Anthos frontend user path is reachable.",
    service="frontend",
    sli_type=SliType.AVAILABILITY,
    source="prometheus",
    signal_name="frontend_availability_5m",
    unit="ratio",
    good_event_description="Synthetic frontend probe succeeds.",
    bad_event_description="Synthetic frontend probe fails.",
)


FRONTEND_LATENCY_SLI = SliDefinition(
    id="frontend-latency-p95",
    name="Frontend p95 Latency",
    description="Measures the p95 response latency of the frontend user path.",
    service="frontend",
    sli_type=SliType.LATENCY,
    source="prometheus",
    signal_name="frontend_latency_p95_ms",
    unit="milliseconds",
    good_event_description="p95 latency is below the accepted threshold.",
    bad_event_description="p95 latency exceeds the accepted threshold.",
)


TRANSACTION_SUCCESS_SLI = SliDefinition(
    id="transaction-success-rate",
    name="Transaction Success Rate",
    description="Measures successful completion of user banking transactions.",
    service="transaction",
    sli_type=SliType.SUCCESS_RATE,
    source="prometheus",
    signal_name="transaction_success_rate",
    unit="ratio",
    good_event_description="Transaction completes successfully.",
    bad_event_description="Transaction fails or times out.",
)


FRONTEND_AVAILABILITY_30D_SLO = SloDefinition(
    id="frontend-availability-30d",
    name="Frontend Availability 30d SLO",
    description="Frontend user path should be available at least 99.5% over 30 days.",
    sli=FRONTEND_AVAILABILITY_SLI,
    target=0.995,
    window=SloWindow.THIRTY_DAYS,
    warning_threshold=0.50,
    critical_threshold=0.90,
    tags=["frontend", "availability", "user-impact", "bank-of-anthos"],
)


FRONTEND_AVAILABILITY_5M_SLO = SloDefinition(
    id="frontend-availability-5m",
    name="Frontend Availability 5m Fast-Burn SLO",
    description="Short-window frontend availability used for fast-burn incident detection.",
    sli=FRONTEND_AVAILABILITY_SLI,
    target=0.995,
    window=SloWindow.FIVE_MINUTES,
    warning_threshold=0.30,
    critical_threshold=0.70,
    tags=["frontend", "availability", "fast-burn", "incident-detection"],
)


FRONTEND_LATENCY_30D_SLO = SloDefinition(
    id="frontend-latency-30d",
    name="Frontend Latency 30d SLO",
    description="Frontend p95 latency should remain within the expected user experience target.",
    sli=FRONTEND_LATENCY_SLI,
    target=0.99,
    window=SloWindow.THIRTY_DAYS,
    warning_threshold=0.50,
    critical_threshold=0.90,
    tags=["frontend", "latency", "user-experience"],
)


TRANSACTION_SUCCESS_30D_SLO = SloDefinition(
    id="transaction-success-30d",
    name="Transaction Success 30d SLO",
    description="Banking transactions should complete successfully at least 99.0% over 30 days.",
    sli=TRANSACTION_SUCCESS_SLI,
    target=0.990,
    window=SloWindow.THIRTY_DAYS,
    warning_threshold=0.50,
    critical_threshold=0.90,
    tags=["transaction", "business-impact", "bank-of-anthos"],
)
