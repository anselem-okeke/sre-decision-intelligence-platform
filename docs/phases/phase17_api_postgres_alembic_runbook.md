# Phase 17 Runbook — API, PostgreSQL Persistence, Alembic, Live Incident Validation

**Project:** SRE Decision Intelligence Platform  
**Phase:** 17A–17E  
**Scope:** FastAPI incident APIs, PostgreSQL persistence, Alembic migrations, live incident persistence, resolution tracking, incident query APIs, and troubleshooting.

---

## 0. What Phase 17 Built

Phase 17 transformed the platform from a decision engine that only returned API responses into a platform that can **store incident decisions**, **track incident lifecycle**, and **query historical incident records**.

Before Phase 17:

```text
Live signals → Rule Engine → DecisionResponse
```

After Phase 17:

```text
Live signals
    ↓
Rule Engine
    ↓
DecisionResponse
    ↓
PostgreSQL persistence
    ↓
Incident history / open incidents / resolved incidents / detailed incident evidence
```

Phase 17 covered:

| Phase | Purpose | Result |
|---|---|---|
| 17A | PostgreSQL foundation | DB service, DB health endpoint, SQLAlchemy engine/session |
| 17B | Core persistence | Incidents, signals, evidence, decisions, rule evaluations stored |
| 17C | Alembic migrations | Versioned DB schema creation |
| 17D | Resolution tracking | Incident status changes from `detected` to `resolved` |
| 17E | Query APIs + resolution evidence | API endpoints for incident history, open/resolved incidents, detailed records |

---

## 1. Mental Model: What the API Does

The FastAPI application exposes incident-related endpoints under:

```text
/api/v1/incidents
```

The API is not only returning live diagnostic data anymore. It now has three roles:

```text
1. Read current live signals
2. Persist incident decisions when a live rule matches
3. Query stored incident history from PostgreSQL
```

### Main request flow

```text
Client / curl / browser
        ↓
FastAPI route in app/api/v1/incidents.py
        ↓
Collector or repository function
        ↓
RuleEngine or PostgreSQL
        ↓
JSON response
```

---

## 2. Important Files and Responsibilities

| File | Responsibility |
|---|---|
| `app/main.py` | Creates FastAPI app and registers routers |
| `app/api/v1/incidents.py` | Incident API routes, HTTP errors, dependency injection |
| `app/api/v1/incident_presenters.py` | Converts DB models into API response dictionaries |
| `app/collectors/frontend_availability.py` | Aggregates Prometheus, Kubernetes, and OpenSearch live signals |
| `app/db/session.py` | SQLAlchemy engine, session factory, DB connection check |
| `app/db/models.py` | SQLAlchemy database table models |
| `app/db/repository.py` | Database persistence, query, resolution functions |
| `app/db/base.py` | SQLAlchemy declarative base |
| `alembic/env.py` | Alembic migration configuration connected to app models |
| `alembic/versions/` | Generated DB migration files |
| `scripts/init_db.py` | Applies Alembic migrations |
| `docker-compose.yml` | Runs PostgreSQL locally |
| `.env` | Runtime environment values, including `DATABASE_URL` |
| `.env.example` | Safe example environment config |

---

## 3. API Design Cheat Sheet

### Current incident endpoints

| Method | Endpoint | Purpose | Writes DB? |
|---|---|---|---|
| `GET` | `/api/v1/incidents/frontend-availability` | Return sample/demo decision | No |
| `GET` | `/api/v1/incidents/frontend-availability/live` | Evaluate live signals and return decision if rule matches | No |
| `GET` | `/api/v1/incidents/frontend-availability/live/signals` | Return raw live collector signals | No |
| `POST` | `/api/v1/incidents/frontend-availability/sample/persist` | Persist sample/demo decision | Yes |
| `POST` | `/api/v1/incidents/frontend-availability/live/persist` | Persist real live incident only if rule matches | Yes, only on match |
| `POST` | `/api/v1/incidents/frontend-availability/live/resolve` | Resolve latest open incident if live state recovered | Updates DB |
| `GET` | `/api/v1/incidents/history` | List recent incidents | No |
| `GET` | `/api/v1/incidents/open` | List open/detected incidents | No |
| `GET` | `/api/v1/incidents/resolved` | List resolved incidents | No |
| `GET` | `/api/v1/incidents/{incident_db_id}` | Return full detail for one incident | No |

