# Phase 21 — Scenario Registry

## Purpose

Phase 21 introduces the **Scenario Registry** for the SRE Decision Intelligence Platform.

Before this phase, the platform mainly understood one incident pattern through a hardcoded frontend availability flow:

```text
frontend-availability-breach
```

That was useful for proving the first complete vertical slice:

```text
collect signals
    ↓
evaluate rule
    ↓
produce decision
    ↓
persist incident
    ↓
show history and timeline
```

However, a real SRE Decision Intelligence Platform must support many known failure patterns, such as:

```text
frontend service selector mismatch
pod crashloop
image pull failure
failed scheduling
high 5xx rate
backend timeout
database error spike
node not ready
storage degradation
network drops
GitOps drift
```

The Scenario Registry answers one important question:

```text
What known incident patterns can this platform reason about?
```

---

## Conceptual Model

A **scenario** is not the incident record itself.

A scenario is a known failure pattern that the platform understands.

Example:

```text
Scenario:
Frontend Service Selector Mismatch

Meaning:
The frontend user path is unavailable because the Kubernetes Service selector does not match any ready frontend pod.

Required signals:
- probe_success
- frontend_endpoints
- frontend_pod_ready

Root cause category:
service-routing

Safe action:
Restore the frontend Service selector so it matches frontend pod labels.
```

The registry stores this kind of definition as structured data.

---

## Why This Phase Matters

Without a scenario registry, the project would grow like this:

```text
hardcoded frontend logic
hardcoded crashloop logic
hardcoded database logic
hardcoded network logic
hardcoded storage logic
```

That becomes difficult to maintain.

The better design is:

```text
Scenario Registry
    ↓
Scenario Definitions
    ↓
Rules
    ↓
Decision Engine
    ↓
Incident Decision
```

This allows the platform to move from a single scenario to a scenario catalog.

---

## Relationship to Other Phases

Phase 21 sits between the normalized signal model and the multi-rule engine.

```text
Phase 20 — Generic Normalized Signal Model
    ↓
Phase 21 — Scenario Registry
    ↓
Phase 22 — Multi-rule / Multi-scenario Rule Engine
    ↓
Phase 23 — Workload Incident Scenarios
    ↓
Phase 24 — Platform Incident Scenarios
```

Phase 20 defines the signal language.

Phase 21 defines the known scenario catalog.

Phase 22 lets the engine evaluate multiple rules across those scenarios.

---

## Target Package Structure

Phase 21 adds a new package:

```text
app/scenarios/
├── __init__.py
├── models.py
├── registry.py
└── frontend_availability.py
```

It also adds API schemas and routes:

```text
app/schemas/scenarios.py
app/api/v1/scenarios.py
```

And tests:

```text
app/tests/test_scenario_registry.py
app/tests/test_scenario_api.py
```

---

## Scenario Model

File:

```text
app/scenarios/models.py
```

Implementation:

```python
from enum import StrEnum

from pydantic import BaseModel, Field


class ScenarioDomain(StrEnum):
    WORKLOAD = "workload"
    PLATFORM = "platform"
    CORRELATION = "correlation"


class ScenarioStatus(StrEnum):
    ACTIVE = "active"
    EXPERIMENTAL = "experimental"
    DISABLED = "disabled"


class ScenarioDefinition(BaseModel):
    id: str = Field(..., description="Stable scenario identifier")
    name: str = Field(..., description="Human-readable scenario name")
    description: str = Field(..., description="What this scenario detects")
    domain: ScenarioDomain = Field(..., description="workload, platform, or correlation")
    status: ScenarioStatus = Field(default=ScenarioStatus.ACTIVE)

    required_signals: list[str] = Field(
        default_factory=list,
        description="Signals required for this scenario to be evaluated",
    )
    optional_signals: list[str] = Field(
        default_factory=list,
        description="Signals that improve confidence but are not mandatory",
    )

    root_cause_category: str = Field(..., description="Root cause category")
    safe_action_summary: str = Field(..., description="Recommended safe action")
    risk_level: str = Field(..., description="Risk level of the recommended action")

    tags: list[str] = Field(default_factory=list)
```

---

## Scenario Domains

The platform uses three scenario domains.

### 1. Workload

Workload scenarios describe application or user-path degradation.

Examples:

```text
frontend-high-5xx-rate
frontend-high-latency
transaction-error-spike
backend-timeout-spike
ledger-database-error-spike
```

