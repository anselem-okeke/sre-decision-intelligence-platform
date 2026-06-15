# Phase 22 — Multi-rule / Multi-scenario Rule Engine

## 1. Purpose

Phase 22 upgrades the SRE Decision Intelligence Platform from a single-rule evaluator into a multi-rule and multi-scenario decision engine.

Before this phase, the platform mainly evaluated one YAML rule:

```text
frontend_service_selector_mismatch.yaml
```

That was enough for the first complete vertical slice, but not enough for a real decision-intelligence platform. A real incident can have many possible causes:

```text
Service selector mismatch
CrashLoopBackOff
ImagePullBackOff
FailedScheduling
High 5xx rate
Backend timeout
Node pressure
PVC mount failure
GitOps drift
```

Phase 22 introduces the foundation for evaluating multiple rules, ranking matches by priority, returning the best decision, and exposing all rule evaluations for debugging and operational transparency.

---

## 2. Core Design Change

### Before Phase 22

```text
signals
  ↓
one YAML rule
  ↓
DecisionResponse or ValueError
```

### After Phase 22

```text
signals
  ↓
load all YAML rules from app/rules/
  ↓
evaluate every rule
  ↓
collect matched and failed rules
  ↓
sort matching rules by priority
  ↓
return best DecisionResponse
```

This means the platform can now reason over many known incident patterns instead of one hardcoded scenario.

---

## 3. Why This Phase Matters

Phase 22 is important because it separates **signals** from **incident interpretation**.

A single signal set can be evaluated against many possible explanations:

```text
probe_success = 0
frontend_endpoints = none
frontend_pod_ready = true
```

This strongly points to:

```text
frontend-service-selector-mismatch
```

But another signal set:

```text
probe_success = 0
frontend_pod_ready = false
frontend_pod_status = CrashLoopBackOff
```

points to:

```text
frontend-pod-crashloop
```

The rule engine should not be hardcoded to one explanation. It should evaluate all known rules and select the best supported one.

---

## 4. Files Introduced or Modified

Phase 22 modifies these areas:

```text
app/rules/
├── frontend_service_selector_mismatch.yaml
└── frontend_pod_crashloop.yaml

app/engine/
├── rule_loader.py
└── decision_engine.py

app/api/v1/
└── incidents.py

app/tests/
├── test_multi_rule_engine.py
└── test_rule_evaluations_endpoint.py
```

---

## 5. Rule File Naming

The existing rule was renamed from a broad scenario-style name:

```text
frontend_availability_breach.yaml
```

to a root-cause-specific name:

```text
frontend_service_selector_mismatch.yaml
```

This is more accurate because the rule describes one specific explanation for a broader frontend availability problem.

---

## 6. Scenario ID vs Rule ID

Phase 22 introduces an important distinction:

```text
scenario_id = frontend-availability-breach
rule_id     = frontend-service-selector-mismatch
```

### Scenario

A scenario is the broader user-impact condition.

Example:

```text
frontend-availability-breach
```

Meaning:

```text
The frontend user path is unavailable or degraded.
```

### Rule

A rule is one possible explanation for that scenario.

Examples:

```text
frontend-service-selector-mismatch
frontend-pod-crashloop
frontend-image-pull-backoff
frontend-high-5xx-rate
```

This design allows one scenario to have many rules.

---

## 7. Service Selector Mismatch Rule

File:

```text
app/rules/frontend_service_selector_mismatch.yaml
```

Example content:

```yaml
id: frontend-service-selector-mismatch
scenario_id: frontend-availability-breach
name: Frontend Service Selector Mismatch
description: Frontend user path is unavailable because the Kubernetes Service has no backend endpoints while the pod is ready.
priority: 100
severity: warning
domain: correlation

conditions:
  - signal: probe_success
    operator: equals
    value: 0

  - signal: frontend_endpoints
    operator: equals
    value: none

  - signal: frontend_pod_ready
    operator: equals
    value: true

decision:
  impact_summary: Bank of Anthos frontend endpoint unavailable
  user_impact: Users cannot reliably access the banking frontend service path.
  slo_affected: frontend-availability
  likely_root_cause: Frontend Service selector did not match frontend pod labels
  confidence: high
  category: service-routing
  safe_action: Restore the frontend Service selector so it matches frontend pod labels
  safe_action_command: kubectl patch svc frontend -n fintech-workload --type='json' -p='[{"op":"remove","path":"/spec/selector/slo-test"}]'
  risk: low
```

