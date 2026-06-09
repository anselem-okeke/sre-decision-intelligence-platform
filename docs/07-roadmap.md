# Roadmap

## Objective

This roadmap defines the implementation phases for the SRE Decision Intelligence Platform application repository.

The GitOps repository already validated the observability foundation and the first incident scenario.

This repository now focuses on building the application layer.

---

## Repository Boundary

### GitOps repository

```text
sre-decision-intelligence-gitops
```

Owns:

- Argo CD applications
- Kubernetes manifests
- Bank of Anthos workload
- Fluent Bit and OpenSearch deployment
- Blackbox Exporter probe
- PrometheusRule definitions
- incident evidence
- platform documentation

### Platform application repository

```text
sre-decision-intelligence-platform
```

Owns:

- FastAPI application
- collectors
- decision engine
- schemas
- PostgreSQL persistence
- tests
- Dockerfile
- local development setup

---

## Completed Foundation in GitOps Repository

The GitOps repository has already completed:

| Phase | Description | Status |
|---|---|---|
| 1 | Argo CD foundation | Complete |
| 2 | Bank of Anthos workload | Complete |
| 3 | Prometheus/Grafana baseline | Complete |
| 4 | Fluent Bit to OpenSearch | Complete |
| 5 | OpenSearch log investigation | Complete |
| 6 | Structured log parsing | Complete |
| 7 | Platform signal inventory | Complete |
| 8 | SLI/SLO discovery | Complete |
| 9 | Frontend probe SLO | Complete |
| 10 | Frontend availability breach scenario | Complete |
| 11 | Incident correlation evidence | Complete |

The first validated incident scenario is:

```text
Bank of Anthos frontend availability breach
```

---

## Application Roadmap

## Phase 12 — Architecture, Frameworks, and Project Structure

Status:

```text
In progress
```

Goal:

Define the platform application architecture before writing application logic.

Deliverables:

```text
README.md
docs/01-project-overview.md
docs/02-architecture.md
docs/03-frameworks.md
docs/04-api-contract.md
docs/05-decision-engine.md
docs/06-database-design.md
docs/07-roadmap.md
```

Success criteria:

- repo boundary is clear
- framework choices are documented
- API contract is defined
- decision engine design is documented
- PostgreSQL design is documented
- roadmap is documented

---

## Phase 13 — FastAPI Skeleton

Goal:

Create the first working FastAPI app.

Deliverables:

```text
app/main.py
app/api/health.py
app/api/v1/incidents.py
pyproject.toml
```

Initial endpoints:

```http
GET /health
GET /api/v1/incidents/frontend-availability
```

The frontend availability endpoint may return a static decision response based on Phase 10 and Phase 11 evidence.

Success criteria:

- FastAPI app starts locally
- `/health` returns OK
- OpenAPI docs are available
- frontend availability endpoint returns valid JSON

---

## Phase 14 — Pydantic Schemas

Goal:

Define stable response models.

Deliverables:

```text
app/schemas/signal.py
app/schemas/evidence.py
app/schemas/incident.py
app/schemas/decision.py
app/schemas/slo.py
```

Schemas:

```text
Signal
EvidenceItem
Impact
RootCause
SafeAction
Decision
IncidentResponse
```

Success criteria:

- API response uses Pydantic models
- response contract matches docs/04-api-contract.md
- tests validate schema output

---

## Phase 15 — Rule Engine v1

Goal:

Implement the first deterministic rule.

Initial rule:

```text
Service selector mismatch
```

Rule logic:

```text
IF probe_success = 0
AND frontend endpoints = empty
AND frontend pod is Running/Ready
THEN likely root cause = Service selector mismatch
```

Deliverables:

```text
app/rules/frontend_availability_breach.yaml
app/engine/signal_classifier.py
app/engine/correlator.py
app/engine/decision_engine.py
app/engine/safe_action_mapper.py
```

Success criteria:

- rule can be loaded from YAML
- rule can be evaluated against sample signals
- decision output is deterministic
- tests cover matched and non-matched cases

---

## Phase 16 — Live Collectors v1

Goal:

Replace static input with live signal collection.

Initial collectors:

```text
Prometheus collector
Kubernetes collector
OpenSearch collector
```

Deliverables:

```text
app/collectors/prometheus.py
app/collectors/kubernetes.py
app/collectors/opensearch.py
```

Collector responsibilities:

| Collector | Signals |
|---|---|
| Prometheus | `probe_success`, availability, alert state, pod metrics |
| Kubernetes | Service selector, endpoints, pod labels, pod status |
| OpenSearch | frontend logs, severity distribution, error context |

Success criteria:

- collectors can query configured endpoints
- collectors return normalized signal objects
- collector failures are handled safely
- tests mock external APIs

---

## Phase 17 — PostgreSQL Persistence

Goal:

Persist decisions and evidence snapshots.

Database:

```text
PostgreSQL only
```

Deliverables:

```text
app/db/base.py
app/db/session.py
app/db/models.py
app/db/repository.py
app/db/migrations/
```

Tables:

```text
incidents
signals
evidence_items
decisions
rule_evaluations
```

Success criteria:

- PostgreSQL runs with Docker Compose
- Alembic migrations create tables
- decision results can be saved
- decision history can be queried

---

## Phase 18 — Containerization and Local Runtime

Goal:

Run the platform application locally using Docker.

Deliverables:

```text
Dockerfile
docker-compose.yml
.env.example
scripts/run-local.sh
scripts/test.sh
```

Services:

```text
decision-intelligence-api
postgres
```

Success criteria:

- app builds as container image
- app starts with Docker Compose
- PostgreSQL starts with Docker Compose
- `/health` works from container
- tests run in local environment

---

## Phase 19 — GitOps Deployment

Goal:

Deploy the platform application into Kubernetes using the GitOps repository.

Work happens in:

```text
sre-decision-intelligence-gitops
```

Expected GitOps additions:

```text
platform/decision-intelligence/
argocd/applications/decision-intelligence-app.yaml
```

Success criteria:

- app image is deployed to Kubernetes
- Service exists
- health endpoint works in cluster
- Argo CD manages the app
- app can reach Prometheus/OpenSearch/Kubernetes APIs

---

## Phase 20 — Argo CD Change Context

Goal:

Add GitOps/change correlation.

Collector:

```text
Argo CD collector
```

Signals:

- application sync status
- health status
- revision
- recent sync
- out-of-sync state

Success criteria:

- incident decisions include change context
- rollout/regression scenarios can be detected

---

## Phase 21 — Additional Incident Scenarios

Goal:

Extend the platform beyond frontend Service selector mismatch.

Planned scenarios:

```text
pod crashloop
rollout regression
application error storm
network policy drop
node pressure
storage degradation
database dependency failure
```

Each scenario should include:

- controlled incident
- signal evidence
- decision rule
- safe action
- tests

---

## Phase 22 — UI / Dashboard Layer

Goal:

Optionally add a simple UI after the API is stable.

Possible tools:

```text
Streamlit
React
Grafana dashboard integration
```

This is not required for the first working backend version.

---

## Current Priority

The immediate next step after Phase 12 is:

```text
Phase 13 — FastAPI Skeleton
```

Focus:

```text
GET /health
GET /api/v1/incidents/frontend-availability
```

Do not add PostgreSQL or live collectors until the API contract and response schema are stable.
