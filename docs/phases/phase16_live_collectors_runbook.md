# Phase 16 Runbook — Live Collectors v1

## SRE Decision Intelligence Platform

This runbook documents Phase 16 of the SRE Decision Intelligence Platform.

Phase 16 is where the platform moves from **sample incident signals** to **live signal collection** from Prometheus, Kubernetes, and OpenSearch.

---

# 1. Phase 16 Objective

Before Phase 16:

```text
sample_signals.py
    ↓
RuleEngine
    ↓
DecisionResponse
```

After Phase 16:

```text
Prometheus Collector
Kubernetes Collector
OpenSearch Collector
        ↓
normalized live signals
        ↓
RuleEngine
        ↓
DecisionResponse
```

The key architecture principle:

```text
The RuleEngine should not care where signals come from.
```

Signals can come from:

```text
sample_signals.py
```

or:

```text
Prometheus + Kubernetes API + OpenSearch
```

The final output remains the same:

```text
Impact
Evidence
Likely root cause
Safe action
```

---

# 2. Phase 16 Parts

## Phase 16A — Live collector classes

Created collectors:

```text
app/collectors/prometheus.py
app/collectors/kubernetes.py
app/collectors/opensearch.py
app/collectors/frontend_availability.py
```

Created tests:

```text
app/tests/test_prometheus_collector.py
app/tests/test_kubernetes_collector.py
app/tests/test_opensearch_collector.py
```

## Phase 16B — Optional live endpoint

Added endpoint:

```http
GET /api/v1/incidents/frontend-availability/live
```

Optional debug endpoint:

```http
GET /api/v1/incidents/frontend-availability/live/signals
```

---

# 3. Final Architecture

```text
FastAPI API
   │
   ├── Stable endpoint
   │      GET /api/v1/incidents/frontend-availability
   │      ↓
   │      sample validated signals
   │      ↓
   │      RuleEngine
   │      ↓
   │      DecisionResponse
   │
   └── Live endpoint
          GET /api/v1/incidents/frontend-availability/live
          ↓
          PrometheusCollector
          KubernetesCollector
          OpenSearchCollector
          ↓
          normalized live signals
          ↓
          RuleEngine
          ↓
          DecisionResponse or no-active-incident response
```

---

# 4. Product Logic

The first supported incident is:

```text
Bank of Anthos frontend availability breach
```

The rule requires:

```text
probe_success = 0
frontend_endpoints = none
frontend_pod_ready = true
```

Meaning:

| Signal | Meaning |
|---|---|
| `probe_success = 0` | User-facing frontend path failed |
| `frontend_endpoints = none` | Frontend Service has no backend endpoint |
| `frontend_pod_ready = true` | Frontend Pod itself is healthy |

Together:

```text
The pod is healthy.
The user path is broken.
The Service cannot route traffic to the pod.
Likely root cause: Service selector mismatch.
```

---

# 5. Expected File Structure

```text
app/
├── collectors/
│   ├── __init__.py
│   ├── prometheus.py
│   ├── kubernetes.py
│   ├── opensearch.py
│   └── frontend_availability.py
│
├── api/
│   └── v1/
│       └── incidents.py
│
└── tests/
    ├── test_prometheus_collector.py
    ├── test_kubernetes_collector.py
    ├── test_opensearch_collector.py
    └── test_live_incidents.py
```

Verify:

```bash
tree app/collectors app/tests -L 2
```

---

# 6. Dependency Update

`pyproject.toml` should include:

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.8.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",
    "kubernetes>=30.1.0"
]
```

Install:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

---

# 7. Configuration

`app/config.py` should include live collector settings:

```python
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "SRE Decision Intelligence Platform"
    app_version: str = "0.1.0"
    environment: str = "local"

    prometheus_base_url: str = "http://localhost:9090"
    opensearch_base_url: str = "http://localhost:9200"

    workload_namespace: str = "fintech-workload"
    frontend_service_name: str = "frontend"
    frontend_app_label: str = "frontend"


