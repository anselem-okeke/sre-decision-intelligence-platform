# Phase 15 Technical Concept — Rule Engine v1

## SRE Decision Intelligence Platform

This document explains Phase 15 of the SRE Decision Intelligence Platform in detail.

Phase 15 is important because this is where the project moves from a static API response into the first real product logic.

The goal is to make the platform explain **why** an incident happened based on evidence.

---

## 1. What Phase 15 Adds

Before Phase 15, the API returned a hardcoded incident response.

That was useful for proving the API contract, but it was not yet a decision engine.

Phase 15 changes the architecture from this:

```text
API endpoint
   ↓
Hardcoded JSON response
```

To this:

```text
API endpoint
   ↓
Sample normalized signals
   ↓
YAML rule
   ↓
Rule Engine
   ↓
DecisionResponse schema
   ↓
API response
```

This means the API response is no longer just manually written inside the endpoint.

It is now produced by a small rule engine.

---

## 2. Why This Matters

The business value of the platform is not simply to show metrics or logs.

Prometheus already shows metrics.  
OpenSearch already shows logs.  
Kubernetes already shows runtime state.  
Grafana already shows dashboards.

The missing layer is:

```text
What do these signals mean together?
```

Phase 15 introduces that layer.

The platform starts to answer:

```text
The frontend is unavailable.
The pod is still healthy.
The Service has no endpoints.
Therefore this is likely not a pod crash.
The likely cause is a Service selector mismatch.
The safe action is to restore the Service selector.
```

That is the first real Decision Intelligence behavior.

---

## 3. The Incident Scenario

The first supported scenario is:

```text
Bank of Anthos frontend availability breach
```

The validated incident looked like this:

```text
Frontend pod: 1/1 Running
Frontend Service endpoints: <none>
Prometheus probe_success: 0
SLO availability: 0.7
Alert state: pending
```

The key point:

```text
The pod was healthy, but the user-facing service path was broken.
```

This is a realistic Kubernetes failure mode.

A team looking only at pod status may think the workload is fine.

But users cannot reach the frontend because the Service has no endpoints.

---

## 4. Product Logic in Simple Words

The first rule says:

```text
IF the frontend probe failed
AND the frontend Service has no endpoints
AND the frontend pod is still ready
THEN the likely root cause is a Service selector mismatch
```

This is the core logic.

It separates three different facts:

| Signal | Meaning |
|---|---|
| `probe_success = 0` | User-facing path failed |
| `frontend_endpoints = none` | Service has no backend pod |
| `frontend_pod_ready = true` | Pod itself did not crash |

Together, these signals create a strong explanation:

```text
The application pod is alive.
The Service cannot route to it.
The routing relationship is broken.
```

That points to a Service selector or endpoint problem.

---

## 5. Why the Rule Is Valid

A Kubernetes Service sends traffic to Pods through label selectors.

Simplified:

```text
Service selector
    ↓ matches labels
Pod labels
    ↓ creates endpoint
Service endpoint
```

When the Service selector matches the Pod labels, Kubernetes creates endpoints.

Example healthy state:

```text
Service selector:
  app=frontend

Pod labels:
  app=frontend

Endpoint:
  10.244.8.229:8080
```

Broken state:

```text
Service selector:
  app=frontend
  slo-test=broken

Pod labels:
  app=frontend

Endpoint:
  <none>
```

The extra selector label prevents the Service from matching the Pod.

So the Pod remains running, but the Service has no backend endpoint.

That is why this condition is meaningful:

```text
probe_success = 0
frontend_endpoints = none
frontend_pod_ready = true
```

It strongly suggests a Service routing mismatch.

---

## 6. Phase 15 File Structure

Phase 15 introduced these files:

```text
app/
├── engine/
│   ├── __init__.py
│   ├── decision_engine.py
│   ├── rule_loader.py
│   └── sample_signals.py
│
├── rules/
│   └── frontend_availability_breach.yaml
│
├── api/
│   └── v1/
│       └── incidents.py
│
└── tests/
    └── test_rule_engine.py
```

