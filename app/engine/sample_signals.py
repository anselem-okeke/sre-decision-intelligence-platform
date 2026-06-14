def get_frontend_availability_sample_signals() -> dict:
    return {
        "probe_success": 0,
        "frontend_availability_5m": 0.7,
        "alert_state": "pending",
        "frontend_endpoints": "none",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 13,

        # Workload signals
        "frontend_5xx_rate": 0.0,
        "frontend_latency_p95_ms": 120,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,

        # Platform signals for Phase 24
        "pod_crashloop": False,
        "image_pull_backoff": False,
        "failed_scheduling": False,
        "node_not_ready": False,
        "oom_killed": False,
        "pvc_mount_failure": False,
        "cilium_drop_count": 0,
        "longhorn_volume_degraded": False,
        "argocd_sync_status": "Synced",
    }
