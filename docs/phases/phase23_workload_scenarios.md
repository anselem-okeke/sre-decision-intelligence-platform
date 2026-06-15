# Phase 23 — Workload Incident Scenarios

## Purpose

Phase 23 expands the SRE Decision Intelligence Platform from a single frontend availability / Kubernetes routing scenario into a broader set of **workload-side incident scenarios**.

Before this phase, the platform mainly understood this pattern:

```text
Synthetic probe failed
+
Frontend Service endpoints missing
+
Frontend pod still ready
=
Likely root cause: Service selector mismatch
```

That is a valuable correlation scenario, but it only explains one failure mode. Real incidents are not always caused by Kubernetes routing problems. Sometimes Kubernetes is healthy, but the workload itself is degraded.

Phase 23 introduces rules and scenario definitions for application-level and service-path problems such as:

```text
frontend high 5xx rate
frontend high latency
transaction error spike
backend timeout spike
ledger/database error spike
```

The goal is to make the platform reason about **user-facing application impact**, not only Kubernetes infrastructure state.

---

## Position in the roadmap

```text
Phase 19 → API response models and error contracts
Phase 20 → Generic normalized signal model
Phase 21 → Scenario registry
Phase 22 → Multi-rule / multi-scenario rule engine
Phase 23 → Workload incident scenarios
Phase 24 → Platform incident scenarios
Phase 25 → Generic evaluate / persist / resolve API
Phase 26 → Service layer refactor and incident API cleanup
```

Phase 23 depends on Phase 22 because workload scenarios are evaluated by the multi-rule engine.

---

## Main outcome

After Phase 23, the rule engine can evaluate more workload-oriented conditions:

| Scenario | Rule ID | Category |
|---|---|---|
| Frontend high 5xx rate | `frontend-high-5xx-rate` | `application-errors` |
| Frontend high latency | `frontend-high-latency` | `latency-degradation` |
| Transaction error spike | `transaction-error-spike` | `transaction-failure` |
| Backend timeout spike | `backend-timeout-spike` | `dependency-timeout` |
| Ledger/database error spike | `ledger-database-error-spike` | `database-errors` |

These scenarios are still evaluated under `/api/v1`.

No `/api/v2` is needed because this phase is additive and does not break existing API contracts.

---

## Design principle

Phase 23 should **not** create one endpoint per scenario.

Avoid this pattern:

```text
/api/v1/incidents/frontend-5xx/live
/api/v1/incidents/frontend-latency/live
/api/v1/incidents/transaction-errors/live
/api/v1/incidents/backend-timeouts/live
```

That design becomes hard to maintain.

Instead, scenarios should be treated as **data** evaluated by the generic rule engine.

The better long-term API direction is:

```text
POST /api/v1/incidents/evaluate
POST /api/v1/incidents/evaluate/live
POST /api/v1/incidents/persist
GET  /api/v1/scenarios
```

At this phase, the old frontend-specific evaluation endpoint can still be used for debugging:

```text
GET /api/v1/incidents/frontend-availability/live/evaluations
```

---

## Signal model used in Phase 23

Phase 23 introduces workload-specific signal keys.

These are added to the sample signal dictionary and later included in normalized signal output.

```python
"frontend_5xx_rate": 0.0,
"frontend_latency_p95_ms": 120,
"transaction_error_rate": 0.0,
"backend_timeout_count": 0,
"ledger_database_error_count": 0,
```

### Meaning of each signal

| Signal | Source | Domain | Meaning |
|---|---|---|---|
| `frontend_5xx_rate` | Prometheus | Workload | Ratio of frontend requests returning HTTP 5xx |
| `frontend_latency_p95_ms` | Prometheus | Workload | Frontend p95 latency in milliseconds |
| `transaction_error_rate` | Prometheus | Workload | Ratio of failed transaction operations |
| `backend_timeout_count` | OpenSearch/logs | Workload | Count of timeout-related backend log events |
| `ledger_database_error_count` | OpenSearch/logs | Workload | Count of ledger/database-related error log events |

