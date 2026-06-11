# API Design Mental Model Cheat Sheet
## Using the Phase 17 SRE Decision Intelligence Platform as the Example

**Project context:** SRE Decision Intelligence Platform  
**Use case:** Detect a real Kubernetes frontend availability incident, persist the incident decision to PostgreSQL, resolve it after recovery, and query the incident history through an API.

---

## 1. The Core Mental Model

A real API is not just a list of URLs.

A functional API is a controlled interface that lets another system or human do something useful with your application.

Think of an API as this pipeline:

```text
Client request
    ↓
Route / endpoint
    ↓
Input validation
    ↓
Application logic
    ↓
Database / external systems
    ↓
Response formatting
    ↓
HTTP response
```

In Phase 17, we built this exact flow:

```text
curl / FastAPI client
    ↓
/api/v1/incidents/...
    ↓
FastAPI route function
    ↓
Collectors / RuleEngine / Repository
    ↓
PostgreSQL
    ↓
Presenter function
    ↓
JSON response
```

---

## 2. The Big API Design Question

Before writing any endpoint, ask:

> What action or information should this API expose?

For Phase 17, the user-facing capabilities were:

| User Need | API Capability |
|---|---|
| Check if API works | Health endpoint |
| Check if database works | DB health endpoint |
| Evaluate sample incident | Sample incident endpoint |
| Evaluate real live incident | Live incident endpoint |
| Persist a real incident | Live persist endpoint |
| Resolve an incident | Live resolve endpoint |
| See incident history | Query endpoints |
| Inspect one incident deeply | Detail endpoint |

This is how API design starts: not with code, but with capabilities.

---

## 3. API Design Layers

A clean API should separate responsibilities.

In Phase 17, the layers became:

```text
app/main.py
    Creates FastAPI app and includes routers

app/api/v1/incidents.py
    API routes only: paths, HTTP methods, errors, dependency injection

app/api/v1/incident_presenters.py
    Converts database objects into JSON-friendly API responses

app/collectors/
    Reads live signals from Prometheus, Kubernetes, OpenSearch

app/engine/
    Evaluates rules and produces DecisionResponse

app/db/models.py
    SQLAlchemy database table models

app/db/repository.py
    Database read/write functions

app/db/session.py
    Database connection/session lifecycle

alembic/
    Versioned database schema migrations
```

The mental model:

```text
Route handles HTTP.
Repository handles database.
Model defines tables.
Presenter formats response.
Engine decides meaning.
Collector gathers evidence.
```

---

## 4. Route Design: URL + HTTP Verb + Meaning

An endpoint should make the operation obvious.

### GET means read

```http
GET /api/v1/incidents/history
GET /api/v1/incidents/open
GET /api/v1/incidents/resolved
GET /api/v1/incidents/{incident_db_id}
```

These do not change the system. They only return data.

### POST means create, trigger, or perform an action

```http
POST /api/v1/incidents/frontend-availability/sample/persist
POST /api/v1/incidents/frontend-availability/live/persist
POST /api/v1/incidents/frontend-availability/live/resolve
```

These change state or trigger logic.

---

## 5. Why We Split Sample and Live Endpoints

Originally, the endpoint looked like this:

```http
POST /api/v1/incidents/frontend-availability/persist
```

That was confusing because it used sample/demo signals but looked like a live incident.

We changed it to:

```http
POST /api/v1/incidents/frontend-availability/sample/persist
POST /api/v1/incidents/frontend-availability/live/persist
```

The design lesson:

> Endpoint names must reveal whether they operate on demo data, live data, or stored data.

### Correct mental model

```text
/sample/persist
    Uses fixed test/sample signals.
    Good for development and tests.
    Not real cluster state.

/live/persist
    Uses current Prometheus + Kubernetes + OpenSearch signals.
    Writes only if the rule matches current evidence.
```

---

## 6. The Phase 17 API Map

### Health

```http
GET /health
```

Purpose:

```text
Is the API process alive?
```

Expected:

```json
{
  "status": "ok"
}
```

---

### Database Health

```http
GET /health/db
```

Purpose:

```text
Can the API connect to PostgreSQL?
```

