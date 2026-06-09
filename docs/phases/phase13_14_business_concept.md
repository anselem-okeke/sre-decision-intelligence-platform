# Business and Technical Explanation

## SRE Decision Intelligence Platform

This document explains the purpose, business value, and technical concept behind Phase 13 and Phase 14 of the SRE Decision Intelligence Platform.

It is written as a project explanation document, not as implementation documentation.

---

## 1. Executive Summary

Modern observability stacks can detect that something is wrong, but they often do not explain what the engineer should understand next.

Prometheus can show that an SLO is breached.  
OpenSearch can show application logs.  
Kubernetes can show pod, service, and endpoint state.  
Grafana can visualize metrics and dashboards.

But during an incident, the engineer still has to manually connect these signals.

The SRE Decision Intelligence Platform is designed to fill that gap.

It sits above the observability stack and converts fragmented signals into actionable incident context:

```text
What is impacted?
What evidence supports the alert?
What is the likely root cause?
What action is safe now?
```

Phase 13 and Phase 14 created the first application foundation for this platform.

---

## 2. Business Problem

### 2.1 Monitoring detects symptoms, not decisions

Traditional monitoring tools are very good at collecting and displaying signals.

For example:

```text
probe_success = 0
availability = 0.7
alert = pending
```

These signals tell the team that something is wrong.

But they do not automatically explain:

- whether users are affected
- whether the pod crashed
- whether the service path is broken
- whether the root cause is networking, deployment, application, or routing
- what evidence supports the diagnosis
- what remediation action is safe

In real incident response, this creates a gap between detection and decision-making.

---

### 2.2 The cost of fragmented incident response

When signals are fragmented across different tools, engineers lose time switching context.

A typical incident may require checking:

- Prometheus for metrics and SLOs
- Kubernetes for pods, services, endpoints, and labels
- OpenSearch for logs
- Argo CD for deployment and sync state
- Grafana dashboards for visual correlation
- terminal commands for live validation

Each tool has part of the truth.

No single tool explains the full incident story.

This increases:

- mean time to detection
- mean time to understanding
- mean time to recovery
- operational stress
- dependency on senior engineers
- risk of wrong remediation

The platform is designed to reduce that uncertainty.

---

## 3. What Problem This Platform Solves

The SRE Decision Intelligence Platform solves the problem of translating raw observability data into decision-ready incident context.

It does not replace existing tools.

Instead, it uses them as signal sources.

```text
Prometheus     → SLO and metric evidence
OpenSearch     → log evidence
Kubernetes API → runtime and routing evidence
Argo CD        → deployment/change evidence later
PostgreSQL     → decision history later
```

The platform adds a reasoning layer above these systems.

Its output is not just another alert.

Its output is an explanation.

Example:

```json
{
  "impact": "Frontend endpoint unavailable",
  "evidence": [
    "probe_success dropped to 0",
    "frontend Service endpoints became empty",
    "frontend pod remained 1/1 Running"
  ],
  "likely_root_cause": "Frontend Service selector mismatch",
  "safe_action": "Restore the frontend Service selector"
}
```

This is the core value of the system.

---

## 4. First Validated Incident Scenario

The first validated scenario is based on a controlled Kubernetes incident in the Bank of Anthos workload.

The failure mode:

```text
The frontend pod was still running,
but the frontend Service had no endpoints.
```

Evidence:

```text
Frontend pod: 1/1 Running
Frontend Service endpoints: <none>
Prometheus probe_success: 0
SLO availability: 0.7
```

This is important because many teams rely heavily on pod health.

But pod health is not the same as user availability.

A pod can be running while the application path is unavailable to users.

In this scenario, the issue was not a pod crash.

The likely root cause was a Service selector mismatch.

---

## 5. Why This Scenario Matters

This scenario is valuable because it demonstrates a real platform engineering problem:

```text
Infrastructure object exists,
but the user-facing path is broken.
```

From one view, the platform may look healthy:

```text
Pod: Running
Restart count: 0
Deployment: Available
```