settings = Settings()
```

Default assumptions:

```text
Prometheus: http://localhost:9090
OpenSearch: http://localhost:9200
Workload namespace: fintech-workload
Frontend Service: frontend
Frontend label: app=frontend
```

---

# 8. Prometheus Collector

## Purpose

Reads:

```text
probe_success
frontend availability over 5 minutes
SLO alert state
```

## PromQL queries

```promql
probe_success{job="bank-of-anthos-frontend"}
```

```promql
avg_over_time(probe_success{job="bank-of-anthos-frontend"}[5m])
```

```promql
ALERTS{alertname="BankOfAnthosFrontendAvailabilitySLOBreach",alertstate="pending"}
```

## Important snippet

```python
def get_instant_value(self, promql: str) -> float | str | None:
    data = self.query(promql)

    results = data.get("data", {}).get("result", [])
    if not results:
        return None

    value = results[0].get("value", [])
    if len(value) < 2:
        return None

    raw_value = value[1]

    try:
        return float(raw_value)
    except ValueError:
        return raw_value
```

## Expected output

Incident:

```python
{
    "probe_success": 0.0,
    "frontend_availability_5m": 0.7,
    "alert_state": "pending",
}
```

Healthy:

```python
{
    "probe_success": 1.0,
    "frontend_availability_5m": 1.0,
    "alert_state": "inactive",
}
```

---

# 9. Kubernetes Collector

## Purpose

Reads:

```text
frontend Service endpoints
frontend Pod readiness
frontend Pod status
```

## Manual checks

```bash
kubectl get endpoints frontend -n fintech-workload
kubectl get pods -n fintech-workload -l app=frontend
```

Healthy endpoint:

```text
frontend   10.244.8.229:8080
```

Broken endpoint:

```text
frontend   <none>
```

## Important snippet

```python
def get_service_endpoints(self) -> str:
    endpoints = self.core_v1.read_namespaced_endpoints(
        name=self.service_name,
        namespace=self.namespace,
    )

    addresses: list[str] = []

    for subset in endpoints.subsets or []:
        for address in subset.addresses or []:
            for port in subset.ports or []:
                addresses.append(f"{address.ip}:{port.port}")

    if not addresses:
        return "none"

    return ",".join(addresses)
```

## Expected output

Healthy:

```python
{
    "frontend_endpoints": "10.244.8.229:8080",
    "frontend_pod_ready": True,
    "frontend_pod_status": "1/1 Running",
}
```

Incident:

```python
{
    "frontend_endpoints": "none",
    "frontend_pod_ready": True,
    "frontend_pod_status": "1/1 Running",
}
```

---

# 10. OpenSearch Collector

## Purpose

Reads frontend log context.

In Phase 16, it answers:

```text
Are frontend ERROR logs elevated?
```

## Query concept

```json
{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        { "match": { "kubernetes.namespace_name": "fintech-workload" }},
        { "match": { "severity": "ERROR" }}
      ]
    }
  }
}
```

## Important snippet

```python
def count_frontend_error_logs(self, namespace: str) -> int:
    query = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"match": {"kubernetes.namespace_name": namespace}},
                    {"match": {"severity": "ERROR"}},
                ]
            }
        },
    }

    data = self.search(query)
    return int(data.get("hits", {}).get("total", {}).get("value", 0))
```

## Expected output

```python
{
    "frontend_error_log_count": 10,
    "frontend_logs": "mostly INFO",
}
```

or:

```python
{
    "frontend_error_log_count": 50,
    "frontend_logs": "elevated ERROR logs",
}
```

For the Service selector mismatch scenario, OpenSearch is supporting context. The primary root-cause evidence is still:

```text
probe_success = 0
frontend_endpoints = none
frontend_pod_ready = true
```

---

# 11. Frontend Availability Aggregator

File:

```text
app/collectors/frontend_availability.py
```

Purpose:

```text
Combine Prometheus + Kubernetes + OpenSearch outputs into one signal dictionary.
```

Important snippet:

```python
def collect_frontend_availability_live_signals() -> dict[str, Any]:
    prometheus = PrometheusCollector(settings.prometheus_base_url)

    kubernetes = KubernetesCollector(
        namespace=settings.workload_namespace,
        service_name=settings.frontend_service_name,
        app_label=settings.frontend_app_label,
    )

    opensearch = OpenSearchCollector(settings.opensearch_base_url)

    signals: dict[str, Any] = {}

    signals.update(prometheus.collect_frontend_availability_signals())
    signals.update(kubernetes.collect_frontend_kubernetes_signals())
    signals.update(opensearch.collect_frontend_log_signals(settings.workload_namespace))

    return signals