---

## 4. Route File Design

### `app/api/v1/incidents.py`

This file should mainly contain:

```text
FastAPI route decorators
HTTP status handling
Dependency injection using Depends(get_db)
Calls to collectors, rule engine, repository functions
```

It should **not** contain heavy formatting logic or database model definitions.

### `app/api/v1/incident_presenters.py`

This file contains helper functions:

```python
incident_to_summary(incident)
incident_to_detail(incident)
```

These convert SQLAlchemy model objects into simple JSON-compatible dictionaries.

Correct import in `incidents.py`:

```python
from app.api.v1.incident_presenters import incident_to_detail, incident_to_summary
```

Wrong import, causes circular import:

```python
from app.api.v1.incidents import incident_to_detail, incident_to_summary
```

---

## 5. PostgreSQL Design

Phase 17 created these core tables:

```text
incidents
signals
evidence_items
decisions
rule_evaluations
alembic_version
```

### Table purpose

| Table | Purpose |
|---|---|
| `incidents` | Main incident lifecycle record |
| `signals` | Raw/normalized input signals used by the decision |
| `evidence_items` | Human-readable evidence and resolution evidence |
| `decisions` | Root cause, impact, safe action, full decision payload |
| `rule_evaluations` | Which rule matched and with what input signals |
| `alembic_version` | Tracks current migration version |

### Main relationship model

```text
incidents
    ├── signals
    ├── evidence_items
    ├── decisions
    └── rule_evaluations
```

### Incident status lifecycle

```text
detected → resolved
```

When an incident is persisted:

```text
status = detected
resolved_at = null
```

When an incident is resolved:

```text
status = resolved
resolved_at = timestamp
```

---

## 6. PostgreSQL Commands Cheat Sheet

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
LIMIT 5;
```

Check decisions:

```sql
SELECT root_cause_category, confidence, safe_action_summary, created_at
FROM decisions
ORDER BY created_at DESC
LIMIT 5;
```

Check stored signals:

```sql
SELECT source, name, value, meaning, collected_at
FROM signals
ORDER BY collected_at DESC
LIMIT 30;
```

Check evidence:

```sql
SELECT source, category, summary, payload, created_at
FROM evidence_items
ORDER BY created_at DESC
LIMIT 30;
```

Check rule evaluations:

```sql
SELECT rule_id, matched, confidence, reason, created_at
FROM rule_evaluations
ORDER BY created_at DESC
LIMIT 10;
```

Count all records:

```sql
SELECT COUNT(*) FROM incidents;
SELECT COUNT(*) FROM decisions;
SELECT COUNT(*) FROM signals;
SELECT COUNT(*) FROM evidence_items;
SELECT COUNT(*) FROM rule_evaluations;
```

Clean all incident data:

```sql
DELETE FROM rule_evaluations;
DELETE FROM decisions;
DELETE FROM evidence_items;
DELETE FROM signals;
DELETE FROM incidents;
```

Exit PostgreSQL:

```sql
\q
```

---

## 7. Alembic Design

Alembic is used for **versioned schema management**.

Before Alembic, tables were created with:

```python
Base.metadata.create_all(bind=engine)
```

After Phase 17C, the professional workflow is:

```text
Change SQLAlchemy model
        ↓
alembic revision --autogenerate -m "describe change"
        ↓
review migration file
        ↓