Expected:

```json
{
  "status": "ok",
  "database": "postgresql"
}
```

---

### Sample Decision

```http
GET /api/v1/incidents/frontend-availability
```

Purpose:

```text
Return a known validated DecisionResponse using sample signals.
```

Use it when:

```text
You want to test the rule engine without relying on live cluster state.
```

---

### Live Decision

```http
GET /api/v1/incidents/frontend-availability/live
```

Purpose:

```text
Collect live signals and evaluate the rule engine.
```

Behavior:

```text
If live signals match the rule → returns DecisionResponse.
If live signals do not match → returns 404.
```

---

### Live Signals Debug Endpoint

```http
GET /api/v1/incidents/frontend-availability/live/signals
```

Purpose:

```text
Show the raw live signals before the rule engine decides.
```

This endpoint is extremely important for troubleshooting.

Expected healthy state:

```json
{
  "probe_success": 1.0,
  "frontend_endpoints": "10.244.8.229:8080",
  "frontend_pod_ready": true
}
```

Expected broken state:

```json
{
  "probe_success": 0.0,
  "frontend_endpoints": "none",
  "frontend_pod_ready": true
}
```

---

### Sample Persist

```http
POST /api/v1/incidents/frontend-availability/sample/persist
```

Purpose:

```text
Persist a sample/demo incident into PostgreSQL.
```

Use it for:

```text
Testing database persistence
Testing query APIs
Testing repository functions
```

Do not confuse it with real incidents.

---

### Live Persist

```http
POST /api/v1/incidents/frontend-availability/live/persist
```

Purpose:

```text
Persist a real current live incident only if live evidence supports it.
```

Healthy cluster behavior:

```json
{
  "detail": {
    "message": "No matching live incident rule found. Nothing was persisted.",
    "reason": "No matching rule found for provided signals"
  }
}
```

Broken Service selector behavior:

```text
HTTP 200
DecisionResponse JSON
```

---

### Live Resolve

```http
POST /api/v1/incidents/frontend-availability/live/resolve
```

Purpose:

```text
Mark the latest open incident as resolved when live signals prove recovery.
```

Recovery condition:

```text
probe_success == 1.0
frontend_endpoints != "none"
frontend_pod_ready == true
```

Expected success:

```json
{
  "status": "resolved",
  "incident_id": "frontend-availability-breach",
  "service": "frontend",
  "namespace": "fintech-workload",
  "resolved_at": "2026-06-10T..."
}
```

If no open incident exists:

```json
{
  "detail": {
    "message": "No open frontend availability incident found to resolve."
  }
}
```

---

### Incident History

```http
GET /api/v1/incidents/history
```

Purpose:

```text
Return all persisted incidents, latest first.
```

---

### Open Incidents

```http
GET /api/v1/incidents/open
```

Purpose:

```text
Return incidents where status = detected.
```

---

### Resolved Incidents

```http
GET /api/v1/incidents/resolved
```

Purpose:

```text
Return incidents where status = resolved.
```

---

### Incident Detail

```http
GET /api/v1/incidents/{incident_db_id}
```

Purpose:

```text
Return one full incident with signals, evidence, decision, and rule evaluation.
```

This is the endpoint that turns the database into an investigation API.

---

## 7. Route Ordering Rule

This matters in FastAPI.

Put static routes first:

```python
@router.get("/history")
@router.get("/open")
@router.get("/resolved")
```

Put dynamic routes last:

```python
@router.get("/{incident_db_id}")
```

Why?

Because if this comes first:

```python
@router.get("/{incident_db_id}")
```

FastAPI may treat:

```text
/history
/open
/resolved
```

as if they were incident IDs.

Correct order:

```text
/history
/open
/resolved
/{incident_db_id}
```

---

## 8. API File Design Rule

Do not put everything into the route file.

### Bad mental model

```text
incidents.py does everything:
    routes
    database queries
    business logic
    response formatting
    SQLAlchemy models
```

This becomes hard to maintain.

### Good mental model