Each file has a clear responsibility.

---

## 7. Responsibility of Each File

### `app/rules/frontend_availability_breach.yaml`

Stores the decision rule.

It describes:

- rule identity
- scenario name
- severity
- matching conditions
- decision output

This keeps decision logic out of the API endpoint.

### `app/engine/sample_signals.py`

Provides normalized example signals for the first scenario.

In Phase 15, we are not yet querying Prometheus, Kubernetes, or OpenSearch live.

Instead, we use sample signals based on validated Phase 10 and Phase 11 evidence.

### `app/engine/rule_loader.py`

Loads the YAML rule from disk.

It checks:

- whether the file exists
- whether the YAML content is valid
- whether the rule is a dictionary/object

### `app/engine/decision_engine.py`

Contains the main rule evaluation logic.

It answers:

```text
Do the provided signals match the rule conditions?
```

If yes:

```text
Build a DecisionResponse.
```

If no:

```text
Raise an error because no matching rule was found.
```

### `app/api/v1/incidents.py`

The endpoint now calls the rule engine.

The API no longer manually builds the entire decision response.

Instead, it does this:

```text
load sample signals
load rule engine
evaluate signals
return decision
```

### `app/tests/test_rule_engine.py`

Proves the rule works.

It tests both positive and negative cases.

Positive case:

```text
probe_success = 0
frontend_endpoints = none
frontend_pod_ready = true
```

Expected result:

```text
Service selector mismatch detected
```

Negative cases:

```text
probe_success = 1
frontend_endpoints exists
frontend_pod_ready = false
```

Expected result:

```text
Rule should not match
```

This prevents false positives.

---

## 8. YAML Rule Explained

The rule file starts with identity metadata:

```yaml
id: frontend-service-selector-mismatch
name: Frontend Service Selector Mismatch
scenario: frontend-availability-breach
severity: warning
```

| Field | Meaning |
|---|---|
| `id` | Unique rule identifier |
| `name` | Human-readable rule name |
| `scenario` | Incident scenario |
| `severity` | Incident severity |

---

## 9. Rule Conditions Explained

The conditions section defines what must be true before the rule matches.

```yaml
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
```

This means:

```text
probe_success must equal 0
frontend_endpoints must equal none
frontend_pod_ready must equal true
```

The current engine only supports the `equals` operator.

That is intentional.

The first version should stay simple and easy to reason about.

---

## 10. Decision Section Explained

The decision section defines what the platform should return when the rule matches.

```yaml
decision:
  impact_summary: Bank of Anthos frontend endpoint unavailable
  user_impact: Users cannot reliably access the banking frontend service path.
  slo_affected: frontend-availability
  likely_root_cause: Frontend Service selector did not match frontend pod labels
  confidence: high
  category: service-routing
  safe_action: Restore the frontend Service selector so it matches frontend pod labels
  risk: low
```

This transforms low-level signals into a human-readable incident explanation.

Instead of returning only:

```text
probe_success = 0
```

The platform returns:

```text
Impact: Frontend endpoint unavailable
Cause: Service selector mismatch
Action: Restore Service selector
```

That is the product value.

---

## 11. Sample Signals Explained

The normalized sample signals represent the incident evidence.

Example:

```python
signals = {
    "probe_success": 0,
    "frontend_availability_5m": 0.7,
    "alert_state": "pending",
    "frontend_endpoints": "none",
    "frontend_pod_ready": True,
    "frontend_pod_status": "1/1 Running",
    "frontend_logs": "mostly INFO",
}
```

Each signal has a purpose.

