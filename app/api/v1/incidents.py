from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.get("/frontend-availability")
def get_frontend_availability_incident() -> dict:
    return {
        "incident_id": "frontend-availability-breach",
        "service": "frontend",
        "namespace": "fintech-workload",
        "severity": "warning",
        "status": "detected",
        "impact": {
            "summary": "Bank of Anthos frontend endpoint unavailable",
            "user_impact": "Users cannot reliably access the banking frontend service path.",
            "slo_affected": "frontend-availability",
        },
        "signals": {
            "prometheus": [
                {
                    "name": "probe_success",
                    "value": 0,
                    "meaning": "Frontend probe failed",
                },
                {
                    "name": "frontend_availability_5m",
                    "value": 0.7,
                    "meaning": "Availability dropped below the 99% SLO target",
                },
                {
                    "name": "alert_state",
                    "value": "pending",
                    "meaning": "SLO alert condition was detected by Prometheus",
                },
            ],
            "kubernetes": [
                {
                    "name": "frontend_endpoints",
                    "value": "none",
                    "meaning": "Frontend Service had no backend endpoints",
                },
                {
                    "name": "frontend_pod_status",
                    "value": "1/1 Running",
                    "meaning": "Frontend pod was healthy while the service path was broken",
                },
            ],
            "opensearch": [
                {
                    "name": "frontend_logs",
                    "value": "mostly INFO",
                    "meaning": "No dominant frontend application crash signal found",
                }
            ],
            "argocd": [],
        },
        "evidence": [
            "probe_success dropped to 0",
            "avg_over_time(probe_success[5m]) dropped to 0.7",
            "BankOfAnthosFrontendAvailabilitySLOBreach entered pending state",
            "frontend Service endpoints became empty",
            "frontend pod remained 1/1 Running",
            "probe_success recovered after Service selector was restored",
        ],
        "likely_root_cause": {
            "summary": "Frontend Service selector did not match frontend pod labels",
            "confidence": "high",
            "category": "service-routing",
        },
        "safe_action": {
            "summary": "Restore the frontend Service selector so it matches frontend pod labels",
            "command": (
                "kubectl patch svc frontend -n fintech-workload "
                "--type='json' "
                "-p='[{\"op\":\"remove\",\"path\":\"/spec/selector/slo-test\"}]'"
            ),
            "risk": "low",
        },
        "metadata": {
            "decision_engine_version": "0.1.0",
            "scenario": "frontend-availability-breach",
            "environment": "lab",
        },
    }
