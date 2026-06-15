# Phase 27A — SLO Registry + Error Budget API

## Project

**SRE Decision Intelligence Platform**

## Phase status

**Planned / implementation-ready**

Phase 27A introduces the reliability foundation of the platform:

```text
SLI → SLO → Error Budget → Budget Status → Decision Priority
```

This phase adds an SLO registry, SLI/SLO models, an error budget calculator, and API endpoints for listing and evaluating SLOs.

It remains under:

```text
/api/v1
```

No `/api/v2` is introduced because this phase is additive.

---

## 1. Why Phase 27A exists

Until this phase, the platform can already:

```text
collect live signals
normalize workload/platform signals
evaluate multiple rules
match incident scenarios
persist incidents
resolve incidents
show timeline/history
```

However, an enterprise SRE platform should not only answer:

```text
What failed?
```

It should also answer:

```text
How much reliability budget are we burning?
Is this incident violating an SLO?
Should this incident be warning, critical, or urgent?
Is the service still within its error budget?
```

That is why Phase 27A adds SLI/SLO/error-budget modeling.

---

## 2. Core SRE concepts

### 2.1 SLI — Service Level Indicator

An **SLI** is the measurement.

It answers:

```text
What are we measuring?
```

Examples:

```text
frontend availability
frontend p95 latency
transaction success rate
API error rate
backend dependency success rate
```

In this project, example raw or normalized signals include:

```text
probe_success
frontend_availability_5m
frontend_latency_p95_ms
transaction_error_rate
transaction_success_rate
```

An SLI should be measurable, user-relevant, and connected to business impact.

---

### 2.2 SLO — Service Level Objective

An **SLO** is the reliability target.

It answers:

```text
How reliable should the service be?
```

Example:

```text
Frontend availability should be at least 99.5% over 30 days.
```

In decimal form:

```text
target = 0.995
```

An SLO should be realistic, measurable, and tied to user experience.

---

### 2.3 Error Budget

The **error budget** is the amount of unreliability allowed by the SLO.

Formula:

```text
error_budget = 1 - SLO target
```

Example:

```text
SLO target = 99.5%
Allowed failure = 0.5%
Error budget = 0.005
```

If the current availability is lower than the target, the service consumes error budget.

---

### 2.4 Error Budget Burn

Error budget burn tells us how much of the allowed failure has already been used.

Formula:

```text
current_failure_ratio = 1 - current_value
allowed_failure_ratio = 1 - slo_target
budget_consumed_ratio = current_failure_ratio / allowed_failure_ratio
budget_remaining_ratio = 1 - budget_consumed_ratio
```

Example:

```text
SLO target: 99.5%
Allowed failure: 0.5%

Current availability: 99.0%
Current failure: 1.0%

Budget consumed = 1.0% / 0.5% = 2.0
```

That means:

```text
200% of the error budget is consumed
error budget is exhausted
```

---

## 3. Enterprise mental model

A mature SRE decision platform should prioritize based on:

```text
user impact
+
SLO affected
+
error budget consumed
+
burn rate / budget status
+
root cause confidence
+
safe action risk
```

Without SLOs and error budgets, a decision engine may only say:

```text
probe_success is 0
```

With SLOs and error budgets, it can say:

```text
frontend availability is below target, 200% of the 30-day error budget is consumed,
and the most likely root cause is service-routing.
```

That is a much stronger enterprise SRE story.

---

## 4. Phase 27A scope

Phase 27A includes:

```text
SLI model
SLO model
Error budget evaluation model
SLO registry
Error budget calculator
SLO API router
SLO API schemas
Tests
Manual validation commands
```

Phase 27A does **not** yet attach SLO evaluation directly into every `DecisionResponse`.

That comes later in:

```text
Phase 27B — Attach SLO/Error Budget Evaluation to DecisionResponse
```

---

## 5. Target file structure

Phase 27A adds:

```text
app/slo/
├── __init__.py
├── models.py
├── frontend_slos.py
├── registry.py
└── calculator.py

app/schemas/
└── slo.py

app/api/v1/
└── slo.py

app/tests/
├── test_slo_models.py
├── test_error_budget_calculator.py
└── test_slo_api.py
```

---

