# Database Design

## Objective

This document defines the database design for the SRE Decision Intelligence Platform.

The database stores incident decisions, collected signals, evidence snapshots, rule evaluations, and safe actions.

The project uses:

```text
PostgreSQL only
```

SQLite is not used.

---

## Why PostgreSQL

PostgreSQL is used because the platform should be designed like a production-grade service.

It provides:

- reliable persistence
- JSONB support for flexible evidence payloads
- relational modeling for incidents and decisions
- indexing for historical queries
- compatibility with SQLAlchemy and Alembic
- production-style local development with Docker Compose

---

## Initial Database Scope

The first database version should support storing:

- incidents
- signals
- evidence items
- decisions
- rule evaluations

The database is not required for the first static API response, but it should be part of the planned architecture.

Implementation should come after the API contract, schemas, and first decision engine version.

---

## Proposed Tables

```text
incidents
signals
evidence_items
decisions
rule_evaluations
```

---

## Table: incidents

Stores top-level incident records.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `incident_id` | text | External incident identifier |
| `service` | text | Affected service |
| `namespace` | text | Kubernetes namespace |
| `severity` | text | warning, critical, info |
| `status` | text | detected, investigating, resolved |
| `scenario` | text | Incident scenario name |
| `started_at` | timestamptz | Incident start time |
| `resolved_at` | timestamptz | Incident resolution time |
| `created_at` | timestamptz | Record creation time |
| `updated_at` | timestamptz | Last update time |

Example:

```text
incident_id = frontend-availability-breach
service = frontend
namespace = fintech-workload
severity = warning
status = detected
scenario = service-selector-mismatch
```

---

## Table: signals

Stores normalized signals collected from Prometheus, Kubernetes, OpenSearch, or Argo CD.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `incident_id` | UUID | Foreign key to incidents |
| `source` | text | prometheus, kubernetes, opensearch, argocd |
| `name` | text | Signal name |
| `value` | jsonb | Signal value |
| `meaning` | text | Human-readable meaning |
| `severity` | text | Optional signal severity |
| `collected_at` | timestamptz | Time signal was collected |
| `raw_payload` | jsonb | Optional raw source payload |

Example:

```json
{
  "source": "prometheus",
  "name": "probe_success",
  "value": 0,
  "meaning": "Frontend probe failed"
}
```

---

## Table: evidence_items

Stores evidence used by the decision engine.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `incident_id` | UUID | Foreign key to incidents |
| `source` | text | Evidence source |
| `category` | text | slo, pod, service, logs, deployment, network |
| `summary` | text | Human-readable evidence |
| `raw_reference` | text | Query, resource name, or external reference |
| `payload` | jsonb | Evidence payload |
| `created_at` | timestamptz | Record creation time |

Example:

```json
{
  "category": "service",
  "summary": "Frontend Service endpoints became empty",
  "payload": {
    "endpoints": "none"
  }
}
```

---

## Table: decisions

Stores final decision outputs.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `incident_id` | UUID | Foreign key to incidents |
| `impact_summary` | text | Impact summary |
| `user_impact` | text | User-facing impact |
| `likely_root_cause` | text | Root cause summary |
| `root_cause_category` | text | service-routing, pod-crash, rollout, network, storage |
| `confidence` | text | low, medium, high |
| `safe_action_summary` | text | Safe action |
| `safe_action_command` | text | Optional command |
| `decision_payload` | jsonb | Full decision response |
| `created_at` | timestamptz | Decision creation time |

Example:

```text
likely_root_cause = Frontend Service selector did not match frontend pod labels
root_cause_category = service-routing
confidence = high
safe_action_summary = Restore the frontend Service selector
```

---

## Table: rule_evaluations

Stores which rules were evaluated and whether they matched.

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `incident_id` | UUID | Foreign key to incidents |
| `rule_id` | text | Rule identifier |
| `matched` | boolean | Whether the rule matched |
| `confidence` | text | Rule confidence |
| `reason` | text | Explanation |
| `input_signals` | jsonb | Signals used during evaluation |
| `created_at` | timestamptz | Record creation time |

Example:

```json
{
  "rule_id": "frontend-service-selector-mismatch",
  "matched": true,
  "confidence": "high",
  "reason": "probe failed, endpoints empty, pod running"
}
```

---

## Relationship Model

```text
incident
   ├── signals
   ├── evidence_items
   ├── rule_evaluations
   └── decisions
```

One incident can have many signals, many evidence items, many rule evaluations, and one or more decisions.

---

## SQLAlchemy / Alembic Plan

Use SQLAlchemy models for:

```text
Incident
Signal
EvidenceItem
Decision
RuleEvaluation
```

Use Alembic for database migrations.

Initial migration:

```text
001_create_core_decision_tables
```

---

## Local Development Database

Use Docker Compose with PostgreSQL.

Example service:

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: sre_decision_intelligence
      POSTGRES_USER: sre
      POSTGRES_PASSWORD: sre_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

Application connection string:

```text
DATABASE_URL=postgresql+psycopg://sre:sre_password@localhost:5432/sre_decision_intelligence
```

---

## Database Implementation Phase

Database implementation belongs to:

```text
Phase 17 — PostgreSQL Persistence
```

Do not implement persistence before:

```text
Phase 13 — FastAPI Skeleton
Phase 14 — Pydantic Schemas
Phase 15 — Rule Engine v1
Phase 16 — Live Collectors v1
```

This keeps the project simple and avoids premature complexity.

---

## Design Rules

- Use PostgreSQL only.
- Store raw source payloads in JSONB when useful.
- Keep final decision output reproducible.
- Store enough evidence to explain why a decision was made.
- Do not store secrets.
- Do not store unnecessary high-volume telemetry.
- Store decision snapshots, not every metric sample.
