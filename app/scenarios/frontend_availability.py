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

FRONTEND_IMAGE_PULL_BACKOFF = ScenarioDefinition(
    id="frontend-image-pull-backoff",
    name="Frontend ImagePullBackOff",
    description="Detects when the frontend pod cannot start because Kubernetes cannot pull the image.",
    domain=ScenarioDomain.PLATFORM,
    status=ScenarioStatus.ACTIVE,
    required_signals=["frontend_pod_status", "frontend_pod_ready"],
    optional_signals=["image_pull_backoff"],
    root_cause_category="image-pull-failure",
    safe_action_summary="Check image name, tag, registry credentials, and imagePullSecrets before redeploying",
    risk_level="low",
    tags=["kubernetes", "image", "registry", "frontend", "platform"],
)


FRONTEND_FAILED_SCHEDULING = ScenarioDefinition(
    id="frontend-failed-scheduling",
    name="Frontend FailedScheduling",
    description="Detects when Kubernetes cannot schedule the frontend pod onto a node.",
    domain=ScenarioDomain.PLATFORM,
    status=ScenarioStatus.ACTIVE,
    required_signals=["failed_scheduling"],
    optional_signals=["node_not_ready"],
    root_cause_category="scheduling-failure",
    safe_action_summary="Inspect pod events, node capacity, taints, tolerations, affinity, and resource requests",
    risk_level="low",
    tags=["kubernetes", "scheduler", "capacity", "platform"],
)


NODE_NOT_READY = ScenarioDefinition(
    id="node-not-ready",
    name="Kubernetes NodeNotReady",
    description="Detects when one or more Kubernetes nodes are NotReady.",
    domain=ScenarioDomain.PLATFORM,
    status=ScenarioStatus.ACTIVE,
    required_signals=["node_not_ready"],
    optional_signals=["failed_scheduling"],
    root_cause_category="node-health",
    safe_action_summary="Inspect node conditions, kubelet status, disk pressure, memory pressure, and network connectivity",
    risk_level="low",
    tags=["kubernetes", "node", "platform", "health"],
)


FRONTEND_OOM_KILLED = ScenarioDefinition(
    id="frontend-oom-killed",
    name="Frontend OOMKilled",
    description="Detects when the frontend container was killed after exceeding its memory limit.",
    domain=ScenarioDomain.PLATFORM,
    status=ScenarioStatus.ACTIVE,
    required_signals=["oom_killed"],
    optional_signals=["frontend_pod_status"],
    root_cause_category="memory-pressure",
    safe_action_summary="Inspect memory usage, limits, recent traffic, and memory leak indicators before increasing limits",
    risk_level="medium",
    tags=["kubernetes", "oom", "memory", "frontend", "platform"],
)


PVC_MOUNT_FAILURE = ScenarioDefinition(
    id="pvc-mount-failure",
    name="PVC Mount Failure",
    description="Detects when Kubernetes cannot mount a persistent volume claim.",
    domain=ScenarioDomain.PLATFORM,
    status=ScenarioStatus.ACTIVE,
    required_signals=["pvc_mount_failure"],
    optional_signals=["longhorn_volume_degraded"],
    root_cause_category="storage-mount-failure",
    safe_action_summary="Inspect PVC, PV, storage class, Longhorn volume state, and pod mount events",
    risk_level="medium",
    tags=["kubernetes", "storage", "pvc", "platform"],
)


CILIUM_DROP_SPIKE = ScenarioDefinition(
    id="cilium-drop-spike",
    name="Cilium Drop Spike",
    description="Detects elevated Cilium/Hubble network drops.",
    domain=ScenarioDomain.PLATFORM,
    status=ScenarioStatus.ACTIVE,
    required_signals=["cilium_drop_count"],
    optional_signals=[],
    root_cause_category="network-drops",
    safe_action_summary="Inspect Hubble flows, Cilium policy verdicts, and affected services",
    risk_level="low",
    tags=["cilium", "hubble", "network", "platform"],
)


LONGHORN_VOLUME_DEGRADED = ScenarioDefinition(
    id="longhorn-volume-degraded",
    name="Longhorn Volume Degraded",
    description="Detects when Longhorn reports degraded volume health.",
    domain=ScenarioDomain.PLATFORM,
    status=ScenarioStatus.ACTIVE,
    required_signals=["longhorn_volume_degraded"],
    optional_signals=["pvc_mount_failure"],
    root_cause_category="storage-degradation",
    safe_action_summary="Inspect Longhorn volume replicas, node disk health, and replica rebuild status",
    risk_level="medium",
    tags=["longhorn", "storage", "volume", "platform"],
)


ARGOCD_SYNC_DRIFT = ScenarioDefinition(
    id="argocd-sync-drift",
    name="Argo CD Sync Drift",
    description="Detects when desired Git state and live Kubernetes state are out of sync.",
    domain=ScenarioDomain.PLATFORM,
    status=ScenarioStatus.ACTIVE,
    required_signals=["argocd_sync_status"],
    optional_signals=[],
    root_cause_category="gitops-drift",
    safe_action_summary="Inspect Argo CD diff before syncing or rolling back",
    risk_level="medium",
    tags=["argocd", "gitops", "drift", "platform"],
)
