# Phase 27B — Attach SLO / Error Budget Evaluation to DecisionResponse

## Project

**SRE Decision Intelligence Platform**

## Phase status

**Implementation-ready**

Phase 27B connects the SLO and error budget model from Phase 27A directly into incident decisions.

Phase 27A created:

```text
SLI model
SLO model
Error budget calculator
SLO registry
SLO API
```

Phase 27B makes those reliability concepts visible inside the actual incident decision response.

The result is that every matching incident can now explain not only:

```text
What failed?
Why did it fail?
What is the safe action?
```

but also:

```text
Which SLO is affected?
What is the target?
What is the current reliability value?
How much error budget is consumed?
Is the budget healthy, warning, burning fast, or exhausted?
```

---

## 1. Why Phase 27B exists

Before Phase 27B, the platform could produce decisions like this:

```json
{
  "incident_id": "frontend-availability-breach",
  "likely_root_cause": {
    "category": "service-routing",
    "summary": "Frontend Service selector did not match frontend pod labels"
  },
  "safe_action": {
    "summary": "Restore the frontend Service selector so it matches frontend pod labels"
  }
}
```

That is useful, but it is still mostly technical.

An enterprise SRE platform should also explain reliability impact:

```json
{
  "slo_evaluation": {
    "slo_id": "frontend-availability-30d",
    "target": 0.995,
    "current_value": 0.6,
    "budget_consumed_ratio": 80.0,
    "status": "exhausted"
  }
}
```

This turns a technical incident into an SRE decision:

```text
The frontend user path is failing, the frontend availability SLO is affected,
and the service has consumed 80x its allowed error budget.
```

---

## 2. Enterprise mental model

Phase 27B introduces this chain:

```text
Signals
  ↓
Rule Engine
  ↓
DecisionResponse
  ↓
SLO Mapping
  ↓
Error Budget Evaluation
  ↓
SRE-Aware Decision
```

Before:

```text
probe_success = 0
frontend_endpoints = none
frontend_pod_ready = true
→ service selector mismatch
```

After:

```text
probe_success = 0
frontend_endpoints = none
frontend_pod_ready = true
frontend_availability_5m = 0.6
→ service selector mismatch
→ frontend availability SLO affected
→ 99.5% target
→ 60% current value
→ error budget exhausted
```

---

## 3. Scope of Phase 27B

Phase 27B includes:

```text
Extend DecisionResponse with optional slo_evaluation
Create SLO decision mapping layer
Attach error budget evaluation in the rule engine
Expose slo_evaluation through generic evaluate API
Add tests for SLO mapping
Add tests for DecisionResponse enrichment
Update existing generic API tests
Manual validation commands
```

Phase 27B does **not** add database persistence for SLO evaluation yet.

Database schema remains unchanged.

That means:

```text
slo_evaluation appears in API responses
but is not stored in PostgreSQL yet
```

Persistence can be added later as a separate phase.

---

## 4. Files changed or added

Phase 27B touches:

```text
app/schemas/decision.py
app/slo/decision_mapping.py
app/engine/decision_engine.py
app/tests/test_slo_decision_mapping.py
app/tests/test_decision_response_slo_evaluation.py
app/tests/test_generic_incident_api.py
```

Existing Phase 27A files used:

```text
app/slo/models.py
app/slo/registry.py
app/slo/calculator.py
app/slo/frontend_slos.py
```

---

## 5. Target response shape

After Phase 27B, a matching decision response should include:

```json
{
  "incident_id": "frontend-availability-breach",
  "service": "frontend",
  "namespace": "fintech-workload",
  "severity": "warning",
  "status": "detected",
  "impact": {
    "slo_affected": "frontend-availability"
  },
  "likely_root_cause": {
    "category": "service-routing"
  },
  "safe_action": {
    "summary": "Restore the frontend Service selector so it matches frontend pod labels"
  },
  "slo_evaluation": {
    "slo_id": "frontend-availability-30d",
    "slo_name": "Frontend Availability 30d SLO",
    "service": "frontend",
    "sli_id": "frontend-availability",
    "sli_name": "Frontend Availability",
    "target": 0.995,
    "current_value": 0.6,
    "window": "30d",
    "allowed_failure_ratio": 0.005,
    "current_failure_ratio": 0.4,
    "budget_consumed_ratio": 80.0,
    "budget_remaining_ratio": 0.0,
    "status": "exhausted",
    "summary": "Frontend Availability 30d SLO: current value is 60.0% against target 99.5%."
  }
}
```