From another view, the user path is broken:

```text
Service endpoints: <none>
probe_success = 0
availability = 0.7
```

This distinction is critical in production systems.

A healthy Kubernetes object does not always mean a healthy user experience.

The platform is designed to connect both views and produce a decision.

---

## 6. Business Value

### 6.1 Faster incident understanding

The platform reduces the time engineers spend manually correlating metrics, logs, and Kubernetes state.

Instead of starting with a raw alert, the engineer receives structured context:

- impact
- evidence
- likely root cause
- safe action

This improves response speed.

---

### 6.2 Lower operational risk

During incidents, wrong remediation can make the situation worse.

For example, if the pod is healthy but the Service has no endpoints, restarting the pod may not solve the problem.

A better action is to inspect and restore the Service selector.

The platform helps guide safer decisions.

---

### 6.3 Better SRE and platform engineering maturity

The platform supports a more mature operating model:

```text
Alerting → Evidence → Correlation → Decision → Action
```

This moves the organization away from reactive alert handling and toward structured incident response.

---

### 6.4 Better knowledge transfer

The platform captures reasoning in a repeatable format.

This helps less experienced engineers understand incidents faster.

It also reduces dependency on tribal knowledge.

---

### 6.5 Portfolio and enterprise value

For a platform engineering portfolio, this project demonstrates:

- Kubernetes troubleshooting
- SLO-based incident detection
- observability architecture
- API design
- schema-driven contracts
- decision engine design
- production-style thinking
- business-oriented SRE value

It shows not only how to deploy tools, but how to turn signals into operational decisions.

---

## 7. Product Concept

The product concept is simple:

```text
Observability tools show data.
Decision Intelligence explains what the data means.
```

The platform receives or collects signals from multiple sources, normalizes them, correlates them, and produces a structured decision response.

High-level flow:

```text
SLO breach
    ↓
Collect evidence
    ↓
Normalize signals
    ↓
Correlate symptoms
    ↓
Evaluate rules
    ↓
Identify likely cause
    ↓
Recommend safe action
```

The first version starts small and deterministic.

It does not try to be a generic AI incident tool.

It focuses on trustworthy, explainable, rule-based reasoning.

---

## 8. FastAPI Skeleton

### 8.1 Purpose

Created the first working API service.

The goal was not to build the full decision engine yet.

The goal was to create the platform entry point:

```text
GET /health
GET /api/v1/incidents/frontend-availability
```

This allowed the project to move from documentation and GitOps evidence into a real application service.

---

### 8.2 Why FastAPI

FastAPI was selected because it provides:

- clean Python API development
- automatic OpenAPI documentation
- strong support for Pydantic models
- simple local development
- easy testing with pytest
- good fit for platform APIs

The platform needs to expose structured decision outputs.

FastAPI is a strong choice for that.

---

### 8.3 What Phase 13 Delivered

Phase 13 delivered:

```text
app/main.py
app/config.py
app/api/health.py
app/api/v1/incidents.py
app/tests/test_health.py
app/tests/test_incidents.py
pyproject.toml
```

The incident endpoint returns a static decision response based on the validated incident evidence.

This is intentional.

Before building live collectors, the team needs a stable response shape and a working API contract.

---

### 8.4 Why Static Response First

The static response is not the final product.

It is a controlled first step.

It allows the project to validate:

- API structure
- endpoint naming
- response format
- test setup
- OpenAPI documentation
- incident decision shape

This avoids building live integrations too early.

The architecture stays clean because each phase adds one layer at a time.

---

## 9. Pydantic Schemas

### 9.1 Purpose

This replaced raw dictionary responses with typed Pydantic schemas.

This is important because the platform output should behave like a contract.

Incident decisions should have a predictable structure.

Without schemas, the response can drift over time.

With schemas, the API becomes safer, more testable, and easier to document.

---

### 9.2 What is Delivered

This introduced schema files such as:

```text
app/schemas/signal.py
app/schemas/impact.py
app/schemas/root_cause.py
app/schemas/safe_action.py
app/schemas/decision.py
app/schemas/incident.py
```

