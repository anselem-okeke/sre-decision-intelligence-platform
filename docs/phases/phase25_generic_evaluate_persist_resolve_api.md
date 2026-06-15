# Phase 25 — Generic Evaluate / Persist / Resolve API

## Project

**SRE Decision Intelligence Platform**

## Phase status

**Implemented and validated**

Phase 25 introduces generic incident API endpoints that can evaluate, persist, and resolve incidents without being tied only to the original frontend availability path.

This phase remains under:

```text
/api/v1
```

No `/api/v2` is introduced because the new endpoints are additive and do not break existing API contracts.

---

## 1. Why Phase 25 exists

Before Phase 25, most runtime incident workflows were centered around frontend-specific endpoints:

```text
GET  /api/v1/incidents/frontend-availability/live
POST /api/v1/incidents/frontend-availability/live/persist
POST /api/v1/incidents/frontend-availability/live/resolve
GET  /api/v1/incidents/frontend-availability/live/evaluations
```

That was useful for proving the first complete vertical slice:

```text
collect frontend signals
        ↓
evaluate frontend rule
        ↓
create DecisionResponse
        ↓
persist incident
        ↓
resolve incident
        ↓
query timeline/history
```

However, after adding:

```text
Phase 21 — Scenario registry
Phase 22 — Multi-rule / multi-scenario engine
Phase 23 — Workload scenarios
Phase 24 — Platform scenarios
```

the platform needed a generic API that could evaluate any matching scenario, not only the frontend selector mismatch case.

Phase 25 introduces that generic API.

---

## 2. Main goal

The goal is to move from this style:

```text
/frontend-availability/live
/frontend-availability/live/persist
/frontend-availability/live/resolve
```

toward this scalable style:

```text
POST /api/v1/incidents/evaluate
POST /api/v1/incidents/evaluate/live
POST /api/v1/incidents/persist
POST /api/v1/incidents/live/persist
POST /api/v1/incidents/{incident_db_id}/resolve
```

This makes the API capable of working with any scenario that the rule engine understands.

---

## 3. Mental model

The generic API follows this flow:

```text
signals in
        ↓
MultiRuleEngine evaluates all known rules
        ↓
best matching rule wins
        ↓
DecisionResponse is returned
        ↓
optional persistence creates an incident record
        ↓
optional resolve updates incident lifecycle and timeline
```

This means scenario logic is now data-driven through rules and signals, not hardcoded into one frontend endpoint.

---

## 4. API endpoints introduced

Phase 25 adds these generic endpoints:

| Endpoint | Method | Purpose |
|---|---:|---|
| `/api/v1/incidents/evaluate` | POST | Evaluate caller-provided signals |
| `/api/v1/incidents/evaluate/live` | POST | Collect live signals and evaluate all rules |
| `/api/v1/incidents/persist` | POST | Evaluate provided signals and persist if matched |
| `/api/v1/incidents/live/persist` | POST | Collect live signals, evaluate, and persist if matched |
| `/api/v1/incidents/{incident_db_id}/resolve` | POST | Resolve a persisted incident by database ID |

Existing frontend-specific endpoints remain available for compatibility.

---

## 5. Files added or changed

Phase 25 adds or updates:

```text
app/schemas/generic_incidents.py
app/services/generic_incident_service.py
app/api/v1/incidents.py
app/tests/test_generic_incident_api.py
```

Supporting files from earlier phases remain important:

```text
app/engine/decision_engine.py
app/rules/
app/db/repository.py
app/db/models.py
app/collectors/frontend_availability.py
```

---

## 6. Generic API schemas

File:

```text
app/schemas/generic_incidents.py
```

This file defines request and response models for the generic incident API.

### 6.1 GenericEvaluateRequest

Purpose:

```text
Accept raw signals from an API caller.
```

Shape:

```python
class GenericEvaluateRequest(BaseModel):
    signals: dict[str, Any]
```

Example request:

```json
{
  "signals": {
    "probe_success": 0,
    "frontend_endpoints": "none",
    "frontend_pod_ready": true
  }
}
```

---

### 6.2 RuleEvaluationResponse

Purpose:

```text
Expose how each rule evaluated against the provided signals.
```

Fields:

```text
rule_id
scenario_id
name
matched
priority
failed_conditions
```