| Signal | Source later | Meaning |
|---|---|---|
| `probe_success` | Prometheus | Whether frontend user path is reachable |
| `frontend_availability_5m` | Prometheus | Short-window SLO availability |
| `alert_state` | Prometheus | Alert condition state |
| `frontend_endpoints` | Kubernetes API | Whether Service has backend endpoints |
| `frontend_pod_ready` | Kubernetes API | Whether Pod is ready |
| `frontend_pod_status` | Kubernetes API | Human-readable pod status |
| `frontend_logs` | OpenSearch | Log context |

In Phase 16, these sample signals will be replaced by live collectors.

---

## 12. Rule Loader Logic Explained

The rule loader performs a small but important job.

Concept:

```text
Take the path to a YAML file
Open the file
Parse YAML
Return a Python dictionary
```

Important snippet:

```python
with path.open("r", encoding="utf-8") as file:
    rule = yaml.safe_load(file)
```

This converts YAML into a Python dictionary.

For example, YAML like this:

```yaml
severity: warning
```

becomes:

```python
{"severity": "warning"}
```

The decision engine can then use it.

---

## 13. Decision Engine Logic Explained

The decision engine has two main responsibilities:

```text
1. Check if all rule conditions match
2. Build the final DecisionResponse
```

### Step 1: Load the rule

```python
self.rule = load_rule(rule_path)
```

This loads the YAML rule into memory.

### Step 2: Evaluate signals

```python
if not self._conditions_match(signals):
    raise ValueError("No matching rule found for provided signals")
```

This means:

```text
If the incident signals do not satisfy the rule,
do not produce a decision.
```

This is important because the platform should not invent a root cause when evidence is missing.

### Step 3: Match conditions

Conceptual logic:

```python
for condition in rule.conditions:
    signal_name = condition["signal"]
    expected_value = condition["value"]
    actual_value = signals.get(signal_name)

    if actual_value != expected_value:
        return False

return True
```

Every condition must match.

This is an `AND` relationship.

The rule matches only when all conditions are true.

---

## 14. Understanding the AND Logic

The rule is not:

```text
probe_success = 0
OR endpoints = none
OR pod_ready = true
```

It is:

```text
probe_success = 0
AND endpoints = none
AND pod_ready = true
```

This matters because each signal alone is not enough.

### Case 1: Probe failed only

```text
probe_success = 0
```

This tells us the frontend is unavailable.

But it does not tell us why.

Possible causes:

- pod crash
- Service endpoint problem
- network policy
- application error
- DNS issue
- node problem

So this signal alone is not enough.

### Case 2: Endpoints are empty only

```text
frontend_endpoints = none
```

This tells us the Service has no backend.

But maybe the pod is also down.

So this signal alone is not enough.

### Case 3: Pod is ready only

```text
frontend_pod_ready = true
```

This tells us the pod is healthy.

But it does not prove users can access the application.

So this signal alone is not enough.

### Combined case

```text
probe_success = 0
AND frontend_endpoints = none
AND frontend_pod_ready = true
```

Now the explanation is stronger:

```text
The user path failed.
The Service has no endpoints.
The Pod itself is healthy.
```

This points to Service routing, not pod failure.

---

## 15. Why False Positive Tests Matter

A decision engine must avoid wrong conclusions.

For example, if:

```text
probe_success = 1
```

then the frontend is reachable.

The rule should not match.

If:

```text
frontend_endpoints = 10.244.8.229:8080
```

then the Service has an endpoint.

The rule should not claim endpoints are missing.

If:

```text
frontend_pod_ready = false
```

then the pod may be unhealthy.

The rule should not claim this is only a Service selector mismatch.

That is why Phase 15 includes tests for non-matching cases.

---

## 16. Test Logic Explained

The first test verifies the happy path.

```text
Given incident signals
When the rule engine evaluates them
Then it returns a DecisionResponse
And the root cause is service-routing
```

Expected result:

```text
category = service-routing
confidence = high
safe_action.risk = low
```

This proves the rule detects the intended scenario.

---

## 17. Negative Test: Probe Successful

Input change:

```python
signals["probe_success"] = 1
```

Meaning:

```text
The frontend probe is successful.
```

Expected result:

```text
No matching rule found
```

Why?

Because the rule only applies when the user path is failing.

---

## 18. Negative Test: Endpoints Exist

Input change:

```python
signals["frontend_endpoints"] = "10.244.8.229:8080"
```

Meaning:

```text
The frontend Service has a backend endpoint.
```

Expected result:

```text
No matching rule found
```

Why?

Because the rule is specifically for missing endpoints.

---

## 19. Negative Test: Pod Not Ready

Input change:

```python
signals["frontend_pod_ready"] = False
```

Meaning:

```text
The frontend pod is not ready.
```

Expected result:

```text
No matching rule found
```

Why?

Because if the pod is not ready, the incident may be a pod crash, rollout issue, or application startup issue.

It should not be classified as a clean Service selector mismatch.

---

## 20. API Flow After Phase 15

The incident endpoint now works like this:

```text
GET /api/v1/incidents/frontend-availability
        ↓
get_frontend_availability_sample_signals()
        ↓
RuleEngine(frontend_availability_breach.yaml)
        ↓
engine.evaluate(signals)
        ↓
DecisionResponse
        ↓
JSON response
```

This is the first version of product logic.

---

## 21. Why the API Still Returns the Same JSON

The API output may look similar to Phase 14.

That is expected.

The difference is not the shape of the output.

The difference is how the output is produced.

Phase 14:

```text
Response manually created inside API endpoint
```

Phase 15:

```text
Response produced through rule evaluation
```

This matters because later we can add more rules without rewriting the API response manually.

---

## 22. Current Limitation

Phase 15 still uses sample signals.

It does not yet call:

- Prometheus
- Kubernetes API
- OpenSearch
- Argo CD

That is intentional.

The purpose of Phase 15 is to build and test the reasoning layer first.

Live data collection comes in Phase 16.

---

## 23. Why We Do Not Add Live Collectors Yet

If we add collectors too early, debugging becomes harder.

Problems could come from:

- Prometheus connection
- Kubernetes RBAC
- OpenSearch query
- network access
- bad signal normalization
- broken rule logic

By separating phases, we know Phase 15 tests only the rule engine.

This is clean engineering.

```text
Phase 15 = Does the reasoning logic work?
Phase 16 = Can we collect the real signals?
```

---

## 24. Runbook: Validate Phase 15

Run from repo root:

```bash
cd /mnt/data/sre-decision-intelligence-platform
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Expected result:

```text
all tests passed
```

Then run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Test the incident endpoint:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability | jq
```

Expected key fields:

```json
{
  "incident_id": "frontend-availability-breach",
  "service": "frontend",
  "namespace": "fintech-workload",
  "severity": "warning",
  "status": "detected"
}
```

Expected root cause:

```json
{
  "summary": "Frontend Service selector did not match frontend pod labels",
  "confidence": "high",
  "category": "service-routing"
}
```

Expected safe action:

```json
{
  "summary": "Restore the frontend Service selector so it matches frontend pod labels",
  "risk": "low"
}
```

---

## 25. Runbook: Manually Test Rule Matching

Open a Python shell:

```bash
python
```

Run:

```python
from pathlib import Path

from app.engine.decision_engine import RuleEngine
from app.engine.sample_signals import get_frontend_availability_sample_signals

signals = get_frontend_availability_sample_signals()
engine = RuleEngine(Path("app/rules/frontend_availability_breach.yaml"))

decision = engine.evaluate(signals)

print(decision.likely_root_cause.summary)
print(decision.safe_action.summary)
```

Expected output:

```text
Frontend Service selector did not match frontend pod labels
Restore the frontend Service selector so it matches frontend pod labels
```

---

## 26. Runbook: Manually Test a Non-Matching Case

In Python:

```python
signals = get_frontend_availability_sample_signals()
signals["probe_success"] = 1

engine.evaluate(signals)
```

Expected result:

```text
ValueError: No matching rule found for provided signals
```