---

## Files introduced or modified

Typical Phase 23 changes affect these files:

```text
app/rules/frontend_high_5xx_rate.yaml
app/rules/frontend_high_latency.yaml
app/rules/transaction_error_spike.yaml
app/rules/backend_timeout_spike.yaml
app/rules/ledger_database_error_spike.yaml

app/engine/sample_signals.py
app/signals/frontend_availability.py
app/scenarios/frontend_availability.py
app/scenarios/registry.py

app/tests/test_workload_scenarios.py
```

---

## Rule file: frontend high 5xx rate

Create:

```text
app/rules/frontend_high_5xx_rate.yaml
```

Example content:

```yaml
id: frontend-high-5xx-rate
scenario_id: frontend-availability-breach
name: Frontend High 5xx Rate
description: Frontend user path is degraded because the frontend service is returning elevated 5xx errors.
priority: 80
severity: critical
domain: workload

conditions:
  - signal: probe_success
    operator: equals
    value: 0

  - signal: frontend_5xx_rate
    operator: greater_than
    value: 0.05

  - signal: frontend_endpoints
    operator: not_equals
    value: none

  - signal: frontend_pod_ready
    operator: equals
    value: true

decision:
  impact_summary: Bank of Anthos frontend is returning elevated 5xx errors
  user_impact: Users can reach the frontend path, but requests are failing at the application layer.
  slo_affected: frontend-availability
  likely_root_cause: Frontend application is returning elevated server errors
  confidence: medium
  category: application-errors
  safe_action: Inspect frontend application logs, recent deployments, and upstream dependency errors before restarting
  safe_action_command: kubectl logs -n fintech-workload deploy/frontend --tail=100
  risk: medium
```

### Interpretation

This rule says:

```text
If users are affected,
AND frontend is returning elevated 5xx,
AND Kubernetes routing is healthy,
AND frontend pod is ready,
THEN likely root cause is application-level server errors.
```

---

## Rule file: frontend high latency

Create:

```text
app/rules/frontend_high_latency.yaml
```

Example content:

```yaml
id: frontend-high-latency
scenario_id: frontend-latency-degradation
name: Frontend High Latency
description: Frontend user path is degraded because p95 latency is above the acceptable threshold.
priority: 70
severity: warning
domain: workload

conditions:
  - signal: frontend_latency_p95_ms
    operator: greater_than
    value: 1000

  - signal: frontend_endpoints
    operator: not_equals
    value: none

  - signal: frontend_pod_ready
    operator: equals
    value: true

decision:
  impact_summary: Bank of Anthos frontend latency is elevated
  user_impact: Users can access the frontend, but response time is degraded.
  slo_affected: frontend-latency
  likely_root_cause: Frontend request path is slow while Kubernetes routing appears healthy
  confidence: medium
  category: latency-degradation
  safe_action: Inspect frontend latency metrics, upstream service latency, and recent rollout changes
  safe_action_command: kubectl logs -n fintech-workload deploy/frontend --tail=100
  risk: low
```

---

## Rule file: transaction error spike

Create:

```text
app/rules/transaction_error_spike.yaml
```

Example content:

```yaml
id: transaction-error-spike
scenario_id: transaction-failure-breach
name: Transaction Error Spike
description: User transactions are failing even though the frontend service path is reachable.
priority: 75
severity: critical
domain: workload

conditions:
  - signal: transaction_error_rate
    operator: greater_than
    value: 0.03

  - signal: frontend_endpoints
    operator: not_equals
    value: none

  - signal: frontend_pod_ready
    operator: equals
    value: true

decision:
  impact_summary: Bank of Anthos transaction errors are elevated
  user_impact: Users may be able to access the frontend but cannot reliably complete banking transactions.
  slo_affected: transaction-success-rate
  likely_root_cause: Transaction path is failing at the application or dependency layer
  confidence: medium
  category: transaction-failure
  safe_action: Inspect transaction service logs and dependency health before restarting workloads
  safe_action_command: kubectl logs -n fintech-workload deploy/transactionhistory --tail=100
  risk: medium
```