---

## 6. Design decision: optional `slo_evaluation`

The new field should be optional:

```python
slo_evaluation: ErrorBudgetEvaluation | None = None
```

Why optional?

Because not every decision will have an SLO mapping yet.

Examples where it may be `null`:

```text
The rule has no slo_affected field
The affected SLO name is unknown
The required SLI signal is missing
The SLI value cannot be converted to a ratio
The scenario is platform-only and not yet mapped to a user-facing SLO
```

This is important because the rule engine must remain safe:

```text
No SLO mapping should not break incident detection.
```

---

## 7. Step 1 — Extend DecisionResponse

File:

```text
app/schemas/decision.py
```

Add import:

```python
from app.slo.models import ErrorBudgetEvaluation
```

Add field to `DecisionResponse`:

```python
slo_evaluation: ErrorBudgetEvaluation | None = None
```

Conceptual model:

```python
from typing import Any

from pydantic import BaseModel

from app.schemas.impact import Impact
from app.schemas.root_cause import RootCause
from app.schemas.safe_action import SafeAction
from app.schemas.signal import SignalGroup
from app.slo.models import ErrorBudgetEvaluation


class DecisionResponse(BaseModel):
    incident_id: str
    service: str
    namespace: str
    severity: str
    status: str
    impact: Impact
    signals: SignalGroup
    evidence: list[str]
    likely_root_cause: RootCause
    safe_action: SafeAction
    metadata: dict[str, Any]
    slo_evaluation: ErrorBudgetEvaluation | None = None
```

Your exact field order can be different.

The important addition is:

```python
slo_evaluation: ErrorBudgetEvaluation | None = None
```

---

## 8. Step 2 — Create SLO decision mapping layer

File:

```text
app/slo/decision_mapping.py
```

Purpose:

```text
Map decision impact fields to SLO definitions and SLI signal values.
```

The mapper answers two questions:

```text
Which SLO should this decision evaluate?
Which signal contains the current SLI value?
```

Create file:

```bash
touch app/slo/decision_mapping.py
```

Add:

```python
from typing import Any

from app.slo.calculator import calculate_error_budget
from app.slo.models import ErrorBudgetEvaluation
from app.slo.registry import slo_registry


SLO_BY_AFFECTED_SLO_NAME = {
    "frontend-availability": "frontend-availability-30d",
    "frontend-latency": "frontend-latency-30d",
    "transaction-success-rate": "transaction-success-30d",
    "transaction-success": "transaction-success-30d",
}


SIGNAL_BY_SLO_ID = {
    "frontend-availability-30d": "frontend_availability_5m",
    "frontend-availability-5m": "frontend_availability_5m",
    "frontend-latency-30d": "frontend_latency_good_event_ratio",
    "transaction-success-30d": "transaction_success_rate",
}


def evaluate_slo_for_decision(
    slo_affected: str | None,
    signals: dict[str, Any],
) -> ErrorBudgetEvaluation | None:
    if not slo_affected:
        return None

    slo_id = SLO_BY_AFFECTED_SLO_NAME.get(slo_affected)

    if slo_id is None:
        return None

    slo = slo_registry.get_slo(slo_id)

    if slo is None:
        return None

    signal_name = SIGNAL_BY_SLO_ID.get(slo_id)

    if signal_name is None:
        return None

    current_value = signals.get(signal_name)

    if current_value is None:
        return None

    try:
        current_value_float = float(current_value)
    except (TypeError, ValueError):
        return None

    return calculate_error_budget(
        slo=slo,
        current_value=current_value_float,
    )
```

