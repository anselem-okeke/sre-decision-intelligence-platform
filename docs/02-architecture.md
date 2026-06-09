# Architecture

![img](/img/decision-intelligence-arch.png)

## High-level architecture

```text
API request
   ↓
Incident Service
   ↓
Collectors
   ↓
Signal Classifier
   ↓
Correlator
   ↓
Decision Engine
   ↓
Safe Action Mapper
   ↓
PostgreSQL
   ↓
API response
```

## Signal flow

```text
Prometheus
  - probe_success
  - availability SLO
  - ALERTS
  - pod readiness
  - restart counts
  - deployment availability

OpenSearch
  - frontend logs
  - severity
  - message
  - timestamp
  - Kubernetes metadata

Kubernetes API
  - Service selector
  - Endpoints
  - Pod status
  - Pod labels
  - Deployment state

Argo CD later
  - sync status
  - health status
  - revision
  - recent deployment/change context
```

## First supported incident flow

```text
Frontend availability SLO breach
        ↓
Prometheus shows probe_success = 0
        ↓
Kubernetes shows frontend endpoints = <none>
        ↓
Kubernetes shows frontend pod = 1/1 Running
        ↓
OpenSearch shows no dominant frontend crash signal
        ↓
Decision Engine identifies Service selector mismatch
        ↓
API returns impact, evidence, root cause, and safe action
```

## Main components

### API layer

The API layer exposes endpoints for:

- health checks
- incidents
- decisions
- signals
- SLOs

Initial endpoint:

```http
GET /api/v1/incidents/frontend-availability
```

### Collectors

Collectors retrieve raw signals from external systems.

Initial collectors:

```text
Prometheus collector
OpenSearch collector
Kubernetes collector
```

Later collector:

```text
Argo CD collector
```

### Signal classifier

The signal classifier converts raw data into normalized signal objects.

Example:

```text
probe_success = 0
```

becomes:

```text
Signal type: availability_failure
Source: Prometheus
Severity: warning
Meaning: frontend probe failed
```

### Correlator

The correlator connects related signals.

Example:

```text
probe_success = 0
frontend endpoints = <none>
frontend pod = Running
```

This correlation suggests:

```text
Service path failure, not pod crash
```

### Decision engine

The decision engine evaluates rules and determines:

- impact
- likely root cause
- confidence
- safe action

### PostgreSQL

PostgreSQL stores:

- incidents
- signals
- evidence snapshots
- decisions
- rule evaluations

SQLite is not used in this project.

## Repository architecture

This repository owns application code only.

It does not own Kubernetes deployment manifests or observability infrastructure.

Deployment belongs to the GitOps repository.

```text
sre-decision-intelligence-gitops
```

Application logic belongs to this repository.

```text
sre-decision-intelligence-platform
```
