```markdown
# SLI/SLO Design

## Principle

SLOs are defined from user journeys, not from random available metrics.

The correct design flow is:

```text
User journey
   ↓
SLI
   ↓
SLO target
   ↓
Measurement point
   ↓
Prometheus query
   ↓
Alert / burn-rate rule
```
## Bank of Anthos User Journeys

The first user journeys are:

- User can access the banking frontend
- User can complete a transaction
- User receives acceptable response latency

## Initial SLO Candidates

| User Journey         | SLI                              | SLO                   |
| -------------------- | -------------------------------- | --------------------- |
| Access frontend      | Successful frontend request rate | 99% success           |
| Complete transaction | Successful transaction rate      | 99% success           |
| Fast user experience | p95 request latency              | p95 under 500ms or 1s |

## Measurement Strategy

User-facing availability and latency should be measured as close to the user as possible.

Preferred measurement points:

- Ingress / Gateway / Edge
- Frontend service metrics
- Application business metrics

Infrastructure metrics such as CPU, memory, and pod restarts are investigation signals, not primary user-facing SLOs.

## SLO Role in Decision Intelligence

An SLO breach starts the investigation.

- Example:

```text
Frontend availability SLO breached
   ↓
Decision engine queries OpenSearch for related errors
   ↓
Decision engine checks Kubernetes events
   ↓
Decision engine checks Argo CD for recent changes
   ↓
Incident summary is generated
```

## Important Distinction

SLO alert:

- Users are affected.

Investigation telemetry:

- Why are users affected?

Decision intelligence:

- What should we do safely now?