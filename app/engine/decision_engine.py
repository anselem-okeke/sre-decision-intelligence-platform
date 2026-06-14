from pathlib import Path
from typing import Any

from app.engine.rule_loader import load_rule, load_rules_from_directory
from app.schemas.decision import DecisionResponse
from app.schemas.impact import Impact
from app.schemas.root_cause import RootCause
from app.schemas.safe_action import SafeAction
from app.schemas.signal import Signal, SignalGroup


class RuleEngine:
    def __init__(self, rule_path: Path) -> None:
        self.rule = load_rule(rule_path)

    def evaluate(self, signals: dict[str, Any]) -> DecisionResponse:
        matched, _ = evaluate_rule(self.rule, signals)

        if not matched:
            raise ValueError("No matching rule found for provided signals")

        return build_decision_response(self.rule, signals)


class MultiRuleEngine:
    def __init__(self, rules_dir: Path) -> None:
        self.rules = load_rules_from_directory(rules_dir)

    def evaluate(self, signals: dict[str, Any]) -> DecisionResponse:
        matched_rules = self.evaluate_matches(signals)

        if not matched_rules:
            raise ValueError("No matching rule found for provided signals")

        best_match = matched_rules[0]

        return build_decision_response(best_match["rule"], signals)

    def evaluate_matches(self, signals: dict[str, Any]) -> list[dict[str, Any]]:
        evaluations: list[dict[str, Any]] = []

        for rule in self.rules:
            matched, failed_conditions = evaluate_rule(rule, signals)

            evaluations.append(
                {
                    "rule": rule,
                    "rule_id": rule["id"],
                    "scenario_id": rule.get("scenario_id") or rule.get("scenario"),
                    "matched": matched,
                    "priority": rule.get("priority", 0),
                    "failed_conditions": failed_conditions,
                }
            )

        matched_rules = [
            evaluation
            for evaluation in evaluations
            if evaluation["matched"]
        ]

        return sorted(
            matched_rules,
            key=lambda evaluation: evaluation["priority"],
            reverse=True,
        )

    def evaluate_all(self, signals: dict[str, Any]) -> list[dict[str, Any]]:
        evaluations: list[dict[str, Any]] = []

        for rule in self.rules:
            matched, failed_conditions = evaluate_rule(rule, signals)

            evaluations.append(
                {
                    "rule_id": rule["id"],
                    "scenario_id": rule.get("scenario_id") or rule.get("scenario"),
                    "name": rule.get("name"),
                    "matched": matched,
                    "priority": rule.get("priority", 0),
                    "failed_conditions": failed_conditions,
                }
            )

        return sorted(
            evaluations,
            key=lambda evaluation: evaluation["priority"],
            reverse=True,
        )


def evaluate_rule(rule: dict[str, Any], signals: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    failed_conditions: list[dict[str, Any]] = []

    for condition in rule.get("conditions", []):
        signal_name = condition["signal"]
        operator = condition["operator"]
        expected_value = condition["value"]
        actual_value = signals.get(signal_name)

        if not condition_matches(
            actual_value=actual_value,
            operator=operator,
            expected_value=expected_value,
        ):
            failed_conditions.append(
                {
                    "signal": signal_name,
                    "operator": operator,
                    "expected": expected_value,
                    "actual": actual_value,
                }
            )

    return len(failed_conditions) == 0, failed_conditions


def condition_matches(
    actual_value: Any,
    operator: str,
    expected_value: Any,
) -> bool:
    if operator == "equals":
        return actual_value == expected_value

    if operator == "not_equals":
        return actual_value != expected_value

    if operator == "contains":
        if actual_value is None:
            return False

        return str(expected_value) in str(actual_value)

    if operator == "greater_than":
        if actual_value is None:
            return False

        return float(actual_value) > float(expected_value)

    if operator == "less_than":
        if actual_value is None:
            return False

        return float(actual_value) < float(expected_value)

    raise ValueError(f"Unsupported operator: {operator}")


def build_decision_response(
    rule: dict[str, Any],
    signals: dict[str, Any],
) -> DecisionResponse:
    decision = rule["decision"]

    return DecisionResponse(
        incident_id=rule.get("scenario_id") or rule.get("scenario"),
        service="frontend",
        namespace="fintech-workload",
        severity=rule["severity"],
        status="detected",
        impact=Impact(
            summary=decision["impact_summary"],
            user_impact=decision["user_impact"],
            slo_affected=decision["slo_affected"],
        ),
        signals=SignalGroup(
            prometheus=[
                Signal(
                    name="probe_success",
                    value=signals.get("probe_success"),
                    meaning="Frontend probe failed"
                    if signals.get("probe_success") == 0
                    else "Frontend probe succeeded",
                ),
                Signal(
                    name="frontend_availability_5m",
                    value=signals.get("frontend_availability_5m"),
                    meaning="Frontend availability over the last 5 minutes",
                ),
                Signal(
                    name="alert_state",
                    value=signals.get("alert_state"),
                    meaning="Prometheus alert state for frontend availability",
                ),
            ],
            kubernetes=[
                Signal(
                    name="frontend_endpoints",
                    value=signals.get("frontend_endpoints"),
                    meaning="Frontend Service backend endpoints",
                ),
                Signal(
                    name="frontend_pod_status",
                    value=signals.get("frontend_pod_status"),
                    meaning="Frontend pod status summary",
                ),
            ],
            opensearch=[
                Signal(
                    name="frontend_logs",
                    value=signals.get("frontend_logs"),
                    meaning="Frontend application log summary",
                ),
            ],
            argocd=[],
        ),
        evidence=[
            "Rule matched: " + rule["name"],
            "Scenario evaluated: " + str(rule.get("scenario_id") or rule.get("scenario")),
            "Root cause category: " + decision["category"],
        ],
        likely_root_cause=RootCause(
            summary=decision["likely_root_cause"],
            confidence=decision["confidence"],
            category=decision["category"],
        ),
        safe_action=SafeAction(
            summary=decision["safe_action"],
            command=decision.get("safe_action_command"),
            risk=decision["risk"],
        ),
        metadata={
            "decision_engine_version": "0.1.0",
            "scenario": rule.get("scenario_id") or rule.get("scenario"),
            "environment": "lab",
        },
    )