---

## Rule file: backend timeout spike

Create:

```text
app/rules/backend_timeout_spike.yaml
```

Example content:

```yaml
id: backend-timeout-spike
scenario_id: backend-dependency-degradation
name: Backend Timeout Spike
description: Frontend or transaction path is degraded because backend dependency timeouts are elevated.
priority: 72
severity: warning
domain: workload

conditions:
  - signal: backend_timeout_count
    operator: greater_than
    value: 20

  - signal: frontend_endpoints
    operator: not_equals
    value: none

  - signal: frontend_pod_ready
    operator: equals
    value: true

decision:
  impact_summary: Backend dependency timeouts are elevated
  user_impact: Users may experience failed or slow banking operations caused by backend dependency delays.
  slo_affected: backend-dependency-health
  likely_root_cause: Backend dependency timeout spike
  confidence: medium
  category: dependency-timeout
  safe_action: Inspect backend service logs, service-to-service latency, and dependency availability
  safe_action_command: kubectl get pods -n fintech-workload
  risk: low
```

---

## Rule file: ledger/database error spike

Create:

```text
app/rules/ledger_database_error_spike.yaml
```

Example content:

```yaml
id: ledger-database-error-spike
scenario_id: ledger-database-degradation
name: Ledger Database Error Spike
description: Banking ledger operations are degraded because database-related errors are elevated.
priority: 78
severity: critical
domain: workload

conditions:
  - signal: ledger_database_error_count
    operator: greater_than
    value: 10

  - signal: frontend_endpoints
    operator: not_equals
    value: none

  - signal: frontend_pod_ready
    operator: equals
    value: true

decision:
  impact_summary: Ledger/database errors are elevated
  user_impact: Users may experience failed balance, ledger, or transaction operations.
  slo_affected: ledger-operation-success
  likely_root_cause: Ledger or database error spike
  confidence: medium
  category: database-errors
  safe_action: Inspect ledger service logs, database connectivity, and recent schema/config changes
  safe_action_command: kubectl logs -n fintech-workload deploy/ledgerwriter --tail=100
  risk: medium
```

---

## Updating sample signals

Open:

```text
app/engine/sample_signals.py
```

Add workload keys to `get_frontend_availability_sample_signals()`:

```python
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

        # Workload signals for Phase 23
        "frontend_5xx_rate": 0.0,
        "frontend_latency_p95_ms": 120,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
    }
```

The default values are healthy values so that existing selector-mismatch tests continue to behave predictably.

---

## Updating normalized signal output

Open:

```text
app/signals/frontend_availability.py
```

Add these workload signals to `normalize_frontend_availability_signals()`:

```python
make_signal(
    name="frontend_5xx_rate",
    domain=SignalDomain.WORKLOAD,
    source=SignalSource.PROMETHEUS,
    service=service,
    namespace=namespace,
    value=raw_signals.get("frontend_5xx_rate"),
    unit="ratio",
    meaning="Frontend 5xx error rate",
    raw={"query_result": raw_signals.get("frontend_5xx_rate")},
),
make_signal(
    name="frontend_latency_p95_ms",
    domain=SignalDomain.WORKLOAD,
    source=SignalSource.PROMETHEUS,
    service=service,
    namespace=namespace,
    value=raw_signals.get("frontend_latency_p95_ms"),
    unit="milliseconds",
    meaning="Frontend p95 latency in milliseconds",
    raw={"query_result": raw_signals.get("frontend_latency_p95_ms")},
),
make_signal(
    name="transaction_error_rate",
    domain=SignalDomain.WORKLOAD,
    source=SignalSource.PROMETHEUS,
    service="transaction",
    namespace=namespace,
    value=raw_signals.get("transaction_error_rate"),
    unit="ratio",
    meaning="Transaction error rate",
    raw={"query_result": raw_signals.get("transaction_error_rate")},
),
make_signal(
    name="backend_timeout_count",
    domain=SignalDomain.WORKLOAD,
    source=SignalSource.OPENSEARCH,
    service=None,
    namespace=namespace,
    value=raw_signals.get("backend_timeout_count"),
    unit="count",
    meaning="Backend timeout count from application logs",
    raw={"opensearch_value": raw_signals.get("backend_timeout_count")},
),
make_signal(
    name="ledger_database_error_count",
    domain=SignalDomain.WORKLOAD,
    source=SignalSource.OPENSEARCH,
    service="ledger",
    namespace=namespace,
    value=raw_signals.get("ledger_database_error_count"),
    unit="count",
    meaning="Ledger/database error count from application logs",
    raw={"opensearch_value": raw_signals.get("ledger_database_error_count")},
),
```

---

## Updating the scenario registry

Open:

```text
app/scenarios/frontend_availability.py
```

Add workload scenario definitions for:

```text
FRONTEND_HIGH_5XX_RATE
FRONTEND_HIGH_LATENCY
TRANSACTION_ERROR_SPIKE
BACKEND_TIMEOUT_SPIKE
LEDGER_DATABASE_ERROR_SPIKE
```

Each scenario should define:

```text
id
name
description
domain
status
required_signals
optional_signals
root_cause_category
safe_action_summary
risk_level
tags
```

Example:

```python
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
```

Then update:

```text
app/scenarios/registry.py
```

Import the workload scenarios:

```python
from app.scenarios.frontend_availability import (
    BACKEND_TIMEOUT_SPIKE,
    FRONTEND_HIGH_5XX_RATE,
    FRONTEND_HIGH_LATENCY,
    FRONTEND_SERVICE_SELECTOR_MISMATCH,
    LEDGER_DATABASE_ERROR_SPIKE,
    TRANSACTION_ERROR_SPIKE,
)
```

Register them:

```python
scenario_registry = ScenarioRegistry(
    scenarios=[
        FRONTEND_SERVICE_SELECTOR_MISMATCH,
        FRONTEND_HIGH_5XX_RATE,
        FRONTEND_HIGH_LATENCY,
        TRANSACTION_ERROR_SPIKE,
        BACKEND_TIMEOUT_SPIKE,
        LEDGER_DATABASE_ERROR_SPIKE,
    ]
)
```

---

## Test file

Create:

```text
app/tests/test_workload_scenarios.py
```

The tests should validate that:

```text
frontend high 5xx rule matches
frontend high latency rule matches
transaction error spike rule matches
backend timeout spike rule matches
ledger/database error spike rule matches
workload scenarios are registered
```

Example test pattern:

```python
from pathlib import Path

from app.engine.decision_engine import MultiRuleEngine
from app.scenarios.registry import scenario_registry

RULES_DIR = Path("app/rules")


def test_frontend_high_5xx_rule_matches():
    signals = {
        "probe_success": 0,
        "frontend_availability_5m": 0.8,
        "alert_state": "pending",
        "frontend_endpoints": "10.244.8.229:8080",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "ERROR 500 response",
        "frontend_error_log_count": 40,
        "frontend_5xx_rate": 0.12,
        "frontend_latency_p95_ms": 200,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
    }

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "application-errors"
```

---

## Validation commands

Run the Phase 23 test file:

```bash
pytest app/tests/test_workload_scenarios.py -q
```

Expected:

```text
6 passed
```

Run multi-rule regression tests:

```bash
pytest app/tests/test_multi_rule_engine.py -q
```

Run platform tests if Phase 24 already exists:

```bash
pytest app/tests/test_platform_scenarios.py -q
```

