# Phase 20 — Generic Normalized Signal Model

## 1. Purpose

Phase 20 introduces a **generic normalized signal model** for the SRE Decision Intelligence Platform.

Before this phase, the platform mostly worked with raw dictionaries such as:

```python
{
    "probe_success": 0.0,
    "frontend_endpoints": "none",
    "frontend_pod_ready": True,
}
```

That was enough for the first frontend availability scenario, but it does not scale well when the platform needs to understand many different incident types.

The goal of Phase 20 is to move toward a consistent signal structure that can represent both:

- **Workload signals** from Bank of Anthos or application-level monitoring
- **Platform signals** from Kubernetes, Cilium, Longhorn, Argo CD, and other infrastructure systems

The normalized signal model makes the platform easier to extend for future incident scenarios such as:

- Frontend 5xx rate
- Frontend latency
- Transaction errors
- Backend timeouts
- CrashLoopBackOff
- ImagePullBackOff
- FailedScheduling
- NodeNotReady
- PVC mount failures
- Cilium drops
- Longhorn volume degradation
- Argo CD sync drift

---

## 2. High-Level Concept

The SRE Decision Intelligence Platform does not only collect metrics. It turns raw operational data into decision-ready signals.

The core flow is:

```text
Raw collector output
        ↓
NormalizedSignal
        ↓
Rule engine input
        ↓
DecisionResponse
        ↓
Incident persistence / timeline / API
```

The normalized signal model is the bridge between **raw observability data** and **decision intelligence**.

---

## 3. Signal Domains

Phase 20 introduces two primary signal domains.

### 3.1 Workload Signals

Workload signals answer:

```text
Is the application or user path affected?
```

Examples:

```text
probe_success
frontend_availability_5m
frontend_5xx_rate
frontend_latency_p95_ms
transaction_error_rate
backend_timeout_count
ledger_database_error_count
frontend_logs
frontend_error_log_count
```

These signals usually come from:

```text
Prometheus
Blackbox Exporter
OpenSearch
Application logs
Synthetic probes
```

### 3.2 Platform Signals

Platform signals answer:

```text
Is Kubernetes or infrastructure contributing to the incident?
```

Examples:

```text
frontend_endpoints
frontend_pod_ready
frontend_pod_status
pod_crashloop
image_pull_backoff
failed_scheduling
node_not_ready
oom_killed
pvc_mount_failure
cilium_drop_count
longhorn_volume_degraded
argocd_sync_status
```

These signals usually come from:

```text
Kubernetes API
Cilium / Hubble
Longhorn
Argo CD
Cluster events
Node conditions
```

---

## 4. Why This Phase Matters

Without a normalized signal model, every scenario would need custom logic for interpreting raw data.

That would lead to messy rule evaluation such as:

```text
this rule expects probe_success
that rule expects pod status
another rule expects OpenSearch count
another rule expects Cilium drop values
```

Phase 20 gives every signal a common shape:

```json
{
  "name": "frontend_endpoints",
  "domain": "platform",
  "source": "kubernetes",
  "service": "frontend",
  "namespace": "fintech-workload",
  "value": "none",
  "unit": "endpoint-list",
  "severity": "critical",
  "meaning": "Kubernetes Service backend endpoints for frontend"
}
```

This makes future scenarios easier to add because all signals can be reasoned about in the same way.

---

## 5. Target File Structure

Phase 20 adds a new package:

```text
app/signals/
├── __init__.py
├── models.py
├── normalizer.py
└── frontend_availability.py
```

And tests:

```text
app/tests/
├── test_normalized_signal_model.py
├── test_frontend_signal_normalizer.py
└── test_normalized_signals_endpoint.py
```

---

## 6. Implementation — Signal Models

### File

```text
app/signals/models.py
```

### Purpose

This file defines the core signal schema and enum values.

### Implementation