These answer:

```text
Is the application failing for users?
```

### 2. Platform

Platform scenarios describe Kubernetes or infrastructure failures.

Examples:

```text
frontend-image-pull-backoff
frontend-failed-scheduling
node-not-ready
frontend-oom-killed
pvc-mount-failure
cilium-drop-spike
longhorn-volume-degraded
argocd-sync-drift
```

These answer:

```text
Is the platform contributing to the incident?
```

### 3. Correlation

Correlation scenarios combine workload impact and platform context.

Example:

```text
frontend-service-selector-mismatch
```

This answers:

```text
Is user impact explained by platform state?
```

---

## First Registered Scenario

File:

```text
app/scenarios/frontend_availability.py
```

Initial scenario:

```python
from app.scenarios.models import ScenarioDefinition, ScenarioDomain, ScenarioStatus


FRONTEND_SERVICE_SELECTOR_MISMATCH = ScenarioDefinition(
    id="frontend-service-selector-mismatch",
    name="Frontend Service Selector Mismatch",
    description=(
        "Detects when the Bank of Anthos frontend user path is unavailable "
        "because the Kubernetes frontend Service has no backend endpoints while "
        "the frontend pod remains ready."
    ),
    domain=ScenarioDomain.CORRELATION,
    status=ScenarioStatus.ACTIVE,
    required_signals=[
        "probe_success",
        "frontend_endpoints",
        "frontend_pod_ready",
    ],
    optional_signals=[
        "frontend_availability_5m",
        "alert_state",
        "frontend_pod_status",
        "frontend_logs",
        "frontend_error_log_count",
    ],
    root_cause_category="service-routing",
    safe_action_summary=(
        "Restore the frontend Service selector so it matches frontend pod labels"
    ),
    risk_level="low",
    tags=[
        "bank-of-anthos",
        "frontend",
        "kubernetes",
        "service",
        "slo",
        "routing",
    ],
)
```

---

## Scenario Registry

File:

```text
app/scenarios/registry.py
```

Implementation:

```python
from app.scenarios.frontend_availability import FRONTEND_SERVICE_SELECTOR_MISMATCH
from app.scenarios.models import ScenarioDefinition, ScenarioStatus


class ScenarioRegistry:
    def __init__(self, scenarios: list[ScenarioDefinition]) -> None:
        self._scenarios = {
            scenario.id: scenario
            for scenario in scenarios
        }

    def list_scenarios(
        self,
        include_disabled: bool = False,
    ) -> list[ScenarioDefinition]:
        scenarios = list(self._scenarios.values())

        if include_disabled:
            return scenarios

        return [
            scenario
            for scenario in scenarios
            if scenario.status != ScenarioStatus.DISABLED
        ]

    def get_scenario(self, scenario_id: str) -> ScenarioDefinition | None:
        return self._scenarios.get(scenario_id)

    def require_scenario(self, scenario_id: str) -> ScenarioDefinition:
        scenario = self.get_scenario(scenario_id)

        if scenario is None:
            raise KeyError(f"Scenario not found: {scenario_id}")

        return scenario

    def has_scenario(self, scenario_id: str) -> bool:
        return scenario_id in self._scenarios


scenario_registry = ScenarioRegistry(
    scenarios=[
        FRONTEND_SERVICE_SELECTOR_MISMATCH,
    ]
)
```

---

## Why Use a Registry Object?

The registry gives the platform one consistent way to access known scenarios.

It supports:

```text
list all scenarios
get one scenario by ID
check whether a scenario exists
hide disabled scenarios
raise an explicit error for missing scenarios
```

This is better than scattering scenario definitions across route files or rule-engine code.

---

## API Response Schema

File:

```text
app/schemas/scenarios.py
```

Implementation:

```python
from pydantic import BaseModel

from app.scenarios.models import ScenarioDomain, ScenarioStatus


class ScenarioResponse(BaseModel):
    id: str
    name: str
    description: str
    domain: ScenarioDomain
    status: ScenarioStatus
    required_signals: list[str]
    optional_signals: list[str]
    root_cause_category: str
    safe_action_summary: str
    risk_level: str
    tags: list[str]
```

This keeps the API response stable and clear.

---

## Scenario API Routes

File:

```text
app/api/v1/scenarios.py
```

Implementation:

```python
from fastapi import APIRouter, HTTPException

from app.scenarios.registry import scenario_registry
from app.schemas.scenarios import ScenarioResponse


router = APIRouter(
    prefix="/api/v1/scenarios",
    tags=["scenarios"],
)


@router.get("", response_model=list[ScenarioResponse])
def list_scenarios() -> list[dict]:
    scenarios = scenario_registry.list_scenarios()

    return [
        scenario.model_dump(mode="json")
        for scenario in scenarios
    ]


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: str) -> dict:
    scenario = scenario_registry.get_scenario(scenario_id)

    if scenario is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Scenario not found.",
                "scenario_id": scenario_id,
            },
        )

    return scenario.model_dump(mode="json")
```

---

## Registering the Scenario Router

File:

```text
app/main.py
```

Add import:

```python
from app.api.v1.scenarios import router as scenarios_router
```

Then register the router:

```python
app.include_router(scenarios_router)
```

The application should now expose:

```text
GET /api/v1/scenarios
GET /api/v1/scenarios/{scenario_id}
```

---

## API Endpoints Added

### List scenarios

```http
GET /api/v1/scenarios
```

Example response:

```json
[
  {
    "id": "frontend-service-selector-mismatch",
    "name": "Frontend Service Selector Mismatch",
    "description": "Detects when the Bank of Anthos frontend user path is unavailable because the Kubernetes frontend Service has no backend endpoints while the frontend pod remains ready.",
    "domain": "correlation",
    "status": "active",
    "required_signals": [
      "probe_success",
      "frontend_endpoints",
      "frontend_pod_ready"
    ],
    "optional_signals": [
      "frontend_availability_5m",
      "alert_state",
      "frontend_pod_status",
      "frontend_logs",
      "frontend_error_log_count"
    ],
    "root_cause_category": "service-routing",
    "safe_action_summary": "Restore the frontend Service selector so it matches frontend pod labels",
    "risk_level": "low",
    "tags": [
      "bank-of-anthos",
      "frontend",
      "kubernetes",
      "service",
      "slo",
      "routing"
    ]
  }
]
```

### Get one scenario

```http
GET /api/v1/scenarios/frontend-service-selector-mismatch
```

Expected response:

```json
{
  "id": "frontend-service-selector-mismatch",
  "name": "Frontend Service Selector Mismatch",
  "domain": "correlation",
  "status": "active",
  "root_cause_category": "service-routing",
  "risk_level": "low"
}
```

### Unknown scenario

```http
GET /api/v1/scenarios/unknown-scenario
```

Expected response:

```json
{
  "detail": {
    "message": "Scenario not found.",
    "scenario_id": "unknown-scenario"
  }
}
```

---

## Testing the Registry

File:

```text
app/tests/test_scenario_registry.py
```

Implementation:

```python
from app.scenarios.registry import scenario_registry


def test_scenario_registry_contains_frontend_selector_mismatch():
    scenario = scenario_registry.get_scenario("frontend-service-selector-mismatch")

    assert scenario is not None
    assert scenario.id == "frontend-service-selector-mismatch"
    assert scenario.root_cause_category == "service-routing"
    assert "probe_success" in scenario.required_signals
    assert "frontend_endpoints" in scenario.required_signals
    assert "frontend_pod_ready" in scenario.required_signals


def test_scenario_registry_lists_active_scenarios():
    scenarios = scenario_registry.list_scenarios()

    scenario_ids = {scenario.id for scenario in scenarios}

    assert "frontend-service-selector-mismatch" in scenario_ids
```

Run:

```bash
pytest app/tests/test_scenario_registry.py -q
```

Expected:

```text
2 passed
```

---

## Testing the API

File:

```text
app/tests/test_scenario_api.py
```

Implementation:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_scenarios_endpoint_returns_frontend_selector_mismatch():
    response = client.get("/api/v1/scenarios")

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)
    assert len(body) >= 1

    scenario_ids = {scenario["id"] for scenario in body}

    assert "frontend-service-selector-mismatch" in scenario_ids


def test_get_scenario_endpoint_returns_scenario_detail():
    response = client.get("/api/v1/scenarios/frontend-service-selector-mismatch")

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == "frontend-service-selector-mismatch"
    assert body["root_cause_category"] == "service-routing"
    assert "probe_success" in body["required_signals"]
    assert "frontend_endpoints" in body["required_signals"]


def test_get_unknown_scenario_returns_404():
    response = client.get("/api/v1/scenarios/unknown-scenario")

    assert response.status_code == 404

    body = response.json()

    assert body["detail"]["message"] == "Scenario not found."
    assert body["detail"]["scenario_id"] == "unknown-scenario"