---

## 9. Why use a mapping layer?

Do not hardcode SLO logic directly inside the rule engine.

Bad design:

```text
RuleEngine directly knows every SLO ID and signal mapping.
```

Better design:

```text
RuleEngine builds decision
SLO decision mapper enriches decision
SLO registry owns SLO definitions
Calculator owns budget math
```

This keeps responsibilities clean:

| Component | Responsibility |
|---|---|
| Rule engine | Match rules and build decisions |
| Scenario/rule YAML | Define incident logic |
| SLO registry | Define reliability objectives |
| SLO mapper | Connect decisions to SLOs |
| Error budget calculator | Compute budget status |

---

## 10. Mapping strategy

Phase 27B uses this mapping:

| `slo_affected` from rule decision | SLO ID |
|---|---|
| `frontend-availability` | `frontend-availability-30d` |
| `frontend-latency` | `frontend-latency-30d` |
| `transaction-success-rate` | `transaction-success-30d` |
| `transaction-success` | `transaction-success-30d` |

And this signal mapping:

| SLO ID | Signal used as current value |
|---|---|
| `frontend-availability-30d` | `frontend_availability_5m` |
| `frontend-availability-5m` | `frontend_availability_5m` |
| `frontend-latency-30d` | `frontend_latency_good_event_ratio` |
| `transaction-success-30d` | `transaction_success_rate` |

Important:

```text
frontend_availability_5m is currently used as the measured current value.
```

Later, you can improve this by supporting multiple windows:

```text
frontend_availability_5m
frontend_availability_1h
frontend_availability_30d
```

For Phase 27B, the current approach is acceptable because it proves the SLO-enriched decision path.

---

## 11. Important latency note

Do **not** use raw milliseconds as `current_value` for error budget calculation.

Wrong:

```json
{
  "frontend_latency_p95_ms": 1500
}
```

Correct ratio-based input:

```json
{
  "frontend_latency_good_event_ratio": 0.992
}
```

Meaning:

```text
99.2% of frontend requests are below the latency threshold.
```

This is why the mapping uses:

```text
frontend_latency_good_event_ratio
```

not:

```text
frontend_latency_p95_ms
```

---

## 12. Step 3 — Attach SLO evaluation in the rule engine

File:

```text
app/engine/decision_engine.py
```

Add import:

```python
from app.slo.decision_mapping import evaluate_slo_for_decision
```

Inside `build_decision_response()`, after:

```python
decision = rule["decision"]
```

add:

```python
slo_evaluation = evaluate_slo_for_decision(
    slo_affected=decision.get("slo_affected"),
    signals=signals,
)
```

Then add to the `DecisionResponse(...)` constructor:

```python
slo_evaluation=slo_evaluation,
```

Conceptual implementation:

```python
def build_decision_response(
    rule: dict[str, Any],
    signals: dict[str, Any],
) -> DecisionResponse:
    decision = rule["decision"]

    slo_evaluation = evaluate_slo_for_decision(
        slo_affected=decision.get("slo_affected"),
        signals=signals,
    )

    return DecisionResponse(
        incident_id=rule.get("scenario_id") or rule.get("scenario"),
        service="frontend",
        namespace="fintech-workload",
        severity=rule["severity"],
        status="detected",
        impact=...,
        signals=...,
        evidence=...,
        likely_root_cause=...,
        safe_action=...,
        metadata=...,
        slo_evaluation=slo_evaluation,
    )
```

---

## 13. Step 4 — Do not change the database yet

For Phase 27B:

```text
No Alembic migration
No new table
No new database column
```

The `slo_evaluation` field is response-only.

Reason:

```text
This phase should prove SLO enrichment safely without database schema complexity.
```

Later options:

| Option | Description |
|---|---|
| JSONB in `decisions` table | Simple persistence of SLO evaluation snapshot |
| New `slo_evaluations` table | More normalized and queryable |
| Link incidents to SLO IDs | Good for reporting and dashboards |