Run the full suite:

```bash
pytest
```

Expected final result in the current project state:

```text
62 passed
```

---

## Manual API validation

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

List scenarios:

```bash
curl http://localhost:8000/api/v1/scenarios | jq '.[].id'
```

Expected workload scenario IDs:

```text
"frontend-high-5xx-rate"
"frontend-high-latency"
"transaction-error-spike"
"backend-timeout-spike"
"ledger-database-error-spike"
```

Check rule evaluations:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/evaluations | jq
```

On a healthy live cluster, most workload scenarios should show:

```json
"matched": false
```

Some workload signal values may appear as:

```json
"actual": null
```

This is acceptable at Phase 23 if live collectors do not yet collect real 5xx, latency, transaction, timeout, or database metrics.

---

## Important implementation note

At Phase 23, many workload rules are validated through synthetic test signals.

Live values may remain `null` until later collector expansion phases.

That is expected because Phase 23 is primarily about:

```text
scenario definition
rule evaluation
registry integration
test-driven workload decision logic
```

It is not yet about full production-grade Prometheus/OpenSearch query coverage for every workload signal.

---

## Priority model

The multi-rule engine chooses the highest-priority matching rule.

Example priority ordering:

```text
frontend-service-selector-mismatch → 100
frontend-high-5xx-rate             → 80
ledger-database-error-spike        → 78
transaction-error-spike            → 75
backend-timeout-spike              → 72
frontend-high-latency              → 70
```

The selector mismatch rule remains higher priority because if Service endpoints are missing, Kubernetes routing is the stronger root cause than application symptoms.

This prevents less-specific workload rules from overriding a clearer platform/correlation root cause.

---

## Common issues

### 1. Workload test returns the wrong category

Example:

```text
Expected: latency-degradation
Actual: gitops-drift
```

This usually means a rule is matching because a missing signal is treated as valid.

The rule engine should reject missing signals.

`condition_matches()` should include:

```python
if actual_value is None:
    return False
```

This prevents rules like `argocd_sync_status != Synced` from matching when `argocd_sync_status` is missing.

---

### 2. Live evaluation shows actual null

Example:

```json
{
  "signal": "frontend_5xx_rate",
  "operator": "greater_than",
  "expected": 0.05,
  "actual": null
}
```

This means the rule exists, but the live collector does not yet collect that signal.

That is acceptable in Phase 23.

Later phases can expand the Prometheus and OpenSearch collectors.

---

### 3. Rule does not appear in evaluations

Check that the YAML file exists:

```bash
ls app/rules
```

Check that `MultiRuleEngine` loads all YAML files from:

```text
app/rules/*.yaml
```

Check the rule has valid YAML syntax.

---

### 4. Scenario does not appear in `/api/v1/scenarios`

Check:

```text
app/scenarios/frontend_availability.py
app/scenarios/registry.py
```

The scenario must be defined and added to `scenario_registry`.

---

## Phase 23 success criteria

Phase 23 is complete when:

```text
New workload rule YAML files exist
Workload scenarios are registered
MultiRuleEngine can match workload scenarios in tests
Existing selector mismatch rule still works
Scenario API lists workload scenarios
Full pytest passes
```

---

## Commit command

```bash
git status

git add app/rules \
        app/engine/sample_signals.py \
        app/signals/frontend_availability.py \
        app/scenarios/frontend_availability.py \
        app/scenarios/registry.py \
        app/tests/test_workload_scenarios.py

git commit -m "feat: add workload incident scenarios"
git push
```

---

## Final result

After Phase 23, the platform can reason about workload-side degradation patterns:

```text
frontend server errors
frontend latency degradation
transaction failures
backend dependency timeouts
ledger/database errors
```

This turns the platform from a single Kubernetes routing detector into a broader workload-aware incident decision system.

The next phase is:

```text
Phase 24 — Platform Incident Scenarios
```
