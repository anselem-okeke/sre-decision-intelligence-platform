from app.scenarios.models import ScenarioDefinition, ScenarioDomain, ScenarioStatus


FRONTEND_SERVICE_SELECTOR_MISMATCH = ScenarioDefinition(
    id="frontend-service-selector-mismatch",
    name="Frontend Service Selector Mismatch",
    description=(
        "Detects when the Bank of Anthos frontend user path is unavailable "
        "because the Kubernetes frontend Service has no backend endpoints while "
        "the frontend pod remains ready."
    ),
    domain=ScenarioDomain.CORRELATION,
    status=ScenarioStatus.ACTIVE,
    required_signals=[
        "probe_success",
        "frontend_endpoints",
        "frontend_pod_ready",
    ],
    optional_signals=[
        "frontend_availability_5m",
        "alert_state",
        "frontend_pod_status",
        "frontend_logs",
        "frontend_error_log_count",
    ],
    root_cause_category="service-routing",
    safe_action_summary=(
        "Restore the frontend Service selector so it matches frontend pod labels"
    ),
    risk_level="low",
    tags=[
        "bank-of-anthos",
        "frontend",
        "kubernetes",
        "service",
        "slo",
        "routing",
    ],
)