Example:

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

---

### 6.3 GenericEvaluateResponse

Purpose:

```text
Return the best matching decision plus full rule evaluation transparency.
```

Fields:

```text
matched
decision
evaluations
message
```

Example:

```json
{
  "matched": true,
  "decision": {
    "incident_id": "frontend-availability-breach"
  },
  "evaluations": [],
  "message": "Matching rule found."
}
```

If no rule matches:

```json
{
  "matched": false,
  "decision": null,
  "evaluations": [],
  "message": "No matching rule found for provided signals."
}
```

---

### 6.4 GenericPersistRequest

Purpose:

```text
Accept raw signals, evaluate them, and persist the incident only if a rule matches.
```

Shape:

```python
class GenericPersistRequest(BaseModel):
    signals: dict[str, Any]
```

---

### 6.5 GenericPersistResponse

Purpose:

```text
Return persistence outcome.
```

Fields:

```text
persisted
incident_db_id
incident_id
status
service
namespace
message
```

Example when persisted:

```json
{
  "persisted": true,
  "incident_db_id": "6e55...",
  "incident_id": "frontend-availability-breach",
  "status": "detected",
  "service": "frontend",
  "namespace": "fintech-workload",
  "message": "Incident persisted successfully."
}
```

Example when duplicate open incident exists:

```json
{
  "persisted": false,
  "incident_db_id": "6e55...",
  "incident_id": "frontend-availability-breach",
  "status": "detected",
  "service": "frontend",
  "namespace": "fintech-workload",
  "message": "Open incident already exists. Duplicate incident was not created."
}
```

---

### 6.6 GenericResolveRequest

Purpose:

```text
Accept recovery evidence/signals used when resolving an incident.
```

Shape:

```python
class GenericResolveRequest(BaseModel):
    recovery_signals: dict[str, Any] = {}
```

Example:

```json
{
  "recovery_signals": {
    "probe_success": 1,
    "frontend_endpoints": "10.244.8.229:8080",
    "frontend_pod_ready": true
  }
}
```

---

### 6.7 GenericResolveResponse

Purpose:

```text
Return resolution outcome.
```

Fields:

```text
status
incident_db_id
incident_id
service
namespace
message
```

Example:

```json
{
  "status": "resolved",
  "incident_db_id": "6e55...",
  "incident_id": "frontend-availability-breach",
  "service": "frontend",
  "namespace": "fintech-workload",
  "message": "Incident resolved successfully."
}
```

---

## 7. Generic incident service

File:

```text
app/services/generic_incident_service.py
```

The service layer prevents `app/api/v1/incidents.py` from becoming too large.

It owns the generic orchestration logic:

```text
evaluate signals
evaluate live signals
persist evaluated incident
persist live incident
resolve incident by ID
```

---

## 8. Service functions

### 8.1 evaluate_signals

Purpose:

```text
Evaluate provided signals against all rules.
```

Logic:

```text
MultiRuleEngine loads all rules
        ↓
evaluate_all() returns full evaluations
        ↓
evaluate() returns best matching DecisionResponse
        ↓
if no rule matches, return None
```

Expected signature:

```python
def evaluate_signals(signals: dict[str, Any]) -> tuple[DecisionResponse | None, list[dict[str, Any]]]:
    ...
```

---

### 8.2 evaluate_live_signals

Purpose:

```text
Collect live frontend availability signals and evaluate them generically.
```

Expected signature:

```python
def evaluate_live_signals() -> tuple[DecisionResponse | None, list[dict[str, Any]], dict[str, Any]]:
    ...
```

This currently uses:

```text
collect_frontend_availability_live_signals()
```

Later, this can be replaced with a richer live signal aggregator.

---

### 8.3 persist_evaluated_incident

Purpose:

```text
Evaluate provided signals and persist the incident if a rule matches.
```

Important behavior:

```text
if no rule matches:
    do not persist

if an open incident already exists:
    do not create duplicate

if a rule matches and no open duplicate exists:
    save DecisionResponse into PostgreSQL
```

This function uses:

```text
get_latest_open_incident()
save_decision_response()
```

---

### 8.4 persist_live_incident

Purpose:

```text
Collect current live signals and persist a matching incident if found.
```

This is the generic version of the old frontend-specific live persist workflow.

---

