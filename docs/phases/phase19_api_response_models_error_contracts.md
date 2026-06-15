# Phase 19 — API Response Models and Error Contracts

## Project

**SRE Decision Intelligence Platform**

## Phase Goal

Phase 19 strengthens the API contract by replacing loose Python `dict` / `list[dict]` responses with explicit **Pydantic response models**.

The platform already had working incident persistence, query APIs, resolution tracking, and timeline events. However, several endpoints returned unstructured dictionaries. That works locally, but it is weak for a real API because the response shape can drift without FastAPI or OpenAPI clearly exposing the contract.

Phase 19 makes the `/api/v1` incident API more stable, predictable, and professional.

---

## Why Phase 19 Matters

Before Phase 19, an endpoint could return data like this:

```python
def get_incident_history(...) -> list[dict]:
    ...
```

That means the API response is only informally defined. Clients, frontend tools, documentation, and future tests cannot rely strongly on a stable response schema.

After Phase 19, endpoints use explicit response models:

```python
@router.get("/history", response_model=list[IncidentSummaryResponse])
def get_incident_history(...) -> list[dict]:
    ...
```

This provides:

- stable API contracts
- better OpenAPI documentation
- stronger response validation
- cleaner client/frontend integration later
- reduced accidental response drift
- clearer separation between database models and API responses

---

## Versioning Decision

All changes remain under:

```text
/api/v1
```

Phase 19 does **not** require `/api/v2` because it is additive and stabilizing. The purpose is to define the response contracts more clearly without breaking the existing API design.

---

## Target Endpoints Hardened in Phase 19

The following endpoints should use explicit Pydantic response models:

```text
GET  /api/v1/incidents/history
GET  /api/v1/incidents/open
GET  /api/v1/incidents/resolved
GET  /api/v1/incidents/{incident_db_id}
GET  /api/v1/incidents/{incident_db_id}/timeline
POST /api/v1/incidents/frontend-availability/live/resolve
```

These endpoints represent the query and lifecycle side of the incident API.

---

## Main Files Added or Updated

```text
app/schemas/incident_history.py
app/api/v1/incident_presenters.py
app/api/v1/incidents.py
app/tests/test_incident_response_schemas.py
```

---

# 1. Response Schema File

## File

```text
app/schemas/incident_history.py
```

## Purpose

This file defines API-facing response schemas for persisted incident history, details, timeline events, decisions, signals, evidence, rule evaluations, and resolution responses.

These schemas are separate from database models. The database model controls persistence; these response models control the API contract.

---

## Schema Definitions

```python
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class IncidentSummaryResponse(BaseModel):
    id: UUID
    incident_id: str
    service: str
    namespace: str
    severity: str
    status: str
    scenario: str
    created_at: datetime | None = None
    resolved_at: datetime | None = None


class IncidentSignalResponse(BaseModel):
    source: str
    name: str
    value: Any
    meaning: str
    collected_at: datetime | None = None


class IncidentEvidenceResponse(BaseModel):
    source: str
    category: str
    summary: str
    payload: Any = None
    created_at: datetime | None = None


class IncidentDecisionRecordResponse(BaseModel):
    impact_summary: str
    user_impact: str
    likely_root_cause: str
    root_cause_category: str
    confidence: str
    safe_action_summary: str
    safe_action_command: str | None = None
    created_at: datetime | None = None


class IncidentRuleEvaluationResponse(BaseModel):
    rule_id: str
    matched: bool
    confidence: str | None = None
    reason: str
    created_at: datetime | None = None


class IncidentTimelineEventResponse(BaseModel):
    event_type: str
    summary: str
    source: str
    payload: Any = None
    created_at: datetime | None = None


class IncidentDetailResponse(IncidentSummaryResponse):
    timeline: list[IncidentTimelineEventResponse]
    signals: list[IncidentSignalResponse]
    evidence: list[IncidentEvidenceResponse]
    decisions: list[IncidentDecisionRecordResponse]
    rule_evaluations: list[IncidentRuleEvaluationResponse]


class IncidentResolveResponse(BaseModel):
    status: str
    incident_id: str
    service: str
    namespace: str
    resolved_at: datetime | str | None = None


class ErrorDetailResponse(BaseModel):
    message: str
    reason: str | None = None


class ErrorResponse(BaseModel):
    detail: ErrorDetailResponse
```

---

## Key Schema Roles