### Meaning

This rule says:

```text
If users cannot reach the frontend,
and the Service has no endpoints,
and the pod is ready,
then the likely root cause is Service selector mismatch.
```

---

## 8. Frontend Pod CrashLoop Rule

File:

```text
app/rules/frontend_pod_crashloop.yaml
```

Example content:

```yaml
id: frontend-pod-crashloop
scenario_id: frontend-availability-breach
name: Frontend Pod CrashLoopBackOff
description: Frontend user path is unavailable because the frontend pod is repeatedly crashing.
priority: 90
severity: critical
domain: platform

conditions:
  - signal: probe_success
    operator: equals
    value: 0

  - signal: frontend_pod_ready
    operator: equals
    value: false

  - signal: frontend_pod_status
    operator: contains
    value: CrashLoopBackOff

decision:
  impact_summary: Bank of Anthos frontend pod is crashing
  user_impact: Users cannot reliably access the banking frontend service because the frontend workload is unhealthy.
  slo_affected: frontend-availability
  likely_root_cause: Frontend pod is in CrashLoopBackOff
  confidence: high
  category: workload-crash
  safe_action: Inspect frontend pod logs and recent rollout before restarting or rolling back the deployment
  safe_action_command: kubectl logs -n fintech-workload deploy/frontend --previous
  risk: medium
```

### Meaning

This rule says:

```text
If users cannot reach the frontend,
and the frontend pod is not ready,
and the pod status contains CrashLoopBackOff,
then the likely root cause is a crashing frontend workload.
```

---

## 9. Rule Priority

Every rule has a priority:

```yaml
priority: 100
```

Higher priority wins when more than one rule matches.

Example:

```text
frontend-service-selector-mismatch → priority 100
frontend-pod-crashloop            → priority 90
```

If both rules somehow match, the engine selects the highest-priority rule.

This makes rule resolution deterministic.

---

## 10. Supported Operators

Phase 22 supports these condition operators:

```text
equals
not_equals
contains
greater_than
less_than
```

Example:

```yaml
conditions:
  - signal: frontend_pod_status
    operator: contains
    value: CrashLoopBackOff
```

This means:

```text
Check whether the actual frontend_pod_status string contains CrashLoopBackOff.
```

---

## 11. Important Rule Engine Safety Fix

A missing signal must not accidentally match a rule.

The condition matcher should start like this:

```python
def condition_matches(
    actual_value: Any,
    operator: str,
    expected_value: Any,
) -> bool:
    if actual_value is None:
        return False
```

This prevents bugs like:

```python
None != "Synced"  # True
```

Without this guard, a missing `argocd_sync_status` could falsely match a GitOps drift rule.

Correct behavior:

```text
missing signal → rule condition fails → rule does not match
```

---

## 12. Rule Loader

File:

```text
app/engine/rule_loader.py
```

Purpose:

```text
Load one YAML rule file or all YAML rules from a directory.
```

Example implementation:

```python
from pathlib import Path
from typing import Any

import yaml


def load_rule(rule_path: Path) -> dict[str, Any]:
    with rule_path.open("r", encoding="utf-8") as file:
        rule = yaml.safe_load(file)

    if not isinstance(rule, dict):
        raise ValueError(f"Invalid rule file: {rule_path}")

    return rule


def load_rules_from_directory(rules_dir: Path) -> list[dict[str, Any]]:
    rule_files = sorted(rules_dir.glob("*.yaml"))

    rules: list[dict[str, Any]] = []

    for rule_file in rule_files:
        rules.append(load_rule(rule_file))

    return rules
```

---

## 13. Single Rule Engine

The existing `RuleEngine` remains useful for backwards compatibility.

It evaluates one rule file:

```python
engine = RuleEngine(Path("app/rules/frontend_service_selector_mismatch.yaml"))
decision = engine.evaluate(signals)
```

This keeps old frontend-specific endpoints working.

---

## 14. MultiRuleEngine

The new engine loads all rules:

```python
engine = MultiRuleEngine(Path("app/rules"))
```

It exposes three important methods:

```python
evaluate(signals)
evaluate_matches(signals)
evaluate_all(signals)
```

### `evaluate(signals)`

Returns the best matching `DecisionResponse`.

If no rule matches:

```python
raise ValueError("No matching rule found for provided signals")
```