### 8.5 resolve_incident_by_id

Purpose:

```text
Resolve any persisted incident by database ID.
```

This function uses:

```text
get_incident_by_id()
resolve_incident_with_evidence()
```

It writes recovery evidence and timeline events through existing repository logic.

---

## 9. Generic API routes

File:

```text
app/api/v1/incidents.py
```

Phase 25 adds generic routes.

### 9.1 Evaluate provided signals

Endpoint:

```http
POST /api/v1/incidents/evaluate
```

Behavior:

```text
caller sends signals
API evaluates all rules
API returns matched decision or no-match result
```

Example:

```bash
curl -X POST http://localhost:8000/api/v1/incidents/evaluate   -H "Content-Type: application/json"   -d '{
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
  }' | jq
```

Expected:

```json
{
  "matched": true,
  "decision": {
    "incident_id": "frontend-availability-breach",
    "likely_root_cause": {
      "category": "service-routing"
    }
  },
  "message": "Matching rule found."
}
```

---

### 9.2 Evaluate live signals

Endpoint:

```http
POST /api/v1/incidents/evaluate/live
```

Behavior:

```text
API collects live signals
API evaluates all rules
API returns matched decision or no-match result
```

On healthy cluster, expected:

```json
{
  "matched": false,
  "decision": null,
  "message": "No matching rule found for current live signals."
}
```

---

### 9.3 Persist provided signals

Endpoint:

```http
POST /api/v1/incidents/persist
```

Behavior:

```text
caller sends signals
API evaluates all rules
if a rule matches, persist incident
if no rule matches, do not persist
if duplicate open incident exists, do not create another
```

Example request is same signal body as `/evaluate`.

Expected persisted response:

```json
{
  "persisted": true,
  "incident_id": "frontend-availability-breach",
  "status": "detected"
}
```

---

### 9.4 Persist live incident

Endpoint:

```http
POST /api/v1/incidents/live/persist
```

Behavior:

```text
API collects current live signals
API evaluates all rules
API persists if a rule matches
```

On healthy cluster, expected:

```json
{
  "persisted": false,
  "message": "No matching rule found. Incident was not persisted."
}
```

During a matching failure, expected:

```json
{
  "persisted": true,
  "incident_id": "frontend-availability-breach",
  "status": "detected"
}
```

---

### 9.5 Resolve incident by database ID

Endpoint:

```http
POST /api/v1/incidents/{incident_db_id}/resolve
```

Behavior:

```text
resolve an existing incident by database primary key
attach recovery evidence
write resolution timeline events
update status to resolved
```

Example:

```bash
curl -X POST http://localhost:8000/api/v1/incidents/<INCIDENT_DB_ID>/resolve   -H "Content-Type: application/json"   -d '{
    "recovery_signals": {
      "probe_success": 1,
      "frontend_endpoints": "10.244.8.229:8080",
      "frontend_pod_ready": true
    }
  }' | jq
```

Expected:

```json
{
  "status": "resolved",
  "incident_id": "frontend-availability-breach",
  "message": "Incident resolved successfully."
}
```

---

## 10. Route order requirement

Because the router has dynamic UUID paths, static routes must come first.

Correct ordering:

```text
/history
/open
/resolved
/evaluate
/evaluate/live
/persist
/live/persist
/{incident_db_id}/timeline
/{incident_db_id}/resolve
/{incident_db_id}
```

The generic static routes must be defined before:

```text
/{incident_db_id}
```

Otherwise FastAPI may interpret `/evaluate` or `/persist` as an `incident_db_id`.

---

## 11. Duplicate incident protection

Phase 25 includes duplicate protection.

Before persisting, the service checks:

```python
existing_incident = get_latest_open_incident(
    db=db,
    incident_id=decision.incident_id,
    service=decision.service,
    namespace=decision.namespace,
)
```

If an open incident already exists, the API returns:

```json
{
  "persisted": false,
  "message": "Open incident already exists. Duplicate incident was not created."
}
```

This prevents repeated calls to `/persist` or `/live/persist` from creating endless open incidents for the same active failure.

---

## 12. Tests added

File:

```text
app/tests/test_generic_incident_api.py
```

Expected tests include:

```text
test_generic_evaluate_matches_frontend_selector_mismatch
test_generic_evaluate_returns_no_match_for_healthy_signals
test_generic_evaluate_matches_platform_node_not_ready
test_generic_persist_creates_incident_for_matching_signals
```

These tests validate:

```text
generic evaluate works
healthy signals do not match
platform scenario evaluation works
generic persist writes an incident
```

---

## 13. Validation commands

### 13.1 Validate service imports

```bash
python - <<'PY'
from app.services.generic_incident_service import (
    evaluate_signals,
    evaluate_live_signals,
    persist_evaluated_incident,
    persist_live_incident,
    resolve_incident_by_id,
)

print("generic incident service imports ok")
PY
```

Expected:

```text
generic incident service imports ok
```

---

### 13.2 Validate routes

```bash
python - <<'PY'
from app.main import app

for route in app.routes:
    if "/api/v1/incidents" in route.path:
        print(route.path, route.methods)
PY
```

Expected generic routes:

```text
/api/v1/incidents/evaluate {'POST'}
/api/v1/incidents/evaluate/live {'POST'}
/api/v1/incidents/persist {'POST'}
/api/v1/incidents/live/persist {'POST'}
/api/v1/incidents/{incident_db_id}/resolve {'POST'}
```

---

### 13.3 Run generic tests

```bash
pytest app/tests/test_generic_incident_api.py -q
```

Expected:

```text
4 passed
```

---

### 13.4 Run regression tests

```bash
pytest app/tests/test_generic_incident_api.py -q
pytest app/tests/test_multi_rule_engine.py -q
pytest app/tests/test_workload_scenarios.py -q
pytest app/tests/test_platform_scenarios.py -q
```

Expected:

```text
all passed
```

---

### 13.5 Run full suite

```bash
pytest
```

Expected after the project reached Phase 26:

```text
62 passed
```

Warnings are currently not blockers.

---

## 14. Manual runtime validation

Start API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### 14.1 Healthy evaluate

```bash
curl -X POST http://localhost:8000/api/v1/incidents/evaluate   -H "Content-Type: application/json"   -d '{
    "signals": {
      "probe_success": 1,
      "frontend_availability_5m": 1.0,
      "alert_state": "inactive",
      "frontend_endpoints": "10.244.8.229:8080",
      "frontend_pod_ready": true,
      "frontend_pod_status": "1/1 Running",
      "frontend_logs": "mostly INFO",
      "frontend_error_log_count": 0,
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
  }' | jq
```

Expected:

```json
{
  "matched": false,
  "decision": null
}
```

---

### 14.2 Selector mismatch evaluate

```bash
curl -X POST http://localhost:8000/api/v1/incidents/evaluate   -H "Content-Type: application/json"   -d '{
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
  }' | jq
```

Expected:

```json
{
  "matched": true,
  "decision": {
    "incident_id": "frontend-availability-breach",
    "likely_root_cause": {
      "category": "service-routing"
    }
  }
}
```

---

### 14.3 Platform scenario evaluate

Example: NodeNotReady.

```bash
curl -X POST http://localhost:8000/api/v1/incidents/evaluate   -H "Content-Type: application/json"   -d '{
    "signals": {
      "probe_success": 1,
      "frontend_availability_5m": 1.0,
      "alert_state": "inactive",
      "frontend_endpoints": "10.244.8.229:8080",
      "frontend_pod_ready": true,
      "frontend_pod_status": "1/1 Running",
      "frontend_logs": "mostly INFO",
      "frontend_error_log_count": 0,
      "frontend_5xx_rate": 0.0,
      "frontend_latency_p95_ms": 120,
      "transaction_error_rate": 0.0,
      "backend_timeout_count": 0,
      "ledger_database_error_count": 0,
      "pod_crashloop": false,
      "image_pull_backoff": false,
      "failed_scheduling": false,
      "node_not_ready": true,
      "oom_killed": false,
      "pvc_mount_failure": false,
      "cilium_drop_count": 0,
      "longhorn_volume_degraded": false,
      "argocd_sync_status": "Synced"
    }
  }' | jq
```

Expected:

```json
{
  "matched": true,
  "decision": {
    "likely_root_cause": {
      "category": "node-health"
    }
  }
}
```

---

### 14.4 Generic persist

Clean DB first if needed:

```bash
docker exec -it sre-decision-postgres psql -U sre -d sre_decision_intelligence
```

```sql
DELETE FROM incident_events;
DELETE FROM rule_evaluations;
DELETE FROM decisions;
DELETE FROM evidence_items;
DELETE FROM signals;
DELETE FROM incidents;
\q
```

Persist:

```bash
curl -X POST http://localhost:8000/api/v1/incidents/persist   -H "Content-Type: application/json"   -d '{
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
  }' | jq
```

Expected:

```json
{
  "persisted": true,
  "incident_id": "frontend-availability-breach",
  "status": "detected"
}
```

Save:

```text
incident_db_id
```

---

### 14.5 Duplicate protection

Run the same `/persist` request again.

Expected:

```json
{
  "persisted": false,
  "message": "Open incident already exists. Duplicate incident was not created."
}
```

---

### 14.6 Generic resolve

```bash
curl -X POST http://localhost:8000/api/v1/incidents/<INCIDENT_DB_ID>/resolve   -H "Content-Type: application/json"   -d '{
    "recovery_signals": {
      "probe_success": 1,
      "frontend_endpoints": "10.244.8.229:8080",
      "frontend_pod_ready": true
    }
  }' | jq
```

Expected:

```json
{
  "status": "resolved",
  "incident_id": "frontend-availability-breach",
  "message": "Incident resolved successfully."
}
```

---

### 14.7 Validate history and timeline

```bash
curl http://localhost:8000/api/v1/incidents/history | jq
```

Then:

```bash
curl http://localhost:8000/api/v1/incidents/<INCIDENT_DB_ID>/timeline | jq
```

Expected timeline includes:

```text
incident_detected
signals_collected
rule_matched
decision_created
recovery_observed
incident_resolved
```

---

## 15. Common issues and fixes

### 15.1 Route shadowing

Problem:

```text
/evaluate is interpreted as {incident_db_id}
```

Cause:

```text
/{incident_db_id} route appears before /evaluate
```

Fix:

```text
Place /evaluate, /persist, /live/persist before /{incident_db_id}
```

---

### 15.2 Response validation error on persist

Problem:

```text
GenericPersistResponse validation fails
```

Possible cause:

```text
service returns extra keys not in response model
```

Fix:

Either add the key to the response model or remove it from the returned dictionary.

For Phase 25, keep `GenericPersistResponse` simple:

```text
persisted
incident_db_id
incident_id
status
service
namespace
message
```

---

### 15.3 Duplicate incidents

Problem:

```text
Repeated /persist creates multiple open incidents
```

Fix:

Ensure `persist_evaluated_incident()` calls:

```text
get_latest_open_incident()
```

before saving.

---

### 15.4 Cleanup fails due to FK constraints

If tests fail during cleanup, delete child tables first:

```sql
DELETE FROM incident_events;
DELETE FROM rule_evaluations;
DELETE FROM decisions;
DELETE FROM evidence_items;
DELETE FROM signals;
DELETE FROM incidents;
```

---

## 16. Success criteria

Phase 25 is complete when:

```text
Generic evaluate endpoint works
Generic live evaluate endpoint works
Generic persist endpoint works
Generic live persist endpoint works
Generic resolve by ID endpoint works
Duplicate protection works
Existing frontend-specific endpoints still work
Generic API tests pass
Full pytest passes
```

---

## 17. Git commit

After validation:

```bash
git status
```

Then:

```bash
git add app/schemas/generic_incidents.py         app/services/generic_incident_service.py         app/api/v1/incidents.py         app/tests/test_generic_incident_api.py
```

If cleanup was updated:

```bash
git add app/tests/db_cleanup.py
```

Commit:

```bash
git commit -m "feat: add generic incident evaluate persist resolve API"
git push
```

---

## 18. What Phase 25 gives the project

Before Phase 25:

```text
The API was mostly frontend-specific.
```

After Phase 25:

```text
The API can evaluate, persist, and resolve incidents generically across all known scenarios.
```

This means the platform now behaves more like a reusable SRE decision service instead of a single frontend outage demo.

---

## 19. Next phase

The next phase is:

```text
Phase 26 — Service Layer Refactor and Incident API Cleanup
```

Phase 26 moves orchestration logic out of `incidents.py` and into service modules, making the API routing layer thinner and cleaner.