Recommended future phase:

```text
Phase 27C — Persist SLO Evaluation Snapshots
```

---

## 14. Step 5 — Add SLO mapping tests

File:

```text
app/tests/test_slo_decision_mapping.py
```

Create:

```python
from app.slo.decision_mapping import evaluate_slo_for_decision
from app.slo.models import SloStatus


def test_slo_mapping_attaches_frontend_availability_budget_evaluation():
    signals = {
        "frontend_availability_5m": 0.990,
    }

    result = evaluate_slo_for_decision(
        slo_affected="frontend-availability",
        signals=signals,
    )

    assert result is not None
    assert result.slo_id == "frontend-availability-30d"
    assert result.target == 0.995
    assert result.current_value == 0.990
    assert result.status == SloStatus.EXHAUSTED


def test_slo_mapping_returns_none_for_unknown_slo_name():
    signals = {
        "frontend_availability_5m": 0.990,
    }

    result = evaluate_slo_for_decision(
        slo_affected="unknown-slo",
        signals=signals,
    )

    assert result is None


def test_slo_mapping_returns_none_when_signal_missing():
    result = evaluate_slo_for_decision(
        slo_affected="frontend-availability",
        signals={},
    )

    assert result is None
```

Run:

```bash
pytest app/tests/test_slo_decision_mapping.py -q
```

Expected:

```text
3 passed
```

---

## 15. Step 6 — Add DecisionResponse SLO enrichment test

File:

```text
app/tests/test_decision_response_slo_evaluation.py
```

Create:

```python
from pathlib import Path

from app.engine.decision_engine import MultiRuleEngine

RULES_DIR = Path("app/rules")


def test_decision_response_includes_slo_evaluation_for_frontend_availability():
    signals = {
        "probe_success": 0,
        "frontend_availability_5m": 0.6,
        "alert_state": "pending",
        "frontend_endpoints": "none",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 13,
        "frontend_5xx_rate": 0.0,
        "frontend_latency_p95_ms": 120,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
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

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.slo_evaluation is not None
    assert decision.slo_evaluation.slo_id == "frontend-availability-30d"
    assert decision.slo_evaluation.target == 0.995
    assert decision.slo_evaluation.current_value == 0.6
    assert decision.slo_evaluation.status == "exhausted"
    assert decision.slo_evaluation.budget_consumed_ratio > 1.0
```

Run:

```bash
pytest app/tests/test_decision_response_slo_evaluation.py -q
```

Expected:

```text
1 passed
```

---

## 16. Step 7 — Update generic incident API test

File:

```text
app/tests/test_generic_incident_api.py
```

In the existing selector mismatch test, add:

```python
assert body["decision"]["slo_evaluation"] is not None
assert body["decision"]["slo_evaluation"]["slo_id"] == "frontend-availability-30d"
assert body["decision"]["slo_evaluation"]["status"] == "exhausted"
```

Example:

```python
def test_generic_evaluate_matches_frontend_selector_mismatch():
    response = client.post(
        "/api/v1/incidents/evaluate",
        json={
            "signals": {
                "probe_success": 0,
                "frontend_availability_5m": 0.6,
                "alert_state": "pending",
                "frontend_endpoints": "none",
                "frontend_pod_ready": True,
                "frontend_pod_status": "1/1 Running",
                "frontend_logs": "mostly INFO",
                "frontend_error_log_count": 13,
                "frontend_5xx_rate": 0.0,
                "frontend_latency_p95_ms": 120,
                "transaction_error_rate": 0.0,
                "backend_timeout_count": 0,
                "ledger_database_error_count": 0,
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
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["matched"] is True
    assert body["decision"]["incident_id"] == "frontend-availability-breach"
    assert body["decision"]["likely_root_cause"]["category"] == "service-routing"
    assert body["decision"]["slo_evaluation"] is not None
    assert body["decision"]["slo_evaluation"]["slo_id"] == "frontend-availability-30d"
    assert body["decision"]["slo_evaluation"]["status"] == "exhausted"
```