```python
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SignalDomain(StrEnum):
    WORKLOAD = "workload"
    PLATFORM = "platform"


class SignalSource(StrEnum):
    PROMETHEUS = "prometheus"
    KUBERNETES = "kubernetes"
    OPENSEARCH = "opensearch"
    ARGOCD = "argocd"
    CILIUM = "cilium"
    LONGHORN = "longhorn"
    UNKNOWN = "unknown"


class SignalSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class NormalizedSignal(BaseModel):
    name: str = Field(..., description="Stable machine-readable signal name")
    domain: SignalDomain = Field(..., description="workload or platform")
    source: SignalSource = Field(..., description="System that produced the signal")
    service: str | None = Field(None, description="Affected service, if known")
    namespace: str | None = Field(None, description="Kubernetes namespace, if known")
    value: Any = Field(..., description="Observed signal value")
    unit: str | None = Field(None, description="Unit of measurement")
    severity: SignalSeverity = Field(default=SignalSeverity.UNKNOWN)
    meaning: str = Field(..., description="Human-readable explanation")
    labels: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] | None = Field(default=None)
```

---

## 7. NormalizedSignal Field Meaning

| Field | Purpose |
|---|---|
| `name` | Stable machine-readable signal name |
| `domain` | Whether the signal is workload or platform related |
| `source` | System that produced the signal |
| `service` | Affected service, if known |
| `namespace` | Kubernetes namespace, if known |
| `value` | Actual observed signal value |
| `unit` | Unit such as `ratio`, `count`, `boolean`, `milliseconds` |
| `severity` | Signal-level severity such as `info`, `warning`, `critical` |
| `meaning` | Human-readable explanation of what the signal means |
| `labels` | Optional labels for future filtering or enrichment |
| `raw` | Optional original collector output or raw query result |

---

## 8. Implementation — Normalizer Utilities

### File

```text
app/signals/normalizer.py
```

### Purpose

This file contains helper functions for converting raw values into normalized signal objects.

### Implementation

```python
from typing import Any

from app.signals.models import (
    NormalizedSignal,
    SignalDomain,
    SignalSeverity,
    SignalSource,
)


def severity_from_probe_success(value: float | int | None) -> SignalSeverity:
    if value == 1 or value == 1.0:
        return SignalSeverity.INFO

    if value == 0 or value == 0.0:
        return SignalSeverity.CRITICAL

    return SignalSeverity.UNKNOWN


def severity_from_availability(value: float | int | None) -> SignalSeverity:
    if value is None:
        return SignalSeverity.UNKNOWN

    if value < 0.95:
        return SignalSeverity.CRITICAL

    if value < 0.99:
        return SignalSeverity.WARNING

    return SignalSeverity.INFO


def severity_from_endpoints(value: Any) -> SignalSeverity:
    if value == "none":
        return SignalSeverity.CRITICAL

    if value:
        return SignalSeverity.INFO

    return SignalSeverity.UNKNOWN


def severity_from_boolean_health(value: bool | None) -> SignalSeverity:
    if value is True:
        return SignalSeverity.INFO

    if value is False:
        return SignalSeverity.CRITICAL

    return SignalSeverity.UNKNOWN


def make_signal(
    name: str,
    domain: SignalDomain,
    source: SignalSource,
    value: Any,
    meaning: str,
    service: str | None = None,
    namespace: str | None = None,
    unit: str | None = None,
    severity: SignalSeverity = SignalSeverity.UNKNOWN,
    labels: dict[str, Any] | None = None,
    raw: dict[str, Any] | None = None,
) -> NormalizedSignal:
    return NormalizedSignal(
        name=name,
        domain=domain,
        source=source,
        service=service,
        namespace=namespace,
        value=value,
        unit=unit,
        severity=severity,
        meaning=meaning,
        labels=labels or {},
        raw=raw,
    )
```

---

## 9. Implementation — Frontend Availability Normalizer

### File

```text
app/signals/frontend_availability.py
```

### Purpose

This file converts raw frontend availability signals into normalized signals.

Raw input example:

```python
{
    "probe_success": 0.0,
    "frontend_availability_5m": 0.6,
    "alert_state": "pending",
    "frontend_endpoints": "none",
    "frontend_pod_ready": True,
    "frontend_pod_status": "1/1 Running",
    "frontend_logs": "mostly INFO",
    "frontend_error_log_count": 13,
}
```

Normalized output includes both workload and platform signals.

### Core function

```python
def normalize_frontend_availability_signals(
    raw_signals: dict[str, Any],
    service: str = "frontend",
    namespace: str = "fintech-workload",
) -> list[NormalizedSignal]:
    ...
```

### Key normalized signals

| Signal | Domain | Source | Meaning |
|---|---|---|---|
| `probe_success` | workload | prometheus | Synthetic probe success state |
| `frontend_availability_5m` | workload | prometheus | Frontend availability over 5 minutes |
| `alert_state` | workload | prometheus | Prometheus alert state |
| `frontend_endpoints` | platform | kubernetes | Service backend endpoints |
| `frontend_pod_ready` | platform | kubernetes | Pod readiness state |
| `frontend_pod_status` | platform | kubernetes | Pod status summary |
| `frontend_logs` | workload | opensearch | Application log summary |
| `frontend_error_log_count` | workload | opensearch | Error log count |

Later phases extend this same normalizer with workload and platform signals such as:

```text
frontend_5xx_rate
frontend_latency_p95_ms
transaction_error_rate
backend_timeout_count
ledger_database_error_count
pod_crashloop
image_pull_backoff
failed_scheduling
node_not_ready
oom_killed
pvc_mount_failure
cilium_drop_count
longhorn_volume_degraded
argocd_sync_status
```

---

## 10. API Endpoint Added in Phase 20

### Endpoint

```http
GET /api/v1/incidents/frontend-availability/live/signals/normalized
```

### Purpose

This endpoint allows the user to inspect live normalized signals from the frontend availability collector.

### Example response

```json
[
  {
    "name": "probe_success",
    "domain": "workload",
    "source": "prometheus",
    "service": "frontend",
    "namespace": "fintech-workload",
    "value": 1.0,
    "unit": "boolean",
    "severity": "info",
    "meaning": "Frontend synthetic probe success state",
    "labels": {},
    "raw": {
      "query_result": 1.0
    }
  },
  {
    "name": "frontend_endpoints",
    "domain": "platform",
    "source": "kubernetes",
    "service": "frontend",
    "namespace": "fintech-workload",
    "value": "10.244.8.229:8080",
    "unit": "endpoint-list",
    "severity": "info",
    "meaning": "Kubernetes Service backend endpoints for frontend",
    "labels": {},
    "raw": {
      "kubernetes_value": "10.244.8.229:8080"
    }
  }
]
```

---

## 11. API Route Implementation

The endpoint was added to:

```text
app/api/v1/incidents.py
```

In the pre-refactor implementation, it directly called the collector and normalizer.

After Phase 26, the route should call the frontend incident service:

```python
@router.get("/frontend-availability/live/signals/normalized")
def get_frontend_availability_live_normalized_signals() -> list[dict]:
    try:
        return get_frontend_live_normalized_signals()

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to collect or normalize live frontend availability signals.",
                "reason": str(error),
            },
        ) from error
```

Service-layer implementation:

```python
def get_frontend_live_normalized_signals() -> list[dict[str, Any]]:
    raw_signals = collect_frontend_availability_live_signals()
    normalized_signals = normalize_frontend_availability_signals(raw_signals)

    return [signal.model_dump(mode="json") for signal in normalized_signals]
```

---

## 12. Tests Added in Phase 20

Phase 20 introduced tests for three layers:

```text
model validation
normalizer behavior
API endpoint behavior
```

---

## 13. Test — Normalized Signal Model

### File

```text
app/tests/test_normalized_signal_model.py
```

### Purpose

Validates that `NormalizedSignal` supports both workload and platform signals.

### Test command

```bash
pytest app/tests/test_normalized_signal_model.py -q
```