| Schema | Purpose |
|---|---|
| `IncidentSummaryResponse` | Lightweight incident list item |
| `IncidentDetailResponse` | Full incident detail with timeline, signals, evidence, decisions, and rule evaluations |
| `IncidentTimelineEventResponse` | Timeline event response contract |
| `IncidentSignalResponse` | Persisted signal response contract |
| `IncidentEvidenceResponse` | Evidence item response contract |
| `IncidentDecisionRecordResponse` | Stored decision response contract |
| `IncidentRuleEvaluationResponse` | Stored rule evaluation response contract |
| `IncidentResolveResponse` | Response returned after resolving an incident |
| `ErrorResponse` | Structured error contract pattern |

---

# 2. Presenter Layer Update

## File

```text
app/api/v1/incident_presenters.py
```

## Purpose

The presenter converts SQLAlchemy database models into schema-compatible dictionaries.

This keeps route handlers simple and prevents database model details from leaking directly into API logic.

---

## Presenter Functions

```python
from app.db.models import Incident


def incident_to_summary(incident: Incident) -> dict:
    return {
        "id": incident.id,
        "incident_id": incident.incident_id,
        "service": incident.service,
        "namespace": incident.namespace,
        "severity": incident.severity,
        "status": incident.status,
        "scenario": incident.scenario,
        "created_at": incident.created_at,
        "resolved_at": incident.resolved_at,
    }


def incident_to_timeline_event(event) -> dict:
    return {
        "event_type": event.event_type,
        "summary": event.summary,
        "source": event.source,
        "payload": event.payload,
        "created_at": event.created_at,
    }


def incident_to_detail(incident: Incident) -> dict:
    return {
        **incident_to_summary(incident),
        "timeline": [
            incident_to_timeline_event(event)
            for event in sorted(incident.events, key=lambda item: item.created_at)
        ],
        "signals": [
            {
                "source": signal.source,
                "name": signal.name,
                "value": signal.value,
                "meaning": signal.meaning,
                "collected_at": signal.collected_at,
            }
            for signal in incident.signals
        ],
        "evidence": [
            {
                "source": evidence.source,
                "category": evidence.category,
                "summary": evidence.summary,
                "payload": evidence.payload,
                "created_at": evidence.created_at,
            }
            for evidence in incident.evidence_items
        ],
        "decisions": [
            {
                "impact_summary": decision.impact_summary,
                "user_impact": decision.user_impact,
                "likely_root_cause": decision.likely_root_cause,
                "root_cause_category": decision.root_cause_category,
                "confidence": decision.confidence,
                "safe_action_summary": decision.safe_action_summary,
                "safe_action_command": decision.safe_action_command,
                "created_at": decision.created_at,
            }
            for decision in incident.decisions
        ],
        "rule_evaluations": [
            {
                "rule_id": rule.rule_id,
                "matched": rule.matched,
                "confidence": rule.confidence,
                "reason": rule.reason,
                "created_at": rule.created_at,
            }
            for rule in incident.rule_evaluations
        ],
    }


def incident_timeline_to_response(incident: Incident) -> list[dict]:
    return [
        incident_to_timeline_event(event)
        for event in sorted(incident.events, key=lambda item: item.created_at)
    ]
```

---

## Design Note

The presenter returns dictionaries, not Pydantic objects directly.

This is okay because FastAPI applies the declared `response_model` and validates/serializes the final response.

This lets the route remain simple:

```python
return incident_to_detail(incident)
```

while the response contract remains strict:

```python
@router.get("/{incident_db_id}", response_model=IncidentDetailResponse)
```

---

# 3. Incident Route Updates

## File

```text
app/api/v1/incidents.py
```

## Required Imports

```python
from uuid import UUID

from app.schemas.incident_history import (
    IncidentDetailResponse,
    IncidentResolveResponse,
    IncidentSummaryResponse,
    IncidentTimelineEventResponse,
)
from app.api.v1.incident_presenters import (
    incident_timeline_to_response,
    incident_to_detail,
    incident_to_summary,
)
```

---

## History Endpoint

```python
@router.get("/history", response_model=list[IncidentSummaryResponse])
def get_incident_history(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    incidents = list_incidents(
        db=db,
        limit=limit,
    )

    return [incident_to_summary(incident) for incident in incidents]
```

---

## Open Incidents Endpoint

```python
@router.get("/open", response_model=list[IncidentSummaryResponse])
def get_open_incidents(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    incidents = list_incidents(
        db=db,
        status="detected",
        limit=limit,
    )

    return [incident_to_summary(incident) for incident in incidents]
```

