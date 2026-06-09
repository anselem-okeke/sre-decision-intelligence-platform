from pathlib import Path
from typing import Any

from app.engine.rule_loader import load_rule
from app.schemas.decision import DecisionResponse


class RuleEngine:
    def __init__(self, rule_path: str | Path):
        self.rule = load_rule(rule_path)

    def evaluate(self, signals: dict[str, Any]) -> DecisionResponse:
        if not self._conditions_match(signals):
            raise ValueError("No matching rule found for provided signals")

        decision = self.rule["decision"]

        return DecisionResponse(
            incident_id=self.rule["scenario"],
            service="frontend",
            namespace="fintech-workload",
            severity=self.rule["severity"],
            status="detected",
            impact={
                "summary": decision["impact_summary"],
                "user_impact": decision["user_impact"],
                "slo_affected": decision["slo_affected"],
            },
            signals={
                "prometheus": [
                    {
                        "name": "probe_success",
                        "value": signals["probe_success"],
                        "meaning": "Frontend probe failed",
                    },
                    {
                        "name": "frontend_availability_5m",
                        "value": signals["frontend_availability_5m"],
                        "meaning": "Availability dropped below the 99% SLO target",
                    },
                    {
                        "name": "alert_state",
                        "value": signals["alert_state"],
                        "meaning": "SLO alert condition was detected by Prometheus",
                    },
                ],
                "kubernetes": [
                    {
                        "name": "frontend_endpoints",
                        "value": signals["frontend_endpoints"],
                        "meaning": "Frontend Service had no backend endpoints",
                    },
                    {
                        "name": "frontend_pod_status",
                        "value": signals["frontend_pod_status"],
                        "meaning": "Frontend pod was healthy while the service path was broken",
                    },
                ],
                "opensearch": [
                    {
                        "name": "frontend_logs",
                        "value": signals["frontend_logs"],
                        "meaning": "No dominant frontend application crash signal found",
                    }
                ],
                "argocd": [],
            },
            evidence=[
                "probe_success dropped to 0",
                "avg_over_time(probe_success[5m]) dropped to 0.7",
                "BankOfAnthosFrontendAvailabilitySLOBreach entered pending state",
                "frontend Service endpoints became empty",
                "frontend pod remained 1/1 Running",
                "probe_success recovered after Service selector was restored",
            ],
            likely_root_cause={
                "summary": decision["likely_root_cause"],
                "confidence": decision["confidence"],
                "category": decision["category"],
            },
            safe_action={
                "summary": decision["safe_action"],
                "command": decision["safe_action_command"],
                "risk": decision["risk"],
            },
            metadata={
                "decision_engine_version": "0.1.0",
                "scenario": self.rule["scenario"],
                "environment": "lab",
            },
        )

    def _conditions_match(self, signals: dict[str, Any]) -> bool:
        for condition in self.rule.get("conditions", []):
            signal_name = condition["signal"]
            operator = condition["operator"]
            expected_value = condition["value"]

            actual_value = signals.get(signal_name)

            if operator == "equals":
                if actual_value != expected_value:
                    return False
            else:
                raise ValueError(f"Unsupported operator: {operator}")

        return True
