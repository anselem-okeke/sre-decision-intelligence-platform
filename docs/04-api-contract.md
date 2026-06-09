# API Contract

## Objective

This document defines the initial API contract for the SRE Decision Intelligence Platform.

The API converts correlated observability signals into actionable incident decisions.

The first supported scenario is:

```text
Bank of Anthos frontend availability breach
```

This scenario was validated in the GitOps repository using real evidence:

```text
Frontend pod: 1/1 Running
Frontend Service endpoints: <none>
Prometheus probe_success: 0
SLO availability: 0.7
Alert state: pending
Likely root cause: Service selector mismatch
Safe action: Restore Service selector
```

---

## API Design Principle

The API should not expose raw telemetry as the final product.

Raw telemetry already exists in:

- Prometheus
- OpenSearch
- Kubernetes
- Argo CD
- Grafana

The Decision Intelligence API should return a structured incident decision:

```text
Impact
Evidence
Likely root cause
Safe action
Confidence
```

---

## API Versioning

Initial API version:

```http
/api/v1
```

Versioning is required because the response schema may evolve as new scenarios and collectors are added.

---

## Initial Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Basic application health check |
| `GET` | `/api/v1/incidents/frontend-availability` | Return decision output for the frontend availability scenario |
| `GET` | `/api/v1/signals/frontend-availability` | Return normalized signals for the frontend scenario |
| `GET` | `/api/v1/decisions/latest` | Return latest generated decision |
| `GET` | `/api/v1/slos/frontend-availability` | Return SLO status for frontend availability |

The first implementation may start with only:

```http
GET /health
GET /api/v1/incidents/frontend-availability
```

---

## Health Endpoint

### Request

```http
GET /health
```

### Response

```json
{
  "status": "ok",
  "service": "sre-decision-intelligence-platform",
  "version": "0.1.0"
}
```

---

## Frontend Availability Incident Endpoint

### Request

```http
GET /api/v1/incidents/frontend-availability
```

### Purpose

Return a decision-ready incident summary for the Bank of Anthos frontend availability breach.

### Response

```json
{
  "incident_id": "frontend-availability-breach",
  "service": "frontend",
  "namespace": "fintech-workload",
  "severity": "warning",
  "status": "detected",
  "impact": {
    "summary": "Bank of Anthos frontend endpoint unavailable",
    "user_impact": "Users cannot reliably access the banking frontend service path.",
    "slo_affected": "frontend-availability"
  },
  "signals": {
    "prometheus": [
      {
        "name": "probe_success",
        "value": 0,
        "meaning": "Frontend probe failed"
      },
      {
        "name": "frontend_availability_5m",
        "value": 0.7,
        "meaning": "Availability dropped below the 99% SLO target"
      },
      {
        "name": "alert_state",
        "value": "pending",
        "meaning": "SLO alert condition was detected by Prometheus"
      }
    ],
    "kubernetes": [
      {
        "name": "frontend_endpoints",
        "value": "none",
        "meaning": "Frontend Service had no backend endpoints"
      },
      {
        "name": "frontend_pod_status",
        "value": "1/1 Running",
        "meaning": "Frontend pod was healthy while the service path was broken"
      }
    ],
    "opensearch": [
      {
        "name": "frontend_logs",
        "value": "mostly INFO",
        "meaning": "No dominant frontend application crash signal found"
      }
    ],
    "argocd": []
  },
  "evidence": [
    "probe_success dropped to 0",
    "avg_over_time(probe_success[5m]) dropped to 0.7",
    "BankOfAnthosFrontendAvailabilitySLOBreach entered pending state",
    "frontend Service endpoints became empty",
    "frontend pod remained 1/1 Running",
    "probe_success recovered after Service selector was restored"
  ],
  "likely_root_cause": {
    "summary": "Frontend Service selector did not match frontend pod labels",
    "confidence": "high",
    "category": "service-routing"
  },
  "safe_action": {
    "summary": "Restore the frontend Service selector so it matches frontend pod labels",
    "command": "kubectl patch svc frontend -n fintech-workload --type='json' -p='[{"op":"remove","path":"/spec/selector/slo-test"}]'",
    "risk": "low"
  },
  "metadata": {
    "decision_engine_version": "0.1.0",
    "scenario": "frontend-availability-breach",
    "environment": "lab"
  }
}
```

---

## Response Object Definitions

### Incident

| Field | Type | Description |
|---|---|---|
| `incident_id` | string | Unique incident identifier |
| `service` | string | Affected service |
| `namespace` | string | Kubernetes namespace |
| `severity` | string | Decision severity |
| `status` | string | Detection status |
| `impact` | object | User/business impact |
| `signals` | object | Signals grouped by source |
| `evidence` | array | Human-readable evidence list |
| `likely_root_cause` | object | Root cause analysis |
| `safe_action` | object | Recommended safe action |
| `metadata` | object | Engine and scenario metadata |

### Impact

| Field | Type | Description |
|---|---|---|
| `summary` | string | Short impact summary |
| `user_impact` | string | User-facing explanation |
| `slo_affected` | string | Related SLO |

### Signal

| Field | Type | Description |
|---|---|---|
| `name` | string | Signal name |
| `value` | any | Signal value |
| `meaning` | string | Human-readable meaning |

### Root Cause

| Field | Type | Description |
|---|---|---|
| `summary` | string | Likely root cause |
| `confidence` | string | low, medium, high |
| `category` | string | failure category |

### Safe Action

| Field | Type | Description |
|---|---|---|
| `summary` | string | Action summary |
| `command` | string | Optional command |
| `risk` | string | low, medium, high |

---

## Error Response

Example:

```json
{
  "error": {
    "code": "SIGNAL_SOURCE_UNAVAILABLE",
    "message": "Prometheus is unavailable or returned no data.",
    "source": "prometheus"
  }
}
```

---

## First Implementation Scope

The first implementation can return a static response based on the validated Phase 10 and Phase 11 evidence.

Live integrations will be added later.

Implementation order:

```text
1. Static response
2. Pydantic response schema
3. Prometheus collector
4. Kubernetes collector
5. OpenSearch collector
6. Decision engine
7. PostgreSQL persistence
```

---

## Out of Scope for Initial Version

The first version will not include:

- AI-generated root cause analysis
- automatic remediation
- write access to Kubernetes
- direct Argo CD rollback
- multi-cluster support
- user authentication

The first goal is correctness, clarity, and trustworthy incident explanation.