```

Expected combined signal dictionary:

```python
{
    "probe_success": 0.0,
    "frontend_availability_5m": 0.7,
    "alert_state": "pending",
    "frontend_endpoints": "none",
    "frontend_pod_ready": True,
    "frontend_pod_status": "1/1 Running",
    "frontend_error_log_count": 10,
    "frontend_logs": "mostly INFO",
}
```

---

# 12. Live Endpoint

Endpoint:

```http
GET /api/v1/incidents/frontend-availability/live
```

Flow:

```text
collect live signals
    ↓
RuleEngine evaluates signals
    ↓
if rule matches: return DecisionResponse
if no rule matches: return 404 no active incident
if collection fails: return 503 collector failure
```

Important snippet:

```python
@router.get("/frontend-availability/live", response_model=DecisionResponse)
def get_frontend_availability_live_incident() -> DecisionResponse:
    try:
        signals = collect_frontend_availability_live_signals()
        engine = RuleEngine(RULE_PATH)

        return engine.evaluate(signals)

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "No matching incident rule found for current live signals.",
                "reason": str(error),
            },
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to collect live frontend availability signals.",
                "reason": str(error),
            },
        ) from error
```

---

# 13. Understanding Live Endpoint 404

If `/live` returns:

```json
{
  "detail": {
    "message": "No matching incident rule found for current live signals.",
    "reason": "No matching rule found for provided signals"
  }
}
```

This means:

```text
The route exists.
Collectors ran.
Signals were collected.
RuleEngine evaluated the signals.
No active incident matched the rule.
```

Most likely the cluster is healthy.

This is correct behavior.

---

# 14. Debug Signals Endpoint

Optional endpoint:

```http
GET /api/v1/incidents/frontend-availability/live/signals
```

Purpose:

```text
Return raw normalized live signals before rule evaluation.
```

Snippet:

```python
@router.get("/frontend-availability/live/signals")
def get_frontend_availability_live_signals() -> dict[str, Any]:
    try:
        return collect_frontend_availability_live_signals()

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Unable to collect live frontend availability signals.",
                "reason": str(error),
            },
        ) from error
```

Test:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

---

# 15. Validation Runbook

## Start API

```bash
cd /mnt/data/sre-decision-intelligence-platform
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Stable endpoint

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability | jq
```

Expected:

```text
Always returns validated sample decision.
```

## Live signals endpoint

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

Healthy example:

```json
{
  "probe_success": 1.0,
  "frontend_availability_5m": 1.0,
  "alert_state": "inactive",
  "frontend_endpoints": "10.244.x.x:8080",
  "frontend_pod_ready": true,
  "frontend_pod_status": "1/1 Running",
  "frontend_error_log_count": 10,
  "frontend_logs": "mostly INFO"
}
```

## Live decision endpoint

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live | jq
```

Healthy expected result:

```json
{
  "detail": {
    "message": "No matching incident rule found for current live signals.",
    "reason": "No matching rule found for provided signals"
  }
}
```

Incident expected result:

```text
HTTP 200 with DecisionResponse
```

---

# 16. Incident Injection Runbook

Use this only for controlled validation.

## Inject Service selector mismatch

```bash
kubectl patch svc frontend -n fintech-workload \
  --type='merge' \
  -p '{"spec":{"selector":{"app":"frontend","application":"bank-of-anthos","environment":"development","team":"frontend","tier":"web","slo-test":"broken"}}}'
```

## Verify endpoints are gone

```bash
kubectl get endpoints frontend -n fintech-workload
```

Expected:

```text
frontend   <none>
```

## Wait

Wait:

```text
30–60 seconds
```

## Check live signals

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

Expected important fields:

```json
{
  "probe_success": 0.0,
  "frontend_endpoints": "none",
  "frontend_pod_ready": true
}
```

## Check live decision

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live | jq
```

Expected root cause:

```json
{
  "likely_root_cause": {
    "summary": "Frontend Service selector did not match frontend pod labels",
    "confidence": "high",
    "category": "service-routing"
  }
}
```

---

# 17. Restore Runbook

Always restore after validation.

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

Verify:

```bash
kubectl get endpoints frontend -n fintech-workload
```

Expected:

```text
frontend   10.244.x.x:8080
```

Check live endpoint again:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live | jq
```

Expected:

```text
No matching incident rule found for current live signals.
```

---

# 18. Unit Test Runbook

Run collector tests:

```bash
pytest app/tests/test_prometheus_collector.py -q
pytest app/tests/test_kubernetes_collector.py -q
pytest app/tests/test_opensearch_collector.py -q
```

