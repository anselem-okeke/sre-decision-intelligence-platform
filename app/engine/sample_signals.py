def get_frontend_availability_sample_signals() -> dict:
    return {
        "probe_success": 0,
        "frontend_availability_5m": 0.7,
        "alert_state": "pending",
        "frontend_endpoints": "none",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
    }