alembic upgrade head
```

### Important Alembic files

| File | Purpose |
|---|---|
| `alembic.ini` | Alembic config |
| `alembic/env.py` | Connects Alembic to app settings and SQLAlchemy metadata |
| `alembic/versions/*.py` | Migration files |
| `alembic_version` table | Stores current applied migration |

### Apply migrations

```bash
alembic upgrade head
```

Or:

```bash
python scripts/init_db.py
```

### Check current migration

```bash
alembic current
```

### Show migration history

```bash
alembic history
```

### Generate new migration after model changes

```bash
alembic revision --autogenerate -m "describe schema change"
```

Always inspect generated migration before applying it.

---

## 8. Running the Platform Locally

From repo root:

```bash
cd /mnt/data/sre-decision-intelligence-platform
```

Activate venv if needed:

```bash
source ~/.venvs/sre-decision-intelligence-platform/bin/activate
```

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Check PostgreSQL container:

```bash
docker compose ps
```

Apply migrations:

```bash
alembic upgrade head
```

Run tests:

```bash
pytest
```

Start API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open API docs in browser:

```text
http://localhost:8000/docs
```

Check OpenAPI routes:

```bash
curl http://localhost:8000/openapi.json | jq '.paths | keys[]' | grep incidents
```

Expected important routes:

```text
/api/v1/incidents/frontend-availability
/api/v1/incidents/frontend-availability/live
/api/v1/incidents/frontend-availability/live/signals
/api/v1/incidents/frontend-availability/sample/persist
/api/v1/incidents/frontend-availability/live/persist
/api/v1/incidents/frontend-availability/live/resolve
/api/v1/incidents/history
/api/v1/incidents/open
/api/v1/incidents/resolved
/api/v1/incidents/{incident_db_id}
```

---

## 9. API Validation Cheat Sheet

### Health check

```bash
curl http://localhost:8000/health | jq
```

### DB health check

```bash
curl http://localhost:8000/health/db | jq
```

Expected:

```json
{
  "status": "ok",
  "database": "postgresql"
}
```

### Sample decision, no DB write

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability | jq
```

### Sample persist, writes demo data

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/sample/persist | jq
```

Use this only for testing persistence without breaking Kubernetes.

### Live signals, no DB write

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

Healthy expected example:

```json
{
  "probe_success": 1.0,
  "frontend_endpoints": "10.244.8.229:8080",
  "frontend_pod_ready": true
}
```

Broken expected example:

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

### Live persist, writes only when rule matches

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/persist | jq
```

Healthy expected response:

```json
{
  "detail": {
    "message": "No matching live incident rule found. Nothing was persisted.",
    "reason": "No matching rule found for provided signals"
  }
}
```

Broken expected response:

```text
HTTP 200 with DecisionResponse JSON
```

### Resolve incident after recovery

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/resolve | jq
```

Expected when recovered and open incident exists:

```json
{
  "status": "resolved",
  "incident_id": "frontend-availability-breach",
  "service": "frontend",
  "namespace": "fintech-workload",
  "resolved_at": "..."
}
```

Expected when no open incident exists:

```json
{
  "detail": {
    "message": "No open frontend availability incident found to resolve."
  }
}
```

### Query history

```bash
curl http://localhost:8000/api/v1/incidents/history | jq
```

### Query open incidents

```bash
curl http://localhost:8000/api/v1/incidents/open | jq
```

### Query resolved incidents

```bash
curl http://localhost:8000/api/v1/incidents/resolved | jq
```

### Query one incident detail

First get an ID:

```bash
curl http://localhost:8000/api/v1/incidents/history | jq '.[0].id'
```

Then:

```bash
curl http://localhost:8000/api/v1/incidents/<PASTE_ID_HERE> | jq
```

Expected detail includes:

```text
signals
evidence
decisions
rule_evaluations
```

---

## 10. Controlled Break/Fix Exercise

This is the most important end-to-end validation exercise.

### Step 1: Clean database

```bash
docker exec -it sre-decision-postgres psql -U sre -d sre_decision_intelligence
```

```sql
DELETE FROM rule_evaluations;
DELETE FROM decisions;
DELETE FROM evidence_items;
DELETE FROM signals;
DELETE FROM incidents;
\q
```

### Step 2: Confirm healthy frontend

```bash
kubectl get endpoints frontend -n fintech-workload
kubectl get pods -n fintech-workload -l app=frontend
```

Expected:

```text
frontend   10.x.x.x:8080
frontend-...   1/1 Running
```

### Step 3: Confirm healthy API signals

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

Expected:

```text
probe_success = 1.0
frontend_endpoints != none
frontend_pod_ready = true
```

### Step 4: Confirm healthy state does not persist incident

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/persist | jq
```

Expected:

```text
404 No matching live incident rule found. Nothing was persisted.
```

Check DB:

```bash
docker exec -it sre-decision-postgres psql -U sre -d sre_decision_intelligence
```

```sql
SELECT COUNT(*) FROM incidents;
SELECT COUNT(*) FROM decisions;
\q
```

Expected:

```text
0
0
```

### Step 5: Break the frontend Service selector

This adds a selector that the frontend pod does not have:

```bash
kubectl patch svc frontend -n fintech-workload \
  --type='merge' \
  -p '{"spec":{"selector":{"app":"frontend","application":"bank-of-anthos","environment":"development","team":"frontend","tier":"web","slo-test":"broken"}}}'
```

### Step 6: Verify Service endpoints are gone

```bash
kubectl get endpoints frontend -n fintech-workload
```

Expected:

```text
frontend   <none>
```

Pod should still be healthy:

```bash
kubectl get pods -n fintech-workload -l app=frontend
```

Expected:

```text
frontend-...   1/1 Running
```

### Step 7: Wait for Prometheus probe

```bash
sleep 60
```

### Step 8: Validate live broken signals

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

Expected:

```text
probe_success = 0.0
frontend_endpoints = none
frontend_pod_ready = true
```

### Step 9: Persist live incident

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/persist | jq
```

Expected:

```text
HTTP 200 with DecisionResponse
```

### Step 10: Validate DB detected incident

```bash
docker exec -it sre-decision-postgres psql -U sre -d sre_decision_intelligence
```

```sql
SELECT incident_id, service, namespace, status, created_at, resolved_at
FROM incidents
ORDER BY created_at DESC
LIMIT 5;
```

Expected:

```text
frontend-availability-breach | frontend | fintech-workload | detected | timestamp | null
```

Exit:

```sql
\q
```

### Step 11: Validate query APIs

```bash
curl http://localhost:8000/api/v1/incidents/open | jq
curl http://localhost:8000/api/v1/incidents/history | jq
```

Expected:

```text
One detected/open incident
```

### Step 12: Restore Service selector

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

### Step 13: Verify endpoints recovered

```bash
kubectl get endpoints frontend -n fintech-workload
```

Expected:

```text
frontend   10.x.x.x:8080
```

Wait for probe recovery:

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

### Step 15: Validate DB resolved state

```bash
docker exec -it sre-decision-postgres psql -U sre -d sre_decision_intelligence
```

```sql
SELECT incident_id, service, namespace, status, created_at, resolved_at
FROM incidents
ORDER BY created_at DESC
LIMIT 5;
```

Expected:

```text
frontend-availability-breach | frontend | fintech-workload | resolved | created_at | resolved_at
```

### Step 16: Validate resolution evidence

```sql
SELECT source, category, summary, payload, created_at
FROM evidence_items
ORDER BY created_at DESC
LIMIT 10;
```

Expected resolution evidence:

```text
source = live-collector
category = resolution
summary = Frontend service recovery confirmed from live signals
payload includes probe_success=1.0 and frontend_endpoints != none
```

Exit:

```sql
\q
```

### Step 17: Validate open and resolved APIs

```bash
curl http://localhost:8000/api/v1/incidents/open | jq
```

Expected:

```json
[]
```

```bash
curl http://localhost:8000/api/v1/incidents/resolved | jq
```

Expected:

```text
One resolved incident
```

---

## 11. Rule Logic Cheat Sheet

The current selector mismatch rule matches when:

```text
probe_success = 0
frontend_endpoints = none
frontend_pod_ready = true
```

Interpretation:

```text
The user path is broken.
The frontend Service has no backend endpoints.
The frontend pod is still healthy.
Therefore the likely root cause is service routing / selector mismatch.
```

Why not require `alert_state = pending` yet?

Because alerts can lag. The failure can be real before the alert enters pending/firing state.

Better future improvement:

```text
Add support for comparison operators:
frontend_availability_5m < 0.99
```

But current v1 rule is valid for controlled selector mismatch detection.

---

## 12. Common Troubleshooting

### Problem: `kubectl` command fails inside PostgreSQL

Symptom:

```text
sre_decision_intelligence=# kubectl get endpoints frontend -n fintech-workload
ERROR: syntax error at or near "kubectl"
```

Cause:

You are inside the PostgreSQL prompt.

Fix:

```sql
\q
```

Then run `kubectl` from Linux shell.

---

### Problem: API returns `Not Found` for a route

Check registered routes:

```bash
curl http://localhost:8000/openapi.json | jq '.paths | keys[]' | grep incidents
```

If route is missing, check:

```bash
grep -n "live/resolve\|history\|open\|resolved" app/api/v1/incidents.py
```

Restart uvicorn:

```bash
pkill -f "uvicorn app.main:app"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### Problem: FastAPI route exists in file but not in OpenAPI

Cause:

Old uvicorn process still running or server not reloaded.

Fix:

```bash
ps aux | grep uvicorn
pkill -f "uvicorn app.main:app"
ss -ltnp | grep 8000 || echo "port 8000 free"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### Problem: Circular import in `incidents.py`

Bad import:

```python
from app.api.v1.incidents import incident_to_detail, incident_to_summary
```

Correct import:

```python
from app.api.v1.incident_presenters import incident_to_detail, incident_to_summary
```

---

### Problem: `NameError: UUID is not defined`

Cause:

Route uses:

```python
incident_db_id: UUID
```

but file is missing:

```python
from uuid import UUID
```

Fix:

Add this import at top of `app/api/v1/incidents.py`:

```python
from uuid import UUID
```

---

### Problem: `Incident has no attribute evidence`

Bad repository code:

```python
selectinload(Incident.evidence)
selectinload(Incident.actions)
```

Correct relationship names:

```python
selectinload(Incident.signals)
selectinload(Incident.evidence_items)
selectinload(Incident.decisions)
selectinload(Incident.rule_evaluations)
```

Check:

```bash
grep -n "Incident.evidence)\|Incident.actions" app/db/repository.py
```

Expected:

```text
no output
```

---

### Problem: DB rows appear after tests

Tests that persist data must clean up after themselves.

Helper:

```python
from sqlalchemy import text
from app.db.session import engine


def clean_decision_tables() -> None:
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM rule_evaluations"))
        connection.execute(text("DELETE FROM decisions"))
        connection.execute(text("DELETE FROM evidence_items"))
        connection.execute(text("DELETE FROM signals"))
        connection.execute(text("DELETE FROM incidents"))
```

Use before and after DB-writing tests.

---

### Problem: Healthy state still shows old incident in DB

This is usually historical data, not a new live write.

Check whether count increases after calling `/live/persist`.

Before:

```sql
SELECT COUNT(*) FROM incidents;
```

Call:

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/persist | jq
```

After:

```sql
SELECT COUNT(*) FROM incidents;
```

If count does not increase, live persist is behaving correctly.

---

## 13. Test Suite Cheat Sheet

Run all tests:

```bash
pytest
```

Run query API tests:

```bash
pytest app/tests/test_incident_query_api.py -q
```

Run resolution tests:

```bash
pytest app/tests/test_incident_resolution.py -q
```

Run repository tests:

```bash
pytest app/tests/test_repository.py -q
```

Run migration tests:

```bash
pytest app/tests/test_migrations.py -q
```

Expected after Phase 17E:

```text
all tests passed
```

Warnings about `datetime.utcnow()` and `httpx`/Starlette are not blocking. They can be cleaned later.

---

## 14. Full Phase 17 Validation Checklist

Use this checklist before moving to Phase 18.

### Database

```bash
docker compose ps
alembic current
alembic upgrade head
curl http://localhost:8000/health/db | jq
```

Expected:

```text
Postgres running
Alembic at head
DB health ok
```

### API route registration

```bash
python - <<'PY'
from app.main import app

for route in app.routes:
    if "/api/v1/incidents" in route.path:
        print(route.path, route.methods)
PY
```

Expected routes include:

```text
/live/persist
/live/resolve
/history
/open
/resolved
/{incident_db_id}
```

### Tests

```bash
pytest
```

Expected:

```text
all passed
```

### Healthy no-write test

```bash
curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/persist | jq
```

Expected:

```text
No matching live incident rule found. Nothing was persisted.
```

### Broken persist test

```bash
kubectl patch svc frontend -n fintech-workload \
  --type='merge' \
  -p '{"spec":{"selector":{"app":"frontend","application":"bank-of-anthos","environment":"development","team":"frontend","tier":"web","slo-test":"broken"}}}'

sleep 60

curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/persist | jq
```

Expected:

```text
DecisionResponse persisted
```

### Restore resolve test

```bash
kubectl patch svc frontend -n fintech-workload \
  --type='json' \
  -p='[
    {
      "op": "remove",
      "path": "/spec/selector/slo-test"
    }
  ]'

sleep 60

curl -X POST http://localhost:8000/api/v1/incidents/frontend-availability/live/resolve | jq
```

Expected:

```text
status = resolved
resolved_at populated
```

---

## 15. What Phase 17 Does Not Yet Do

Phase 17 does **not** yet implement a full event timeline.

It does not yet store separate lifecycle events like:

```text
detected
decision_created
safe_action_recommended
recovery_observed
resolved
```

It only stores:

```text
incident row
related signals
evidence items
decision row
rule evaluation row
resolution update on incident
resolution evidence item
```

This is why Phase 18 should add an `incident_events` table and a timeline API.

---

## 16. Phase 17 Completion Definition

Phase 17 is complete when:

```text
PostgreSQL runs locally
Alembic creates schema
DB health endpoint works
Live collectors return current signals
Sample persistence writes demo data
Live persistence writes only real matching incidents
Healthy state does not create incidents
Broken Service selector creates detected incident
Restored Service resolves incident
Resolution evidence is stored
History/open/resolved/detail APIs work
pytest passes
```

---

## 17. Recommended Commit for Phase 17E

```bash
git status
```

```bash
git add app/api/v1/incidents.py \
        app/api/v1/incident_presenters.py \
        app/db/repository.py \
        app/tests/test_incident_query_api.py
```

```bash
git commit -m "feat: add incident query APIs and resolution evidence"
git push
```

---

## 18. Next Phase Preview — Phase 18

Phase 18 should introduce a true timeline/event model:

```text
incident_events
    ├── detected
    ├── decision_created
    ├── safe_action_recommended
    ├── recovery_observed
    └── resolved
```

Then the platform can answer:

```text
When was the incident detected?
When was the decision created?
When was the safe action recommended?
When did recovery become visible?
When was the incident resolved?
How long did recovery take?
```

That is the next level of SRE decision intelligence.