### Expected result

```text
2 passed
```

### Example test

```python
def test_normalized_signal_model_accepts_workload_signal():
    signal = NormalizedSignal(
        name="frontend_5xx_rate",
        domain=SignalDomain.WORKLOAD,
        source=SignalSource.PROMETHEUS,
        service="frontend",
        namespace="fintech-workload",
        value=0.12,
        unit="ratio",
        severity=SignalSeverity.WARNING,
        meaning="Frontend is returning elevated 5xx responses",
    )

    assert signal.name == "frontend_5xx_rate"
    assert signal.domain == SignalDomain.WORKLOAD
    assert signal.source == SignalSource.PROMETHEUS
    assert signal.severity == SignalSeverity.WARNING
```

---

## 14. Test — Frontend Signal Normalizer

### File

```text
app/tests/test_frontend_signal_normalizer.py
```

### Purpose

Validates that raw frontend availability signals are converted into normalized workload and platform signals.

### Test command

```bash
pytest app/tests/test_frontend_signal_normalizer.py -q
```

### Expected result

```text
3 passed
```

### Key assertions

The normalizer should produce:

```text
probe_success
frontend_endpoints
```

It should include both domains:

```text
workload
platform
```

It should include multiple sources:

```text
prometheus
kubernetes
opensearch
```

Broken endpoint case:

```text
frontend_endpoints = none
severity = critical
```

Healthy endpoint case:

```text
frontend_endpoints = 10.244.8.229:8080
severity = info
```

---

## 15. Test — Normalized Signals Endpoint

### File

```text
app/tests/test_normalized_signals_endpoint.py
```

### Purpose

Validates that the API endpoint returns normalized signals as JSON.

### Test command

```bash
pytest app/tests/test_normalized_signals_endpoint.py -q
```

### Expected result

```text
1 passed
```

### Important note after Phase 26 refactor

After the service-layer refactor, tests should monkeypatch the collector in:

```python
from app.services import frontend_incident_service
```

not in:

```python
from app.api.v1 import incidents
```

Correct monkeypatch target:

```python
monkeypatch.setattr(
    frontend_incident_service,
    "collect_frontend_availability_live_signals",
    fake_collect_signals,
)
```

This matches the Phase 26 architecture where the API route calls the service layer.

---

## 16. Focused Validation Commands

Run all Phase 20 tests:

```bash
pytest app/tests/test_normalized_signal_model.py -q
pytest app/tests/test_frontend_signal_normalizer.py -q
pytest app/tests/test_normalized_signals_endpoint.py -q
```

Expected:

```text
2 passed
3 passed
1 passed
```

Run the full suite:

```bash
pytest
```

Expected after the later refactors:

```text
62 passed
```

---

## 17. Manual API Validation

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Call the raw live signals endpoint:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

Expected example:

```json
{
  "probe_success": 1.0,
  "frontend_availability_5m": 1.0,
  "alert_state": "inactive",
  "frontend_endpoints": "10.244.8.229:8080",
  "frontend_pod_ready": true,
  "frontend_pod_status": "1/1 Running",
  "frontend_error_log_count": 34,
  "frontend_logs": "elevated ERROR logs"
}
```

Call the normalized endpoint:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals/normalized | jq
```

Expected:

```text
A JSON list of normalized signals
```

Important healthy-state signals should include:

```text
probe_success → workload/prometheus/info
frontend_availability_5m → workload/prometheus/info
frontend_endpoints → platform/kubernetes/info
frontend_pod_ready → platform/kubernetes/info
frontend_logs → workload/opensearch
```

---

## 18. Manual Broken Scenario Validation

Break the frontend Service selector:

```bash
kubectl patch svc frontend -n fintech-workload \
  --type='merge' \
  -p '{"spec":{"selector":{"app":"frontend","application":"bank-of-anthos","environment":"development","team":"frontend","tier":"web","slo-test":"broken"}}}'