---

## Resolved Incidents Endpoint

```python
@router.get("/resolved", response_model=list[IncidentSummaryResponse])
def get_resolved_incidents(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[dict]:
    incidents = list_incidents(
        db=db,
        status="resolved",
        limit=limit,
    )

    return [incident_to_summary(incident) for incident in incidents]
```

---

## Timeline Endpoint

```python
@router.get("/{incident_db_id}/timeline", response_model=list[IncidentTimelineEventResponse])
def get_incident_timeline(
    incident_db_id: UUID,
    db: Session = Depends(get_db),
) -> list[dict]:
    incident = get_incident_by_id(
        db=db,
        incident_db_id=incident_db_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Incident not found.",
                "incident_db_id": str(incident_db_id),
            },
        )

    return incident_timeline_to_response(incident)
```

---

## Detail Endpoint

```python
@router.get("/{incident_db_id}", response_model=IncidentDetailResponse)
def get_incident_detail(
    incident_db_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    incident = get_incident_by_id(
        db=db,
        incident_db_id=incident_db_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Incident not found.",
                "incident_db_id": str(incident_db_id),
            },
        )

    return incident_to_detail(incident)
```

---

## Resolve Endpoint Response Model

```python
@router.post(
    "/frontend-availability/live/resolve",
    response_model=IncidentResolveResponse,
)
def resolve_frontend_availability_live_incident(
    db: Session = Depends(get_db),
) -> dict:
    ...
```

The returned object should match:

```python
return {
    "status": "resolved",
    "incident_id": resolved_incident.incident_id,
    "service": resolved_incident.service,
    "namespace": resolved_incident.namespace,
    "resolved_at": resolved_incident.resolved_at,
}
```

Pydantic handles datetime serialization.

---

# 4. Route Ordering Rule

FastAPI route order matters when static paths and dynamic paths are mixed.

The correct order is:

```text
/history
/open
/resolved
/{incident_db_id}/timeline
/{incident_db_id}
```

Do not put this route too early:

```text
/{incident_db_id}
```

If it appears before `/history`, `/open`, or `/resolved`, FastAPI may treat those static words as path parameters.

---

# 5. OpenAPI Validation

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check that incident schemas are visible in OpenAPI:

```bash
curl http://localhost:8000/openapi.json | jq '.components.schemas | keys[]' | grep Incident
```

Expected examples:

```text
IncidentDetailResponse
IncidentSummaryResponse
IncidentTimelineEventResponse
IncidentResolveResponse
```

This confirms FastAPI sees the new response models.

---

# 6. Route Registration Validation

Run:

```bash
python - <<'PY'
from app.main import app

for route in app.routes:
    if "/api/v1/incidents" in route.path:
        print(route.path, route.methods)
PY
```

Expected relevant routes:

```text
/api/v1/incidents/history {'GET'}
/api/v1/incidents/open {'GET'}
/api/v1/incidents/resolved {'GET'}
/api/v1/incidents/{incident_db_id}/timeline {'GET'}
/api/v1/incidents/{incident_db_id} {'GET'}
```

---

# 7. Tests Added in Phase 19

## File

```text
app/tests/test_incident_response_schemas.py
```

## Purpose

This test file validates that the new Pydantic schemas accept the expected fields and nested sections.

---

## Test Content

```python
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.incident_history import (
    IncidentDetailResponse,
    IncidentSummaryResponse,
    IncidentTimelineEventResponse,
)


def test_incident_summary_response_accepts_expected_fields():
    response = IncidentSummaryResponse(
        id=uuid4(),
        incident_id="frontend-availability-breach",
        service="frontend",
        namespace="fintech-workload",
        severity="warning",
        status="detected",
        scenario="frontend-availability-breach",
        created_at=datetime.now(timezone.utc),
        resolved_at=None,
    )

    assert response.incident_id == "frontend-availability-breach"
    assert response.status == "detected"


def test_timeline_event_response_accepts_payload():
    response = IncidentTimelineEventResponse(
        event_type="incident_detected",
        summary="Incident detected for service frontend",
        source="decision-engine",
        payload={"service": "frontend"},
        created_at=datetime.now(timezone.utc),
    )

    assert response.event_type == "incident_detected"
    assert response.payload["service"] == "frontend"


def test_incident_detail_response_accepts_nested_sections():
    incident_id = uuid4()

    response = IncidentDetailResponse(
        id=incident_id,
        incident_id="frontend-availability-breach",
        service="frontend",
        namespace="fintech-workload",
        severity="warning",
        status="detected",
        scenario="frontend-availability-breach",
        created_at=datetime.now(timezone.utc),
        resolved_at=None,
        timeline=[],
        signals=[],
        evidence=[],
        decisions=[],
        rule_evaluations=[],
    )

    assert response.id == incident_id
    assert response.timeline == []
```