Run live endpoint tests:

```bash
pytest app/tests/test_live_incidents.py -q
```

Run full suite:

```bash
pytest
```

Expected:

```text
all tests passed
```

---

# 19. Troubleshooting

## `EOFcat` error

Error:

```text
NameError: name 'EOFcat' is not defined
```

Cause:

```text
Shell heredoc text was accidentally pasted into a Python file.
```

Find corrupted files:

```bash
grep -R "EOFcat\|cat >\|<<'EOF'\|EOF$" app/collectors app/tests app/engine app/api -n
```

Expected:

```text
empty output
```

Fix by rewriting the corrupted Python file.

---

## `/live` returns 404

If response is:

```json
{
  "detail": {
    "message": "No matching incident rule found for current live signals.",
    "reason": "No matching rule found for provided signals"
  }
}
```

Meaning:

```text
Collectors worked.
The cluster is probably healthy.
No incident rule matched.
```

Inspect:

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/signals | jq
```

---

## `/live` returns 503

Meaning:

```text
A collector failed.
```

Common causes:

```text
Prometheus not reachable
OpenSearch not reachable
Kubernetes config unavailable
Wrong namespace
Wrong service name
Wrong port-forward
```

---

# 20. Source System Checks

## Kubernetes

```bash
kubectl get svc frontend -n fintech-workload
kubectl get endpoints frontend -n fintech-workload
kubectl get pods -n fintech-workload -l app=frontend
```

## Prometheus

Port-forward if needed:

```bash
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
```

Check probe:

```bash
curl "http://localhost:9090/api/v1/query?query=probe_success%7Bjob%3D%22bank-of-anthos-frontend%22%7D" | jq
```

Check availability:

```bash
curl "http://localhost:9090/api/v1/query?query=avg_over_time%28probe_success%7Bjob%3D%22bank-of-anthos-frontend%22%7D%5B5m%5D%29" | jq
```

## OpenSearch

Port-forward if needed:

```bash
kubectl -n logging port-forward svc/opensearch 9200:9200
```

Check cluster health:

```bash
curl "http://localhost:9200/_cluster/health?pretty"
```

Check frontend ERROR logs:

```bash
curl "http://localhost:9200/k8s-logs-*/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 0,
    "query": {
      "bool": {
        "must": [
          { "match": { "kubernetes.namespace_name": "fintech-workload" }},
          { "match": { "severity": "ERROR" }}
        ]
      }
    }
  }'
```

---

# 21. What Phase 16 Proves

Phase 16 proves:

```text
The platform can collect live signals.
The platform can normalize live signals.
The same RuleEngine can evaluate sample or live data.
The live API can return either a decision or a no-active-incident response.
```

Before Phase 16:

```text
The platform explained a validated static incident.
```

After Phase 16:

```text
The platform can evaluate the current live platform state.
```

---

# 22. What Phase 16 Does Not Do Yet

Phase 16 does not yet:

```text
persist incidents
store signals
store decisions
maintain incident history
compare current and previous states
support many rules dynamically
authenticate API access
perform automatic remediation
```

The next phase is:

```text
Phase 17 — PostgreSQL Persistence
```

---

# 23. Recommended Git Commits

Phase 16A:

```bash
git add app/collectors app/tests/test_prometheus_collector.py \
        app/tests/test_kubernetes_collector.py \
        app/tests/test_opensearch_collector.py \
        app/config.py pyproject.toml

git commit -m "feat: add live collectors for frontend availability signals"
```

Phase 16B:

```bash
git add app/api/v1/incidents.py \
        app/collectors/frontend_availability.py \
        app/tests/test_live_incidents.py

git commit -m "feat: add optional live frontend incident endpoint"
```

Push:

```bash
git push
```

---

# 24. Final Mental Model

```text
Collectors = get facts from tools
Signals = normalized facts
Rules = interpretation logic
RuleEngine = applies interpretation
DecisionResponse = product output
```

Example:

```text
Prometheus says:
probe_success = 0

Kubernetes says:
frontend_endpoints = none
frontend_pod_ready = true

OpenSearch says:
frontend_logs = mostly INFO

RuleEngine says:
This is likely Service selector mismatch.

API returns:
Impact, evidence, likely root cause, safe action.
```

That is the core of the SRE Decision Intelligence Platform after Phase 16.