```

Wait for the probe to fail:

```bash
sleep 60
```

Call normalized signals:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals/normalized | jq
```

Expected important values:

```json
[
  {
    "name": "probe_success",
    "domain": "workload",
    "source": "prometheus",
    "value": 0.0,
    "severity": "critical"
  },
  {
    "name": "frontend_endpoints",
    "domain": "platform",
    "source": "kubernetes",
    "value": "none",
    "severity": "critical"
  },
  {
    "name": "frontend_pod_ready",
    "domain": "platform",
    "source": "kubernetes",
    "value": true,
    "severity": "info"
  }
]
```

Restore the selector:

```bash
kubectl patch svc frontend -n fintech-workload \
  --type='json' \
  -p='[
    {
      "op": "remove",
      "path": "/spec/selector/slo-test"
    }
  ]'
```

Verify endpoints return:

```bash
kubectl get endpoints frontend -n fintech-workload
```

Expected:

```text
frontend   10.x.x.x:8080
```

---

## 19. How Phase 20 Connects to Later Phases

Phase 20 is the foundation for the later expansion phases.

| Later Phase | Dependency on Phase 20 |
|---|---|
| Phase 21 — Scenario Registry | Scenarios declare required signal names |
| Phase 22 — Multi-rule Engine | Rules evaluate signal names and values |
| Phase 23 — Workload Scenarios | Adds workload-specific signal types |
| Phase 24 — Platform Scenarios | Adds platform-specific signal types |
| Phase 25 — Generic Evaluate API | Accepts signal dictionaries for generic evaluation |
| Phase 26 — Service Refactor | Moves normalized signal endpoint behind service layer |

---

## 20. Common Issues and Fixes

### Issue 1 — Normalized endpoint test fails after service refactor

Error example:

```text
AttributeError: module app.api.v1.incidents has no attribute collect_frontend_availability_live_signals
```

Cause:

```text
The test still monkeypatches the old route module instead of the new service module.
```

Fix:

```python
from app.services import frontend_incident_service

monkeypatch.setattr(
    frontend_incident_service,
    "collect_frontend_availability_live_signals",
    fake_collect_signals,
)
```

---

### Issue 2 — Some normalized signals return null

Example:

```json
{
  "name": "frontend_5xx_rate",
  "value": null,
  "severity": "unknown"
}
```

This is acceptable if the live collector does not yet collect that metric.

Phase 20 defines the signal structure. Later phases expand actual collection support.

---

### Issue 3 — Severity is unknown

Some signals intentionally use:

```text
severity = unknown
```

because Phase 20 only defines severity mapping for selected signals:

```text
probe_success
frontend_availability_5m
frontend_endpoints
frontend_pod_ready
```

More severity rules can be added later.

---

## 21. Phase 20 Success Criteria

Phase 20 is complete when:

```text
NormalizedSignal model exists
SignalDomain exists
SignalSource exists
SignalSeverity exists
Frontend raw signals can be normalized
Normalized signals include workload and platform domains
Normalized signals endpoint works
Tests pass
Manual healthy-state validation works
Manual broken-selector validation works
```

---

## 22. Commit

```bash
git status
```

Then:

```bash
git add app/signals \
        app/api/v1/incidents.py \
        app/tests/test_normalized_signal_model.py \
        app/tests/test_frontend_signal_normalizer.py \
        app/tests/test_normalized_signals_endpoint.py
```

Commit:

```bash
git commit -m "feat: add generic normalized signal model"
git push
```

If Phase 20 was already committed earlier, no additional commit is needed unless tests or service-layer monkeypatch targets were updated later.

---

## 23. Final Summary

Phase 20 moves the project from raw signal dictionaries to a structured signal model.

Before Phase 20:

```text
Raw collector dictionaries were directly consumed by rule logic.
```

After Phase 20:

```text
Raw collector output can be converted into normalized workload and platform signals.
```

This is what allows the SRE Decision Intelligence Platform to grow from one frontend incident scenario into a multi-scenario decision platform.
