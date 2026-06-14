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


FRONTEND_HIGH_5XX_RATE = ScenarioDefinition(
    id="frontend-high-5xx-rate",
    name="Frontend High 5xx Rate",
    description=(
        "Detects elevated frontend 5xx responses while Kubernetes routing and pod readiness appear healthy."
    ),
    domain=ScenarioDomain.WORKLOAD,
    status=ScenarioStatus.ACTIVE,
    required_signals=[
        "frontend_5xx_rate",
        "frontend_endpoints",
        "frontend_pod_ready",
    ],
    optional_signals=[
        "probe_success",
        "frontend_logs",
        "frontend_error_log_count",
    ],
    root_cause_category="application-errors",
    safe_action_summary=(
        "Inspect frontend logs, recent deployments, and upstream dependency errors before restarting"
    ),
    risk_level="medium",
    tags=["bank-of-anthos", "frontend", "5xx", "workload", "slo"],
)


FRONTEND_HIGH_LATENCY = ScenarioDefinition(
    id="frontend-high-latency",
    name="Frontend High Latency",
    description=(
        "Detects elevated frontend p95 latency while Kubernetes routing and pod readiness appear healthy."
    ),
    domain=ScenarioDomain.WORKLOAD,
    status=ScenarioStatus.ACTIVE,
    required_signals=[
        "frontend_latency_p95_ms",
        "frontend_endpoints",
        "frontend_pod_ready",
    ],
    optional_signals=[
        "frontend_logs",
        "backend_timeout_count",
    ],
    root_cause_category="latency-degradation",
    safe_action_summary=(
        "Inspect frontend latency metrics, upstream service latency, and recent rollout changes"
    ),
    risk_level="low",
    tags=["bank-of-anthos", "frontend", "latency", "workload", "slo"],
)


TRANSACTION_ERROR_SPIKE = ScenarioDefinition(
    id="transaction-error-spike",
    name="Transaction Error Spike",
    description=(
        "Detects elevated transaction failures while the frontend path remains reachable."
    ),
    domain=ScenarioDomain.WORKLOAD,
    status=ScenarioStatus.ACTIVE,
    required_signals=[
        "transaction_error_rate",
        "frontend_endpoints",
        "frontend_pod_ready",
    ],
    optional_signals=[
        "backend_timeout_count",
        "ledger_database_error_count",
    ],
    root_cause_category="transaction-failure",
    safe_action_summary=(
        "Inspect transaction service logs and dependency health before restarting workloads"
    ),
    risk_level="medium",
    tags=["bank-of-anthos", "transaction", "workload", "slo"],
)


BACKEND_TIMEOUT_SPIKE = ScenarioDefinition(
    id="backend-timeout-spike",
    name="Backend Timeout Spike",
    description=(
        "Detects elevated backend dependency timeout signals affecting user-facing operations."
    ),
    domain=ScenarioDomain.WORKLOAD,
    status=ScenarioStatus.ACTIVE,
    required_signals=[
        "backend_timeout_count",
        "frontend_endpoints",
        "frontend_pod_ready",
    ],
    optional_signals=[
        "frontend_latency_p95_ms",
        "transaction_error_rate",
    ],
    root_cause_category="dependency-timeout",
    safe_action_summary=(
        "Inspect backend service logs, service-to-service latency, and dependency availability"
    ),
    risk_level="low",
    tags=["bank-of-anthos", "backend", "timeout", "dependency", "workload"],
)


LEDGER_DATABASE_ERROR_SPIKE = ScenarioDefinition(
    id="ledger-database-error-spike",
    name="Ledger Database Error Spike",
    description=(
        "Detects elevated ledger or database-related errors affecting banking operations."
    ),
    domain=ScenarioDomain.WORKLOAD,
    status=ScenarioStatus.ACTIVE,
    required_signals=[
        "ledger_database_error_count",
        "frontend_endpoints",
        "frontend_pod_ready",
    ],
    optional_signals=[
        "transaction_error_rate",
        "backend_timeout_count",
    ],
    root_cause_category="database-errors",
    safe_action_summary=(
        "Inspect ledger service logs, database connectivity, and recent schema/config changes"
    ),
    risk_level="medium",
    tags=["bank-of-anthos", "ledger", "database", "workload"],
)