These models define the shape of the decision response.

Main schema concept:

```text
DecisionResponse
 ├── impact
 ├── signals
 ├── evidence
 ├── likely_root_cause
 ├── safe_action
 └── metadata
```

---

### 9.3 Why Schemas Matter for the Business Model

The platform is valuable only if its output can be trusted.

A decision response must be consistent.

For example, dashboards, automation, CI pipelines, or future UI components may depend on fields such as:

```text
impact.summary
likely_root_cause.confidence
safe_action.summary
signals.prometheus
signals.kubernetes
```

Pydantic schemas make this structure explicit.

This supports:

- reliable API consumers
- clean documentation
- safer refactoring
- better tests
- future UI integration
- future PostgreSQL persistence

---

## 10. Current API Concept

The current API has two important endpoints.

### Health endpoint

Purpose:

```text
Confirm the platform API is running.
```

Example:

```http
GET /health
```

Expected response:

```json
{
  "status": "ok",
  "service": "SRE Decision Intelligence Platform",
  "version": "0.1.0",
  "environment": "local"
}
```

---

### Frontend availability incident endpoint

Purpose:

```text
Return decision context for the frontend availability breach scenario.
```

Example:

```http
GET /api/v1/incidents/frontend-availability
```

This endpoint represents the first decision output.

It describes:

- impacted service
- affected namespace
- severity
- SLO impact
- Prometheus signals
- Kubernetes signals
- OpenSearch context
- likely root cause
- safe action

This is the first product-facing version of the platform concept.

---

## 11. What the Current Version Does Not Do Yet

The current version does not yet:

- query Prometheus live
- query Kubernetes live
- query OpenSearch live
- store decisions in PostgreSQL
- evaluate YAML rules dynamically
- perform remediation
- authenticate users
- support multiple scenarios

This is expected.

This establish the API and schema contract before adding dynamic behavior.

---

## 12. Why This Architecture Is Professional

The architecture is professional because it separates concerns clearly.

```text
API layer         → exposes decision endpoints
Schema layer      → defines stable contracts
Collector layer   → will gather external signals later
Engine layer      → will reason over normalized signals
Database layer    → will persist decisions later
GitOps repo       → deploys the platform later
```

This avoids mixing application code with Kubernetes deployment manifests.

It also keeps the platform service independent from the GitOps repository.

---

## 13. How This Becomes a Product

The long-term product model is:

```text
A decision layer for SRE, DevOps, and platform teams.
```

Possible users:

- SRE teams
- DevOps teams
- platform engineering teams
- incident commanders
- operations teams
- engineering managers

Possible use cases:

- incident triage
- SLO breach explanation
- root cause hypothesis generation
- safe action recommendation
- post-incident evidence summary
- operational knowledge capture

The first version is a portfolio-grade implementation.

But the concept is enterprise-relevant because every organization running Kubernetes has the same problem:

```text
Too much telemetry.
Not enough decision context.
```

---

## 14. Outcome

At the end, the platform has:

- a working FastAPI application
- a health endpoint
- a frontend incident decision endpoint
- a typed Pydantic response model
- tests for health and incident response
- a clean foundation for the next phase

The project has now moved from documentation and observability evidence into a real application platform.

---

## 15. Next

The next phase is:

```text
Rule Engine v1
```

> The goal is to move from a static decision response to a rule-based decision engine.

Initial rule:

```text
IF probe_success = 0
AND frontend endpoints = none
AND frontend pod is running
THEN likely root cause = Service selector mismatch
```

This will turn the platform from a static API into the first version of an explainable decision engine.

---

## 16. Final Summary

> - This is to establish the first version of the SRE Decision Intelligence Platform as a structured, testable, and explainable API.

> - The platform’s business value is not collecting more data.

> - The business value is converting existing operational data into decisions.

```text
From alert noise
to incident context.

From scattered signals
to explained root cause.

From manual investigation
to guided safe action.
```