```text
incidents.py
    Receives HTTP request
    Calls the right service/repository
    Returns HTTP response

repository.py
    Reads/writes PostgreSQL

models.py
    Defines tables

incident_presenters.py
    Formats DB models into JSON

decision_engine.py
    Evaluates rules

collectors/
    Collect live observability signals
```

---

## 9. Example: How a Live Persist Request Works

Command:

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/persist | jq
```

Internal flow:

```text
POST /live/persist
    ↓
FastAPI route function
    ↓
collect_frontend_availability_live_signals()
    ↓
PrometheusCollector
KubernetesCollector
OpenSearchCollector
    ↓
RuleEngine.evaluate(signals)
    ↓
If rule matches:
    save_decision_response()
        ↓
        INSERT incidents
        INSERT signals
        INSERT evidence_items
        INSERT decisions
        INSERT rule_evaluations
    ↓
Return DecisionResponse JSON
```

If the rule does not match:

```text
No DB write.
Return HTTP 404.
```

---

## 10. Example: How a Resolve Request Works

Command:

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/resolve | jq
```

Internal flow:

```text
POST /live/resolve
    ↓
Collect live signals
    ↓
Check recovery condition:
        probe_success == 1.0
        endpoints != none
        pod_ready == true
    ↓
Find latest open incident
    ↓
Update incident:
        status = resolved
        resolved_at = now
    ↓
Insert resolution evidence
    ↓
Return resolved response
```

---

## 11. PostgreSQL Design Mental Model

The database stores incident history.

It is not just storing raw alerts.

It stores the decision context.

### Tables

```text
incidents
signals
evidence_items
decisions
rule_evaluations
```

### Table responsibilities

| Table | Meaning |
|---|---|
| incidents | Main incident lifecycle record |
| signals | Raw/normalized signal values |
| evidence_items | Human-readable evidence |
| decisions | Decision output: impact, root cause, safe action |
| rule_evaluations | Which rule matched and why |

---

## 12. Database Relationship Model

One incident can have many supporting records:

```text
incidents
    ├── many signals
    ├── many evidence_items
    ├── many decisions
    └── many rule_evaluations
```

Example:

```text
incident: frontend-availability-breach
    signals:
        probe_success = 0
        frontend_endpoints = none
        frontend_pod_ready = true

    evidence:
        frontend Service endpoints became empty
        frontend pod remained 1/1 Running

    decision:
        root_cause = service-routing
        safe_action = restore Service selector

    rule_evaluation:
        rule_id = frontend-service-selector-mismatch
        matched = true
```

---

## 13. Incident Lifecycle Model

Current lifecycle:

```text
detected → resolved
```

### During failure

```text
status = detected
resolved_at = null
```

### After recovery

```text
status = resolved
resolved_at = timestamp
```

Resolution does not create a new incident. It updates the existing open incident.

---

## 14. Alembic Mental Model

SQLAlchemy models define what tables should look like.

Alembic tracks how the database changes over time.

```text
models.py
    ↓
alembic revision --autogenerate
    ↓
migration file
    ↓
alembic upgrade head
    ↓
PostgreSQL schema updated
```

Do not think of Alembic as the database.

Think of Alembic as the version-control system for database schema.

---

## 15. Alembic Commands Cheat Sheet

### Initialize Alembic

Only once:

```bash
alembic init alembic
```

### Create a migration from model changes

```bash
alembic revision --autogenerate -m "create core decision tables"
```

### Apply migrations

```bash
alembic upgrade head
```

### See current DB migration version

```bash
alembic current
```

### See migration history

```bash
alembic history
```

### Downgrade one migration

```bash
alembic downgrade -1
```

Use downgrade carefully.

---

## 16. When to Create a New Migration

Create a new migration when you change database structure:

```text
Add table
Remove table
Add column
Rename column
Change column type
Add index
Add constraint
```

Do not create a migration when you only change:

```text
API route logic
Repository query logic
Presenter formatting
Tests
README/docs
```

---

## 17. Running the API Locally

From repo root:

```bash
cd /mnt/data/sre-decision-intelligence-platform
```

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Apply migrations:

```bash
alembic upgrade head
```

Start API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Validate routes:

```bash
curl http://localhost:8000/openapi.json | jq '.paths | keys[]'
```