```

Run:

```bash
pytest app/tests/test_scenario_api.py -q
```

Expected:

```text
3 passed
```

---

## Manual Validation

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

List scenarios:

```bash
curl http://localhost:8000/api/v1/scenarios | jq
```

Expected:

```text
frontend-service-selector-mismatch is returned
```

Get one scenario:

```bash
curl http://localhost:8000/api/v1/scenarios/frontend-service-selector-mismatch | jq
```

Expected important values:

```json
{
  "id": "frontend-service-selector-mismatch",
  "domain": "correlation",
  "status": "active",
  "root_cause_category": "service-routing",
  "risk_level": "low"
}
```

Check OpenAPI paths:

```bash
curl http://localhost:8000/openapi.json | jq '.paths | keys[]' | grep scenarios
```

Expected:

```text
"/api/v1/scenarios"
"/api/v1/scenarios/{scenario_id}"
```

---

## Phase 21 Validation Checklist

Phase 21 is complete when all of the following are true:

```text
ScenarioDefinition model exists
ScenarioDomain enum exists
ScenarioStatus enum exists
ScenarioRegistry exists
frontend-service-selector-mismatch is registered
GET /api/v1/scenarios works
GET /api/v1/scenarios/{scenario_id} works
unknown scenario returns 404
scenario registry tests pass
scenario API tests pass
OpenAPI shows scenario routes
```

---

## Naming Decision: Scenario ID vs Rule ID

This phase introduces an important design distinction.

There are two possible naming models.

### Option A — Scenario ID equals Rule ID

```text
scenario_id = frontend-service-selector-mismatch
rule_id     = frontend-service-selector-mismatch
```

This is simple but less flexible.

### Option B — Scenario and rule are separate

```text
scenario_id = frontend-availability-breach
rule_id     = frontend-service-selector-mismatch
```

This is more accurate long-term.

Why?

One scenario can have multiple possible root causes.

Example:

```text
Scenario:
frontend-availability-breach

Rules:
frontend-service-selector-mismatch
frontend-pod-crashloop
frontend-image-pull-backoff
frontend-network-policy-block
frontend-high-5xx-rate
```

Recommended long-term model:

```text
scenario_id = user-visible incident class
rule_id     = specific root-cause detection rule
```

This distinction becomes important in Phase 22.

---

## How Phase 21 Prepares Phase 22

Phase 21 defines the scenario catalog.

Phase 22 makes the rule engine evaluate multiple rules.

Together:

```text
Scenario Registry
    ↓
Rule Files
    ↓
MultiRuleEngine
    ↓
Best Matching Decision
```

The Scenario Registry gives context.

The Rule Engine performs matching.

The Decision API exposes the result.

---

## Common Issues

### 1. Scenario router not found

If this command returns nothing:

```bash
curl http://localhost:8000/openapi.json | jq '.paths | keys[]' | grep scenarios
```

Check that `app/main.py` includes:

```python
from app.api.v1.scenarios import router as scenarios_router
app.include_router(scenarios_router)
```

### 2. Scenario import error

If the registry fails to import, check:

```bash
python - <<'PY'
from app.scenarios.registry import scenario_registry
print(scenario_registry.list_scenarios())
PY
```

If this fails, inspect:

```text
app/scenarios/frontend_availability.py
app/scenarios/registry.py
```

### 3. Scenario ID mismatch

If tests fail because a scenario cannot be found, confirm the ID is exactly:

```text
frontend-service-selector-mismatch
```

Scenario IDs should be stable and lowercase with hyphens.

---

## Commit

After validation:

```bash
git status
```

Add files:

```bash
git add app/scenarios \
        app/schemas/scenarios.py \
        app/api/v1/scenarios.py \
        app/main.py \
        app/tests/test_scenario_registry.py \
        app/tests/test_scenario_api.py
```

Commit:

```bash
git commit -m "feat: add scenario registry"
```

Push:

```bash
git push
```

---

## Outcome

Before Phase 21:

```text
The platform understood one scenario mostly through hardcoded frontend-specific logic.
```

After Phase 21:

```text
The platform has a queryable scenario catalog.
```

This is the foundation for:

```text
multi-rule evaluation
workload incident scenarios
platform incident scenarios
generic evaluate/persist/resolve APIs
```