### `evaluate_matches(signals)`

Returns only matched rules, sorted by priority.

### `evaluate_all(signals)`

Returns all rule evaluations, including matched and failed rules.

This is useful for debug endpoints and transparency.

---

## 15. Evaluation Output Shape

The rule evaluation endpoint returns objects like:

```json
{
  "rule_id": "frontend-service-selector-mismatch",
  "scenario_id": "frontend-availability-breach",
  "name": "Frontend Service Selector Mismatch",
  "matched": true,
  "priority": 100,
  "failed_conditions": []
}
```

For failed rules:

```json
{
  "rule_id": "frontend-pod-crashloop",
  "scenario_id": "frontend-availability-breach",
  "name": "Frontend Pod CrashLoopBackOff",
  "matched": false,
  "priority": 90,
  "failed_conditions": [
    {
      "signal": "frontend_pod_ready",
      "operator": "equals",
      "expected": false,
      "actual": true
    }
  ]
}
```

This is valuable because the API does not only say what matched. It also explains why other rules did not match.

---

## 16. API Endpoint Added

Phase 22 adds this debug/evaluation endpoint:

```http
GET /api/v1/incidents/frontend-availability/live/evaluations
```

This endpoint:

```text
collects live frontend signals
evaluates all rules
returns matched and failed rule results
```

It does not persist anything.

It is read-only.

---

## 17. Example Healthy Output

On a healthy cluster, expected behavior is:

```text
all rules matched = false
```

Example:

```json
[
  {
    "rule_id": "frontend-service-selector-mismatch",
    "matched": false,
    "failed_conditions": [
      {
        "signal": "probe_success",
        "expected": 0,
        "actual": 1.0
      },
      {
        "signal": "frontend_endpoints",
        "expected": "none",
        "actual": "10.244.8.229:8080"
      }
    ]
  }
]
```

This proves the engine is evaluating rules but correctly not raising an incident.

---

## 18. Example Broken Selector Output

When the frontend Service selector is broken:

```text
probe_success = 0
frontend_endpoints = none
frontend_pod_ready = true
```

Expected evaluation:

```json
{
  "rule_id": "frontend-service-selector-mismatch",
  "matched": true,
  "priority": 100,
  "failed_conditions": []
}
```

Other rules should remain unmatched.

---

## 19. Tests Added

Phase 22 includes:

```text
app/tests/test_multi_rule_engine.py
app/tests/test_rule_evaluations_endpoint.py
```

---

## 20. `test_multi_rule_engine.py`

This test file verifies:

```text
MultiRuleEngine matches service selector mismatch
MultiRuleEngine matches pod CrashLoopBackOff
MultiRuleEngine returns all rule evaluations
MultiRuleEngine raises ValueError when no rule matches
```

### Run it

```bash
pytest app/tests/test_multi_rule_engine.py -q
```

Expected:

```text
4 passed
```

---

## 21. `test_rule_evaluations_endpoint.py`

This test verifies the live evaluation endpoint returns all rule results.

It uses monkeypatching to avoid calling real live collectors.

After the Phase 26 service refactor, the monkeypatch target should be:

```python
from app.services import frontend_incident_service

monkeypatch.setattr(
    frontend_incident_service,
    "collect_frontend_availability_live_signals",
    fake_collect_signals,
)
```

Not:

```python
from app.api.v1 import incidents
```

because collector orchestration moved into the service layer.

### Run it

```bash
pytest app/tests/test_rule_evaluations_endpoint.py -q
```

Expected:

```text
1 passed
```

---

## 22. Manual Validation — Route Registration

Run:

```bash
python - <<'PY'
from app.main import app

for route in app.routes:
    if "/api/v1/incidents" in route.path:
        print(route.path, route.methods)
PY
```

Expected route:

```text
/api/v1/incidents/frontend-availability/live/evaluations {'GET'}
```

---

## 23. Manual Validation — Healthy Cluster

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Call:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/evaluations | jq
```

Expected:

```text
all rules matched = false
```

This is correct when the frontend is healthy.

---

## 24. Manual Validation — Broken Service Selector

Break the frontend Service selector:

```bash
kubectl patch svc frontend -n fintech-workload \
  --type='merge' \
  -p '{"spec":{"selector":{"app":"frontend","application":"bank-of-anthos","environment":"development","team":"frontend","tier":"web","slo-test":"broken"}}}'