Validate incident routes only:

```bash
curl http://localhost:8000/openapi.json | jq '.paths | keys[]' | grep incidents
```

---

## 18. Database Validation Commands

Enter PostgreSQL:

```bash
docker exec -it sre-decision-postgres psql -U sre -d sre_decision_intelligence
```

List tables:

```sql
\dt
```

Check incidents:

```sql
SELECT incident_id, service, namespace, status, created_at, resolved_at
FROM incidents
ORDER BY created_at DESC
LIMIT 10;
```

Check decisions:

```sql
SELECT root_cause_category, confidence, safe_action_summary, created_at
FROM decisions
ORDER BY created_at DESC
LIMIT 10;
```

Check signals:

```sql
SELECT source, name, value, meaning, collected_at
FROM signals
ORDER BY collected_at DESC
LIMIT 20;
```

Check evidence:

```sql
SELECT source, category, summary, payload, created_at
FROM evidence_items
ORDER BY created_at DESC
LIMIT 20;
```

Exit:

```sql
\q
```

---

## 19. Clean Database for Controlled Testing

Use this only in lab/dev:

```sql
DELETE FROM rule_evaluations;
DELETE FROM decisions;
DELETE FROM evidence_items;
DELETE FROM signals;
DELETE FROM incidents;
```

Or from shell:

```bash
docker exec -it sre-decision-postgres psql -U sre -d sre_decision_intelligence
```

Then run the SQL cleanup above.

---

## 20. Full Break-Fix Validation Scenario

This is the most important practical test.

### Step 1: Confirm healthy frontend

```bash
kubectl get endpoints frontend -n fintech-workload
kubectl get pods -n fintech-workload -l app=frontend
```

Expected:

```text
frontend   10.x.x.x:8080
frontend-...   1/1 Running
```

### Step 2: Healthy live signals

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

Expected:

```json
{
  "probe_success": 1.0,
  "frontend_endpoints": "10.x.x.x:8080",
  "frontend_pod_ready": true
}
```

### Step 3: Healthy live persist should not write

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/persist | jq
```

Expected:

```json
{
  "detail": {
    "message": "No matching live incident rule found. Nothing was persisted."
  }
}
```

### Step 4: Break Service selector

```bash
kubectl patch svc frontend -n fintech-workload \
  --type='merge' \
  -p '{"spec":{"selector":{"app":"frontend","application":"bank-of-anthos","environment":"development","team":"frontend","tier":"web","slo-test":"broken"}}}'
```

### Step 5: Verify endpoints are empty

```bash
kubectl get endpoints frontend -n fintech-workload
```

Expected:

```text
frontend   <none>
```

### Step 6: Pod should still be healthy

```bash
kubectl get pods -n fintech-workload -l app=frontend
```

Expected:

```text
frontend-...   1/1 Running
```

### Step 7: Wait for Prometheus

```bash
sleep 60
```

### Step 8: Check live signals

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

Expected:

```json
{
  "probe_success": 0.0,
  "frontend_availability_5m": 0.6,
  "alert_state": "pending",
  "frontend_endpoints": "none",
  "frontend_pod_ready": true,
  "frontend_pod_status": "1/1 Running"
}
```

### Step 9: Persist live incident

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/persist | jq
```

Expected:

```text
DecisionResponse JSON
```

### Step 10: Check open incidents

```bash
curl http://localhost:8000/api/v1/incidents/open | jq
```

Expected:

```json
[
  {
    "incident_id": "frontend-availability-breach",
    "service": "frontend",
    "namespace": "fintech-workload",
    "status": "detected"
  }
]
```

### Step 11: Restore Service selector

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

### Step 12: Verify endpoints recovered

```bash
kubectl get endpoints frontend -n fintech-workload
```

Expected:

```text
frontend   10.x.x.x:8080
```

### Step 13: Wait for Prometheus recovery

```bash
sleep 60
```