Run:

```bash
pytest app/tests/test_generic_incident_api.py -q
```

Expected:

```text
all passed
```

---

## 17. Manual API validation

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run generic evaluate:

```bash
curl -X POST http://localhost:8000/api/v1/incidents/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "signals": {
      "probe_success": 0,
      "frontend_availability_5m": 0.6,
      "alert_state": "pending",
      "frontend_endpoints": "none",
      "frontend_pod_ready": true,
      "frontend_pod_status": "1/1 Running",
      "frontend_logs": "mostly INFO",
      "frontend_error_log_count": 13,
      "frontend_5xx_rate": 0.0,
      "frontend_latency_p95_ms": 120,
      "transaction_error_rate": 0.0,
      "backend_timeout_count": 0,
      "ledger_database_error_count": 0,
      "pod_crashloop": false,
      "image_pull_backoff": false,
      "failed_scheduling": false,
      "node_not_ready": false,
      "oom_killed": false,
      "pvc_mount_failure": false,
      "cilium_drop_count": 0,
      "longhorn_volume_degraded": false,
      "argocd_sync_status": "Synced"
    }
  }' | jq '.decision.slo_evaluation'
```

Expected:

```json
{
  "slo_id": "frontend-availability-30d",
  "slo_name": "Frontend Availability 30d SLO",
  "service": "frontend",
  "sli_id": "frontend-availability",
  "sli_name": "Frontend Availability",
  "target": 0.995,
  "current_value": 0.6,
  "window": "30d",
  "allowed_failure_ratio": 0.005,
  "current_failure_ratio": 0.4,
  "budget_consumed_ratio": 80.0,
  "budget_remaining_ratio": 0.0,
  "status": "exhausted"
}
```

---

## 18. Error budget explanation for the sample incident

Given:

```text
SLO target = 99.5%
Current frontend availability = 60%
```

Convert to ratios:

```text
target = 0.995
current_value = 0.6
```

Allowed failure:

```text
1 - 0.995 = 0.005
```

Current failure:

```text
1 - 0.6 = 0.4
```

Budget consumed:

```text
0.4 / 0.005 = 80
```

Interpretation:

```text
The service consumed 80x the allowed error budget.
The error budget is exhausted.
```

This is why the incident is not just a metric failure.

It is an SLO-impacting event.

---

## 19. Validation commands

### 19.1 Run SLO mapping tests

```bash
pytest app/tests/test_slo_decision_mapping.py -q
```

Expected:

```text
3 passed
```

### 19.2 Run DecisionResponse SLO test

```bash
pytest app/tests/test_decision_response_slo_evaluation.py -q
```

Expected:

```text
1 passed
```

### 19.3 Run generic API tests

```bash
pytest app/tests/test_generic_incident_api.py -q
```

Expected:

```text
all passed
```

### 19.4 Run SLO regression tests

```bash
pytest app/tests/test_slo_models.py -q
pytest app/tests/test_error_budget_calculator.py -q
pytest app/tests/test_slo_api.py -q
```

Expected:

```text
all passed
```

### 19.5 Run full regression

```bash
pytest
```

Expected:

```text
all tests passed
```

---

## 20. Common issues and fixes

### 20.1 `slo_evaluation` is always null

Possible causes:

```text
rule decision does not contain slo_affected
slo_affected value does not exist in SLO_BY_AFFECTED_SLO_NAME
mapped signal is missing from input signals
current signal value is not numeric
DecisionResponse constructor did not pass slo_evaluation
```

Check the rule YAML:

```yaml
decision:
  slo_affected: frontend-availability
```

Check input signals:

```json
{
  "frontend_availability_5m": 0.6
}
```

Check `build_decision_response()`:

```python
slo_evaluation=slo_evaluation
```

---

### 20.2 Import error from `app.slo.models`

Possible cause:

```text
Phase 27A files are missing or not committed
```

Validate:

```bash
ls app/slo
```

Expected:

```text
__init__.py
models.py
frontend_slos.py
registry.py
calculator.py
decision_mapping.py
```

---

### 20.3 API response validation error

Possible cause:

```text
DecisionResponse schema does not include slo_evaluation
```

Fix:

```python
slo_evaluation: ErrorBudgetEvaluation | None = None
```

---

### 20.4 Latency SLO evaluation does not attach

Possible cause:

```text
frontend_latency_good_event_ratio is missing
```

Do not use raw latency milliseconds as the budget ratio.

Use:

```json
{
  "frontend_latency_good_event_ratio": 0.992
}
```

---

### 20.5 Existing tests fail because response changed

If tests compare the exact full decision JSON, update them to allow the new optional field.

Recommended assertion style:

```python
assert body["decision"]["slo_evaluation"] is not None
```

Do not overfit tests to every summary string unless necessary.

---

## 21. Success criteria

Phase 27B is complete when:

```text
DecisionResponse has optional slo_evaluation field
SLO decision mapping exists
Rule engine calls evaluate_slo_for_decision()
Generic evaluate API returns slo_evaluation for frontend availability incidents
Unknown SLO mappings safely return null
Missing SLO signals safely return null
No database schema change is required
SLO mapping tests pass
DecisionResponse SLO tests pass
Generic incident API tests pass
Full pytest passes
```

---

## 22. What you can explain after Phase 27B

After Phase 27B, you can explain:

```text
The platform does not only detect incidents.
It attaches SRE reliability context to decisions.
For a frontend availability incident, it maps the decision to the frontend availability SLO.
It then calculates how much error budget is consumed based on the current SLI value.
This allows the decision response to explain business/reliability impact, not only technical symptoms.
```

Example interview explanation:

```text
In Phase 27B, I connected the rule engine to the SLO registry.
When a rule matches, the platform checks which SLO is affected, reads the current SLI value from the signal payload, calculates the error budget state, and attaches that result to the DecisionResponse.
For example, if frontend availability drops to 60% against a 99.5% SLO, the system calculates that the service consumed 80 times its allowed error budget and marks the SLO state as exhausted.
```

---

## 23. Business value

This phase is important because it shifts the platform from:

```text
Alert → Root Cause → Action
```

to:

```text
Alert → Root Cause → SLO Impact → Error Budget Status → Action
```

That is more aligned with how enterprise SRE teams prioritize incidents.

A 5xx spike, latency increase, or endpoint failure is not equally important in every context.

It becomes urgent when it:

```text
affects user-facing SLOs
burns error budget fast
threatens reliability commitments
impacts business-critical flows
```

---

## 24. Recommended Git commit

After validation:

```bash
git status
```

Then:

```bash
git add app/schemas/decision.py \
        app/slo/decision_mapping.py \
        app/engine/decision_engine.py \
        app/tests/test_slo_decision_mapping.py \
        app/tests/test_decision_response_slo_evaluation.py \
        app/tests/test_generic_incident_api.py
```

Commit:

```bash
git commit -m "feat: attach SLO error budget evaluation to decisions"
git push
```

---

## 25. Recommended next phase

After Phase 27B, the next strong phase is:

```text
Phase 28 — Docker Runtime Hardening
```

Optional before Docker:

```text
Phase 27C — Persist SLO Evaluation Snapshots
```

Recommended order:

```text
Phase 27B — Attach SLO/Error Budget Evaluation to DecisionResponse
Phase 28 — Docker Runtime Hardening
Phase 29 — Kubernetes Deployment
Phase 30 — GitOps Deployment
```

If the goal is fast portfolio progress, move to Docker after Phase 27B.

If the goal is deeper SLO analytics, add Phase 27C before Docker.

---

## 26. Summary

Phase 27B makes the decision response SRE-aware.

Before Phase 27B:

```text
The platform could identify the likely root cause and safe action.
```

After Phase 27B:

```text
The platform can also explain SLO impact and error budget state.
```

That is a major architecture improvement because it connects technical incident evidence to reliability commitments.