## 6. SLO API endpoints

Phase 27A introduces:

| Endpoint | Method | Purpose |
|---|---:|---|
| `/api/v1/slo` | GET | List all registered SLOs |
| `/api/v1/slo/{slo_id}` | GET | Return one SLO definition |
| `/api/v1/slo/evaluate` | POST | Evaluate error budget status for an SLO |

Important route-order rule:

```text
POST /api/v1/slo/evaluate
```

must be declared before:

```text
GET /api/v1/slo/{slo_id}
```

Otherwise FastAPI may interpret `evaluate` as a `slo_id`.

Correct order:

```text
GET  /api/v1/slo
POST /api/v1/slo/evaluate
GET  /api/v1/slo/{slo_id}
```

---

## 7. SLI/SLO model design

File:

```text
app/slo/models.py
```

### 7.1 SliType

Purpose:

```text
Classifies the type of reliability measurement.
```

Recommended values:

| Type | Meaning |
|---|---|
| `availability` | User path or service availability |
| `latency` | Request latency or response-time objective |
| `error_rate` | Percentage of failed requests |
| `success_rate` | Percentage of successful operations |
| `saturation` | Capacity/resource pressure |

---

### 7.2 SloWindow

Purpose:

```text
Defines the time window over which the SLO is evaluated.
```

Recommended values:

| Window | Use case |
|---|---|
| `5m` | Fast-burn incident detection |
| `1h` | Short operational window |
| `1d` | Daily reliability view |
| `7d` | Weekly reliability view |
| `30d` | Standard monthly SLO window |

---

### 7.3 SloStatus

Purpose:

```text
Classifies the current error-budget state.
```

Recommended values:

| Status | Meaning |
|---|---|
| `healthy` | Budget consumption is below warning threshold |
| `warning` | Budget consumption crossed warning threshold |
| `burning_fast` | Budget consumption crossed critical threshold |
| `exhausted` | Error budget is fully consumed or exceeded |

---

### 7.4 SliDefinition

Purpose:

```text
Describes the measurement behind an SLO.
```

Recommended fields:

| Field | Meaning |
|---|---|
| `id` | Stable SLI ID |
| `name` | Human-readable SLI name |
| `description` | What the SLI measures |
| `service` | Service being measured |
| `sli_type` | Availability, latency, success rate, etc. |
| `source` | Telemetry source such as Prometheus |
| `signal_name` | Normalized signal connected to the SLI |
| `unit` | Ratio, milliseconds, count, etc. |
| `good_event_description` | What counts as good |
| `bad_event_description` | What counts as bad |

---

### 7.5 SloDefinition

Purpose:

```text
Defines a reliability objective for one SLI.
```

Recommended fields:

| Field | Meaning |
|---|---|
| `id` | Stable SLO ID |
| `name` | Human-readable SLO name |
| `description` | Reliability promise |
| `sli` | Attached SLI definition |
| `target` | Target ratio, e.g. `0.995` |
| `window` | Evaluation window |
| `warning_threshold` | Budget consumed ratio for warning |
| `critical_threshold` | Budget consumed ratio for burning fast |
| `tags` | Search/filter metadata |

---

### 7.6 ErrorBudgetEvaluation

Purpose:

```text
Represents the result of evaluating current SLI value against an SLO.
```

Recommended fields:

| Field | Meaning |
|---|---|
| `slo_id` | SLO evaluated |
| `slo_name` | SLO name |
| `service` | Service attached to SLO |
| `sli_id` | SLI evaluated |
| `sli_name` | SLI name |
| `target` | SLO target |
| `current_value` | Current SLI value |
| `window` | Evaluation window |
| `allowed_failure_ratio` | Failure allowed by SLO |
| `current_failure_ratio` | Current observed failure |
| `budget_consumed_ratio` | How much budget is consumed |
| `budget_remaining_ratio` | How much budget remains |
| `status` | healthy/warning/burning_fast/exhausted |
| `summary` | Human-readable explanation |

---

## 8. Enterprise SLO definitions

File:

```text
app/slo/frontend_slos.py
```

Recommended SLOs for this platform:

| SLO ID | Target | Window | Purpose |
|---|---:|---|---|
| `frontend-availability-30d` | `0.995` | `30d` | Monthly frontend availability reliability |
| `frontend-availability-5m` | `0.995` | `5m` | Fast-burn frontend availability detection |
| `frontend-latency-30d` | `0.990` | `30d` | Frontend user experience target |
| `transaction-success-30d` | `0.990` | `30d` | Business transaction success reliability |

---

## 9. Important note about latency SLOs

Latency SLOs are often misunderstood.

A raw latency value like:

```text
frontend_latency_p95_ms = 1500
```

is **not directly an error-budget ratio**.

For error budget calculation, latency should be transformed into a ratio-based SLI such as:

```text
percentage_of_requests_under_1000ms
```

Example:

```text
99.2% of requests completed below 1000ms
```

That ratio can be evaluated against a latency SLO target.

For Phase 27A:

```text
availability and success-rate SLOs are fully supported by the calculator
latency SLOs are defined conceptually
raw millisecond latency should not be used directly as current_value
```

This is the correct enterprise interpretation.

---

## 10. SLO registry

File:

```text
app/slo/registry.py
```

Purpose:

```text
Provide a central registry of all SLO definitions known to the platform.
```

Expected behavior:

```text
list_slos()
get_slo(slo_id)
require_slo(slo_id)
```

Example:

```python
slo = slo_registry.require_slo("frontend-availability-30d")
```

The registry allows the API, decision engine, and future SLO enrichment logic to reference stable SLO definitions.

---

## 11. Error budget calculator

File:

```text
app/slo/calculator.py
```

Purpose:

```text
Evaluate current SLI value against an SLO target.
```

Core formula:

```python
allowed_failure_ratio = 1.0 - slo.target
current_failure_ratio = max(0.0, 1.0 - current_value)
budget_consumed_ratio = current_failure_ratio / allowed_failure_ratio
budget_remaining_ratio = max(0.0, 1.0 - budget_consumed_ratio)
```

### 11.1 Status classification

Recommended classification:

| Condition | Status |
|---|---|
| `budget_consumed_ratio >= 1.0` | `exhausted` |
| `budget_consumed_ratio >= critical_threshold` | `burning_fast` |
| `budget_consumed_ratio >= warning_threshold` | `warning` |
| otherwise | `healthy` |

### 11.2 Example

For SLO target:

```text
99.5%
```

Allowed failure:

```text
0.5%
```

If current value is:

```text
99.25%
```

Current failure:

```text
0.75%
```

Budget consumed:

```text
0.75 / 0.5 = 1.5
```

Status:

```text
exhausted
```

---

## 12. API schemas

File:

```text
app/schemas/slo.py
```

### 12.1 SloResponse

Purpose:

```text
Return an SLO definition through the API.
```

Can inherit from:

```python
SloDefinition
```

---

### 12.2 ErrorBudgetEvaluateRequest

Purpose:

```text
Request error budget evaluation for an SLO.
```

Example:

```json
{
  "slo_id": "frontend-availability-30d",
  "current_value": 0.990
}
```

`current_value` must be a ratio between:

```text
0.0 and 1.0
```

---

### 12.3 ErrorBudgetEvaluateResponse

Purpose:

```text
Return the error budget evaluation result.
```

Includes:

```text
target
current_value
allowed_failure_ratio
current_failure_ratio
budget_consumed_ratio
budget_remaining_ratio
status
summary
```

---

## 13. API router

File:

```text
app/api/v1/slo.py
```

Expected router:

```text
prefix="/api/v1/slo"
tags=["slo"]
```

Expected endpoints:

```text
GET  /api/v1/slo
POST /api/v1/slo/evaluate
GET  /api/v1/slo/{slo_id}
```

---

## 14. Register router

File:

```text
app/main.py
```

Add:

```python
from app.api.v1.slo import router as slo_router
```

Then include:

```python
app.include_router(slo_router)
```

---

## 15. Tests

Phase 27A should include three test files:

```text
app/tests/test_slo_models.py
app/tests/test_error_budget_calculator.py
app/tests/test_slo_api.py
```

### 15.1 Model and registry tests

File:

```text
app/tests/test_slo_models.py
```

Purpose:

```text
Validate SLO registry and SLO definitions.
```

Recommended tests:

```text
test_slo_registry_lists_defined_slos
test_frontend_availability_slo_has_expected_target
```

Expected checks:

```text
frontend-availability-30d exists
frontend-availability-5m exists
frontend-latency-30d exists
transaction-success-30d exists
frontend availability target is 0.995
frontend availability window is 30d
```

---

### 15.2 Error budget calculator tests

File:

```text
app/tests/test_error_budget_calculator.py
```

Purpose:

```text
Validate budget math and status classification.
```

Recommended tests:

| Test | Purpose |
|---|---|
| healthy budget | Current value comfortably above target |
| warning budget | Budget crosses warning threshold |
| burning fast budget | Budget crosses critical threshold |
| exhausted budget | Budget consumed ratio >= 1.0 |
| formula correctness | Validate exact budget math |

Important example:

```text
target = 0.995
current_value = 0.9925

allowed_failure = 0.005
current_failure = 0.0075
consumed = 1.5
status = exhausted
```

---

### 15.3 SLO API tests

File:

```text
app/tests/test_slo_api.py
```

Purpose:

```text
Validate /api/v1/slo endpoints.
```

Recommended tests:

```text
test_list_slos_endpoint_returns_defined_slos
test_get_slo_endpoint_returns_detail
test_get_unknown_slo_returns_404
test_evaluate_error_budget_endpoint_returns_budget_status
test_evaluate_unknown_slo_returns_404
```

---

## 16. Validation commands

### 16.1 Run model tests

```bash
pytest app/tests/test_slo_models.py -q
```

Expected:

```text
2 passed
```

---

### 16.2 Run calculator tests

```bash
pytest app/tests/test_error_budget_calculator.py -q
```

Expected:

```text
5 passed
```

---

### 16.3 Run API tests

```bash
pytest app/tests/test_slo_api.py -q
```

Expected:

```text
5 passed
```

---

### 16.4 Validate router registration

```bash
python - <<'PY'
from app.main import app

for route in app.routes:
    if "/api/v1/slo" in route.path:
        print(route.path, route.methods)
PY
```

Expected:

```text
/api/v1/slo {'GET'}
/api/v1/slo/evaluate {'POST'}
/api/v1/slo/{slo_id} {'GET'}
```

---

### 16.5 Run full regression

```bash
pytest
```

Expected:

```text
all tests passed
```

---

## 17. Manual runtime validation

Start API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 17.1 List SLOs

```bash
curl http://localhost:8000/api/v1/slo | jq
```

Expected:

```text
list of SLO definitions
```

---

### 17.2 Get one SLO

```bash
curl http://localhost:8000/api/v1/slo/frontend-availability-30d | jq
```

Expected fields:

```text
id
name
description
sli
target
window
warning_threshold
critical_threshold
tags
```

---

### 17.3 Evaluate healthy budget

```bash
curl -X POST http://localhost:8000/api/v1/slo/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "slo_id": "frontend-availability-30d",
    "current_value": 0.999
  }' | jq
```

Expected:

```json
{
  "status": "healthy"
}
```

---

### 17.4 Evaluate burning-fast budget

```bash
curl -X POST http://localhost:8000/api/v1/slo/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "slo_id": "frontend-availability-30d",
    "current_value": 0.9954
  }' | jq
```

Expected:

```json
{
  "status": "burning_fast"
}
```

Explanation:

```text
target = 0.995
allowed failure = 0.005
current value = 0.9954
current failure = 0.0046
budget consumed = 0.0046 / 0.005 = 0.92
critical threshold = 0.90
status = burning_fast
```

---

### 17.5 Evaluate exhausted budget

```bash
curl -X POST http://localhost:8000/api/v1/slo/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "slo_id": "frontend-availability-30d",
    "current_value": 0.990
  }' | jq
```

Expected:

```json
{
  "status": "exhausted"
}
```

Explanation:

```text
target = 0.995
allowed failure = 0.005
current value = 0.990
current failure = 0.010
budget consumed = 0.010 / 0.005 = 2.0
status = exhausted
```

---

## 18. Example error budget table

For a 99.5% SLO:

| Current value | Failure ratio | Budget consumed | Status |
|---:|---:|---:|---|
| 99.9% | 0.1% | 20% | healthy |
| 99.7% | 0.3% | 60% | warning |
| 99.54% | 0.46% | 92% | burning_fast |
| 99.25% | 0.75% | 150% | exhausted |
| 99.0% | 1.0% | 200% | exhausted |

Formula:

```text
allowed failure = 100% - 99.5% = 0.5%
budget consumed = current failure / allowed failure
```

---

## 19. Common issues

### 19.1 `/api/v1/slo/evaluate` returns SLO not found

Cause:

```text
/evaluate is being caught by /{slo_id}
```

Fix:

```text
Declare @router.post("/evaluate") before @router.get("/{slo_id}")
```

---

### 19.2 Latency SLO confusion

Do not pass raw milliseconds to `current_value`.

Wrong:

```json
{
  "slo_id": "frontend-latency-30d",
  "current_value": 1500
}
```

Correct concept:

```json
{
  "slo_id": "frontend-latency-30d",
  "current_value": 0.992
}
```

Where `0.992` means:

```text
99.2% of requests were under the latency threshold
```

---

### 19.3 Budget status seems too strict

For a 99.5% SLO, the allowed failure is only 0.5%.

That means even small drops in availability can consume the budget quickly.

Example:

```text
99.0% availability sounds high,
but for a 99.5% target it is already twice the allowed failure.
```

---

## 20. Success criteria

Phase 27A is complete when:

```text
SLI model exists
SLO model exists
Error budget evaluation model exists
SLO registry exists
Frontend availability 30d SLO exists
Frontend availability 5m fast-burn SLO exists
Transaction success SLO exists
Error budget calculator works
/api/v1/slo lists SLOs
/api/v1/slo/{slo_id} returns one SLO
/api/v1/slo/evaluate returns budget status
SLO tests pass
Full pytest passes
```

---

## 21. What you should be able to explain

After Phase 27A, you should be able to clearly explain:

```text
An SLI is the measurement.
An SLO is the reliability target.
The error budget is the allowed failure.
Budget consumed shows how much of the allowed failure has already been used.
A service can look mostly healthy but still exhaust its error budget if the SLO is strict.
SRE decisions should consider user impact and error-budget burn, not just raw alerts.
```

Example explanation:

```text
For a 99.5% frontend availability SLO, the allowed failure is 0.5%.
If current availability drops to 99.0%, the observed failure is 1.0%.
That means the service consumed 200% of its error budget.
So even though 99.0% sounds high, for this SLO the budget is exhausted.
```

---

## 22. How Phase 27A connects to the wider platform

Phase 27A is currently separate from incident decisions.

It provides:

```text
SLO definitions
error budget evaluation
budget status API
```

The next step is to connect it to incident decisions.

---

## 23. Next phase

Recommended next phase:

```text
Phase 27B — Attach SLO/Error Budget Evaluation to DecisionResponse
```

Goal:

```text
When an incident decision is produced, include SLO impact and error-budget status inside the response.
```

Future decision response could include:

```json
{
  "slo_evaluation": {
    "slo_id": "frontend-availability-30d",
    "target": 0.995,
    "current_value": 0.982,
    "budget_consumed_ratio": 3.6,
    "status": "exhausted"
  }
}
```

This is where the platform becomes more strongly business-aligned.

---

## 24. Git commit

After implementation and validation:

```bash
git status
```

Then:

```bash
git add app/slo \
        app/schemas/slo.py \
        app/api/v1/slo.py \
        app/main.py \
        app/tests/test_slo_models.py \
        app/tests/test_error_budget_calculator.py \
        app/tests/test_slo_api.py
```

Commit:

```bash
git commit -m "feat: add SLI SLO error budget model"
git push
```

---

## 25. Summary

Phase 27A adds the enterprise SRE reliability layer.

Before:

```text
The platform could detect incidents and recommend safe actions.
```

After:

```text
The platform can also evaluate whether reliability objectives are being met,
how much error budget is consumed, and whether the current service state is healthy,
warning, burning fast, or exhausted.
```

This gives the project a much stronger SRE foundation and prepares it for executive-level and enterprise-grade incident decisioning.