### Step 14: Resolve incident

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/resolve | jq
```

Expected:

```json
{
  "status": "resolved",
  "incident_id": "frontend-availability-breach",
  "service": "frontend",
  "namespace": "fintech-workload",
  "resolved_at": "..."
}
```

### Step 15: Check open incidents

```bash
curl http://localhost:8000/api/v1/incidents/open | jq
```

Expected:

```json
[]
```

### Step 16: Check resolved incidents

```bash
curl http://localhost:8000/api/v1/incidents/resolved | jq
```

Expected:

```json
[
  {
    "incident_id": "frontend-availability-breach",
    "status": "resolved"
  }
]
```

---

## 21. Troubleshooting Cheat Sheet

### Problem: API returns `{"detail": "Not Found"}`

Check registered routes:

```bash
curl http://localhost:8000/openapi.json | jq '.paths | keys[]' | grep incidents
```

If the route is missing:

```bash
pkill -f "uvicorn app.main:app"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Also check route exists in code:

```bash
grep -n "live/resolve\|live/persist\|history\|open\|resolved" app/api/v1/incidents.py
```

---

### Problem: Circular import

Bad:

```python
from app.api.v1.incidents import incident_to_detail
```

Good:

```python
from app.api.v1.incident_presenters import incident_to_detail
```

---

### Problem: `NameError: UUID is not defined`

Add:

```python
from uuid import UUID
```

to `app/api/v1/incidents.py`.

---

### Problem: `Incident has no attribute evidence`

Use correct relationship name:

```python
Incident.evidence_items
```

not:

```python
Incident.evidence
```

Use correct relationship name:

```python
Incident.rule_evaluations
```

not:

```python
Incident.actions
```

---

### Problem: Live persist does not create DB record

Check live signals first:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

The rule needs:

```text
probe_success = 0.0
frontend_endpoints = none
frontend_pod_ready = true
```

If these are not true, no record should be created.

---

### Problem: Resolve says no open incident found

Check DB:

```sql
SELECT incident_id, status, created_at, resolved_at
FROM incidents
ORDER BY created_at DESC;
```

If there is no row with:

```text
status != resolved
```

then there is nothing to resolve.

---

## 22. Testing Cheat Sheet

Run one test file:

```bash
pytest app/tests/test_incident_query_api.py -q
```

Run full suite:

```bash
pytest
```

Expected after Phase 17E:

```text
all tests passed
```

If tests leave database rows behind, use cleanup helper:

```python
clean_decision_tables()
```

This should be used in DB-writing tests.

---

## 23. Design Checklist for Building a Real API

When designing a new API feature, follow this checklist:

### 1. Define the use case

```text
What should the client be able to do?
```

Example:

```text
Resolve an open incident after frontend recovery.
```

### 2. Choose HTTP method

```text
GET  = read
POST = create/action
PUT/PATCH = update
DELETE = delete
```

Example:

```http
POST /api/v1/incidents/frontend-availability/live/resolve
```

### 3. Decide data source

```text
Sample data?
Live collectors?
Database?
External service?
```

### 4. Decide if it writes to DB

```text
Read-only?
Persist new record?
Update existing record?
```

### 5. Decide success response

```text
What JSON should the caller receive if it works?
```

### 6. Decide failure responses

```text
404 = not found / no matching incident
409 = current state does not allow action
503 = dependency unavailable
```

### 7. Put logic in correct layer

```text
Route: HTTP handling
Repository: database
Collector: external signals
Engine: decision logic
Presenter: response formatting
```

### 8. Add tests

```text
Route test
Repository test
Failure case test
```

### 9. Validate manually

```text
curl
jq
psql
kubectl
```

---

## 24. Your Phase 17 Mental Model in One Picture

```text
Kubernetes / Prometheus / OpenSearch
        ↓
Collectors
        ↓
Normalized signals
        ↓
RuleEngine
        ↓
DecisionResponse
        ↓
FastAPI route
        ↓
Repository
        ↓
PostgreSQL
        ↓
Query API
        ↓
Human/SRE investigation
```

---

## 25. What You Should Remember

The API is the product interface.

The database is the memory.

The collectors are the eyes.

The rule engine is the reasoning layer.

The repository is the database access boundary.

The presenter is the response formatter.

The tests are the safety net.

A real API is not just endpoints. A real API makes system behavior understandable, repeatable, testable, and safe.

