# Project Overview

## Purpose

The SRE Decision Intelligence Platform is designed to convert observability data into actionable incident decisions.

Modern Kubernetes platforms generate large amounts of telemetry:

- metrics
- logs
- alerts
- events
- deployment state
- runtime state

However, during an incident, engineers still need to manually connect the dots.

This project focuses on that missing layer.

## Problem

Traditional monitoring can detect symptoms:

```text
probe_success = 0
availability = 0.7
alert = pending
```

But detection alone does not explain:

- why the incident happened
- whether users are affected
- whether the pod crashed
- whether the service path is broken
- whether there was a recent deployment
- what action is safe

## Solution

The platform correlates signals from multiple sources and produces a decision-ready incident summary.

```text
Prometheus     → SLO impact and metrics
OpenSearch     → workload and platform logs
Kubernetes API → services, endpoints, pods, labels
Argo CD        → GitOps/change context later
PostgreSQL     → stored incident decisions
```

## First scenario

The first validated scenario is a Bank of Anthos frontend availability breach.

The frontend pod remained healthy:

```text
Frontend pod: 1/1 Running
```

But the frontend Service had no endpoints:

```text
Frontend Service: endpoints <none>
```

Prometheus detected the user-facing failure:

```text
probe_success = 0
availability = 0.7
```

The likely root cause was a Service selector mismatch.

## Expected decision output

The platform should produce output like:

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

## Design principle

> The platform should not create more noise.

> It should reduce incident ambiguity.

> The goal is not another alert.

> The goal is the explanation behind the alert.
