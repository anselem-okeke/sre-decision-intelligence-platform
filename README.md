# SRE Decision Intelligence Platform
![imge](/img/sre-decision-intelligence-architecure2.png)

![img](/img/decision-intelligence-monitor-small.gif)

The SRE Decision Intelligence Platform turns raw observability signals into actionable incident context.

It does not replace Prometheus, OpenSearch, Kubernetes, Argo CD, or Grafana.

It sits above them and answers the questions engineers need during incident response:

- What is impacted?
- What evidence supports the alert?
- What is the likely root cause?
- What action is safe now?

## Core idea

```text
SLO breach
    ↓
Collect evidence
    ↓
Correlate signals
    ↓
Explain likely root cause
    ↓
Recommend safe action
```

## First validated scenario

The first validated incident scenario is:

```text
Bank of Anthos frontend availability breach
```

In the [GitOps repository](https://github.com/anselem-okeke/sre-decision-intelligence-gitops), this scenario was validated with real signals:

```text
Frontend pod: 1/1 Running
Frontend Service endpoints: <none>
Prometheus probe_success: 0
SLO availability: 0.7
Alert: BankOfAnthosFrontendAvailabilitySLOBreach pending
```

The incident was not caused by a pod crash.

The likely root cause was a frontend Service selector mismatch.

## Repository boundary

This repository contains the application/platform code.

```text
sre-decision-intelligence-platform
```

The [GitOps repository](https://github.com/anselem-okeke/sre-decision-intelligence-gitops) contains Kubernetes deployment configuration, Argo CD applications, observability manifests, incident evidence, and workload configuration.

```text
sre-decision-intelligence-gitops
```

## Planned components

- FastAPI API layer
- Prometheus collector
- OpenSearch collector
- Kubernetes collector
- Argo CD collector later
- Signal classifier
- Incident correlator
- Decision engine
- Safe action mapper
- PostgreSQL persistence
- Test suite

## Technology stack

| Layer | Tool |
|---|---|
| API | FastAPI |
| Schemas | Pydantic |
| HTTP clients | httpx |
| Kubernetes client | kubernetes Python client |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Testing | pytest |
| Local runtime | Docker Compose |

> ## Goal
>
> The Decision Intelligence API is an evidence-based SRE decision layer for Kubernetes incident response.
>
> It analyzes operational signals from workloads, services, routing, and cluster state to identify a likely root cause, assign confidence, and recommend a safe next action.
>
> The platform is not designed to blindly automate remediation.
>
> Before recommending an action, it re-validates the current evidence to avoid stale or unsafe decisions.
>
> The goal is to demonstrate how SRE teams can move from raw alerts to explainable, auditable, and safer operational decisions.
