from app.schemas.decision import DecisionResponse


def test_decision_response_schema_accepts_valid_payload():
    decision = DecisionResponse(
        incident_id="frontend-availability-breach",
        service="frontend",
        namespace="fintech-workload",
        severity="warning",
        status="detected",
        impact={
            "summary": "Frontend endpoint unavailable",
            "user_impact": "Users cannot access the frontend path.",
            "slo_affected": "frontend-availability",
        },
        signals={
            "prometheus": [
                {
                    "name": "probe_success",
                    "value": 0,
                    "meaning": "Frontend probe failed",
                }
            ],
            "kubernetes": [
                {
                    "name": "frontend_endpoints",
                    "value": "none",
                    "meaning": "Frontend Service had no endpoints",
                }
            ],
            "opensearch": [],
            "argocd": [],
        },
        evidence=[
            "probe_success dropped to 0",
            "frontend Service endpoints became empty",
        ],
        likely_root_cause={
            "summary": "Service selector mismatch",
            "confidence": "high",
            "category": "service-routing",
        },
        safe_action={
            "summary": "Restore the frontend Service selector",
            "command": None,
            "risk": "low",
        },
        metadata={
            "decision_engine_version": "0.1.0",
            "scenario": "frontend-availability-breach",
            "environment": "lab",
        },
    )

    assert decision.incident_id == "frontend-availability-breach"
    assert decision.impact.slo_affected == "frontend-availability"
    assert decision.signals.prometheus[0].name == "probe_success"
    assert decision.likely_root_cause.confidence == "high"
    assert decision.safe_action.risk == "low"