---

# 8. Test Commands

Run the new schema tests:

```bash
pytest app/tests/test_incident_response_schemas.py -q
```

Run query/timeline related tests:

```bash
pytest app/tests/test_incident_query_api.py -q
pytest app/tests/test_incident_timeline.py -q
```

Run the full suite:

```bash
pytest
```

Expected:

```text
all tests passed
```

Warnings are not blockers for this phase.

---

# 9. Manual API Validation

## History

```bash
curl http://localhost:8000/api/v1/incidents/history | jq
```

Expected shape:

```json
[
  {
    "id": "...",
    "incident_id": "frontend-availability-breach",
    "service": "frontend",
    "namespace": "fintech-workload",
    "severity": "warning",
    "status": "detected",
    "scenario": "frontend-availability-breach",
    "created_at": "...",
    "resolved_at": null
  }
]
```

---

## Detail

```bash
curl http://localhost:8000/api/v1/incidents/<INCIDENT_DB_ID> | jq
```

Expected top-level shape:

```json
{
  "id": "...",
  "incident_id": "frontend-availability-breach",
  "service": "frontend",
  "namespace": "fintech-workload",
  "severity": "warning",
  "status": "detected",
  "scenario": "frontend-availability-breach",
  "timeline": [],
  "signals": [],
  "evidence": [],
  "decisions": [],
  "rule_evaluations": []
}
```

---

## Timeline

```bash
curl http://localhost:8000/api/v1/incidents/<INCIDENT_DB_ID>/timeline | jq
```

Expected shape:

```json
[
  {
    "event_type": "incident_detected",
    "summary": "Incident detected for service frontend",
    "source": "decision-engine",
    "payload": {},
    "created_at": "..."
  }
]
```

---

# 10. Error Contract Pattern

Phase 19 also establishes the preferred error shape:

```json
{
  "detail": {
    "message": "Incident not found.",
    "incident_db_id": "..."
  }
}
```

A more formal reusable error model was defined:

```python
class ErrorDetailResponse(BaseModel):
    message: str
    reason: str | None = None


class ErrorResponse(BaseModel):
    detail: ErrorDetailResponse
```

FastAPI does not automatically enforce `ErrorResponse` unless it is declared in route `responses=...`, but Phase 19 introduces the structure for later hardening.

A future improvement can add:

```python
@router.get(
    "/{incident_db_id}",
    response_model=IncidentDetailResponse,
    responses={404: {"model": ErrorResponse}},
)
```

---

# 11. Success Criteria

Phase 19 is complete when:

```text
Incident response schemas exist
History endpoint uses response_model
Open endpoint uses response_model
Resolved endpoint uses response_model
Detail endpoint uses response_model
Timeline endpoint uses response_model
Resolve endpoint uses response_model
OpenAPI exposes Incident* schemas
Schema tests pass
Query/timeline tests pass
Full pytest passes
```

---

# 12. Commit

```bash
git status
```

Then:

```bash
git add app/schemas/incident_history.py \
        app/api/v1/incidents.py \
        app/api/v1/incident_presenters.py \
        app/tests/test_incident_response_schemas.py
```

If query or timeline tests were adjusted:

```bash
git add app/tests
```

Commit:

```bash
git commit -m "feat: add incident API response schemas"
git push
```

---

# 13. Architectural Result

Before Phase 19:

```text
API responses worked but were loosely defined.
```

After Phase 19:

```text
Incident API responses are explicit, validated, and visible in OpenAPI.
```

This phase prepares the API for later work:

```text
Phase 20 — Generic Normalized Signal Model
Phase 21 — Scenario Registry
Phase 22 — Multi-rule / Multi-scenario Rule Engine
Phase 25 — Generic Evaluate / Persist / Resolve API
```

---

# 14. Notes from Later Phases

Later phases introduced additional generic schemas such as:

```text
app/schemas/generic_incidents.py
app/schemas/scenarios.py
```

Those are separate from Phase 19. Phase 19 specifically focused on persisted incident query, detail, timeline, and resolution response contracts.

---

# End of Phase 19 Documentation