This proves the engine does not produce the root cause when the probe is healthy.

---

## 27. Runbook: Inspect the Rule File

View the rule:

```bash
cat app/rules/frontend_availability_breach.yaml
```

Check:

```text
conditions
decision
```

The conditions explain when the rule matches.

The decision explains what the platform returns when it matches.

---

## 28. Runbook: Inspect API Schema

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/docs
```

Check:

```text
GET /api/v1/incidents/frontend-availability
```

You should see the structured `DecisionResponse` model.

This confirms Phase 14 and Phase 15 are connected.

---

## 29. Mental Model

Use this mental model:

```text
Signals are facts.
Rules are interpretation logic.
DecisionResponse is the product output.
```

Example:

```text
Fact:
probe_success = 0

Fact:
frontend_endpoints = none

Fact:
frontend_pod_ready = true

Rule interpretation:
This matches service selector mismatch.

Product output:
Impact, evidence, likely cause, safe action.
```

This is the whole product logic in Phase 15.

---

## 30. How Phase 15 Prepares Phase 16

Phase 16 will replace this:

```text
sample_signals.py
```

With real collectors:

```text
Prometheus collector
Kubernetes collector
OpenSearch collector
```

But the rule engine should not care where the signals came from.

That is a key architecture principle.

The engine receives normalized signals.

Whether those signals came from a test file, Prometheus, Kubernetes, or OpenSearch should not matter.

```text
Collectors produce normalized signals.
Rule Engine evaluates normalized signals.
API returns decisions.
```

That separation makes the platform scalable.

---

## 31. Future Rule Examples

Later, the platform can add more rules.

### Pod crash rule

```text
IF probe_success = 0
AND frontend_pod_ready = false
AND restart_count increased
THEN likely root cause = pod crash or rollout failure
```

### Application error rule

```text
IF probe_success = 0
AND frontend_endpoints exist
AND frontend_pod_ready = true
AND frontend_error_rate is high
THEN likely root cause = application-level failure
```

### Network policy rule

```text
IF probe_success = 0
AND endpoints exist
AND pod is ready
AND Cilium/Hubble drops increased
THEN likely root cause = network policy or connectivity issue
```

### Rollout regression rule

```text
IF SLO breach occurs after Argo CD sync
AND deployment instability appears
THEN likely root cause = rollout regression
```

This shows how the product can grow.

---

## 32. What Phase 15 Proves

Phase 15 proves that:

- rules can be stored outside the API endpoint
- YAML rules can describe incident logic
- the engine can evaluate normalized signals
- the engine can return a typed DecisionResponse
- the endpoint can use the engine
- tests can verify both matching and non-matching scenarios

This is the first true Decision Intelligence layer.

---

## 33. What Phase 15 Does Not Prove Yet

Phase 15 does not prove:

- Prometheus integration
- Kubernetes API integration
- OpenSearch integration
- PostgreSQL persistence
- dynamic rule discovery
- multi-scenario support
- automatic remediation

Those come later.

Phase 15 focuses only on reasoning logic.

---

## 34. Recommended Git Commit

After validation:

```bash
git add app/engine app/rules app/api/v1/incidents.py app/tests/test_rule_engine.py pyproject.toml
git commit -m "feat: add rule engine v1 for frontend availability decision"
git push
```

---

## 35. Final Summary

Phase 15 changes the platform from a static incident API into a rule-based decision system.

The core concept is:

```text
Raw incident facts
    ↓
Normalized signals
    ↓
YAML rule conditions
    ↓
Rule Engine evaluation
    ↓
DecisionResponse
```

The first implemented decision is:

```text
Frontend availability breach caused by Service selector mismatch.
```

The business value is clear:

```text
Instead of only saying "the frontend is down",
the platform explains:

- the user path failed
- the Service has no endpoints
- the pod is still healthy
- the likely cause is Service selector mismatch
- the safe action is to restore the selector
```

That is the foundation of SRE Decision Intelligence.