```

Wait for probes to observe the failure:

```bash
sleep 60
```

Check endpoints:

```bash
kubectl get endpoints frontend -n fintech-workload
```

Expected:

```text
frontend   <none>
```

Call the evaluations endpoint:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/evaluations | jq
```

Expected:

```text
frontend-service-selector-mismatch matched = true
frontend-pod-crashloop matched = false
```

Restore the Service selector:

```bash
kubectl patch svc frontend -n fintech-workload \
  --type='json' \
  -p='[
    {
      "op": "remove",
      "path": "/spec/selector/slo-test"
    }
  ]'
```

---

## 25. Manual Validation — CrashLoop Synthetic Signals

You can validate the CrashLoop rule without breaking the real cluster by using the engine directly:

```bash
python - <<'PY'
from pathlib import Path
from app.engine.decision_engine import MultiRuleEngine

signals = {
    "probe_success": 0,
    "frontend_availability_5m": 0.5,
    "alert_state": "pending",
    "frontend_endpoints": "none",
    "frontend_pod_ready": False,
    "frontend_pod_status": "CrashLoopBackOff",
    "frontend_logs": "ERROR application failed to start",
    "frontend_error_log_count": 55,
}

decision = MultiRuleEngine(Path("app/rules")).evaluate(signals)
print(decision.likely_root_cause.category)
PY
```

Expected:

```text
workload-crash
```

---

## 26. Full Regression Validation

Run:

```bash
pytest app/tests/test_multi_rule_engine.py -q
pytest app/tests/test_rule_evaluations_endpoint.py -q
pytest
```

Expected after the current project state:

```text
62 passed
```

Warnings are acceptable and are not blockers for Phase 22.

---

## 27. Common Issue — Wrong Schema Imports

During implementation, the engine originally assumed schema classes that did not exist:

```python
from app.schemas.signal import DecisionSignals, Signal
```

But the real schema was:

```python
class Signal(BaseModel):
    ...

class SignalGroup(BaseModel):
    ...
```

Correct import:

```python
from app.schemas.signal import Signal, SignalGroup
```

Correct usage:

```python
signals=SignalGroup(
    prometheus=[...],
    kubernetes=[...],
    opensearch=[...],
    argocd=[],
)
```

---

## 28. Common Issue — Missing Signal False Positives

The `not_equals` operator can be dangerous if missing signals are not handled.

Bad behavior:

```python
None != "Synced"  # True
```

Correct fix:

```python
if actual_value is None:
    return False
```

This prevents false matches for rules like:

```yaml
id: argocd-sync-drift
conditions:
  - signal: argocd_sync_status
    operator: not_equals
    value: Synced
```

---

## 29. Phase 22 Success Criteria

Phase 22 is complete when:

```text
Multiple YAML rules exist
MultiRuleEngine loads all rules from app/rules/
MultiRuleEngine evaluates every rule
Best matching rule is selected by priority
Rule evaluation endpoint works
Failed rule conditions are visible
Existing single-rule endpoints still work
Tests pass
```

---

## 30. Commands Summary

### Run focused tests

```bash
pytest app/tests/test_multi_rule_engine.py -q
pytest app/tests/test_rule_evaluations_endpoint.py -q
```

### Run full test suite

```bash
pytest
```

### Check rule files

```bash
ls -1 app/rules
```

### Check route registration

```bash
python - <<'PY'
from app.main import app

for route in app.routes:
    if "/api/v1/incidents" in route.path:
        print(route.path, route.methods)
PY
```

### Check live rule evaluations

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/evaluations | jq
```

---

## 31. Recommended Commit

```bash
git status

git add app/rules \
        app/engine/rule_loader.py \
        app/engine/decision_engine.py \
        app/api/v1/incidents.py \
        app/tests/test_multi_rule_engine.py \
        app/tests/test_rule_evaluations_endpoint.py

git commit -m "feat: add multi-rule scenario evaluation engine"
git push
```

---

## 32. Result

After Phase 22, the platform is no longer limited to a single frontend availability rule.

It can now:

```text
load multiple YAML rules
evaluate every known rule
explain why rules matched or failed
rank matched rules by priority
return the best decision
support future workload and platform incident scenarios
```

This phase is the foundation for:

```text
Phase 23 — Workload Incident Scenarios
Phase 24 — Platform Incident Scenarios
Phase 25 — Generic Evaluate / Persist / Resolve API
```
