# Phase 24 — Platform Scenarios

## Project

**SRE Decision Intelligence Platform**

## Phase status

**Implemented and validated**

Phase 24 extends the platform from workload/application incident scenarios into Kubernetes and platform-level incident scenarios.

The goal of this phase is to answer:

> Is the Kubernetes platform, infrastructure, networking, storage, or GitOps state contributing to the incident?

This phase remains under the existing API version:

```text
/api/v1
```

No `/api/v2` is introduced because this phase is additive and does not break the existing API contract.

---

## 1. Why Phase 24 exists

Before Phase 24, the platform already supported:

| Phase | Capability |
|---|---|
| Phase 20 | Generic normalized signal model |
| Phase 21 | Scenario registry |
| Phase 22 | Multi-rule / multi-scenario rule engine |
| Phase 23 | Workload scenarios |

Phase 23 focused on application-side and user-path degradation patterns, such as:

```text
frontend-high-5xx-rate
frontend-high-latency
transaction-error-spike
backend-timeout-spike
ledger-database-error-spike
```

However, many real incidents are caused or amplified by platform conditions, such as:

```text
CrashLoopBackOff
ImagePullBackOff
FailedScheduling
NodeNotReady
OOMKilled
PVC mount failure
Cilium drops
Longhorn volume degradation
Argo CD sync drift
```

Phase 24 introduces these platform scenarios into the same decision framework.

---

## 2. Mental model

The platform now correlates:

```text
Workload impact
        +
Platform context
        =
Impact → Evidence → Root Cause → Safe Action
```

A workload signal tells us:

```text
Users are affected.
```

A platform signal tells us:

```text
Why Kubernetes or infrastructure may be contributing.
```

Example:

```text
probe_success = 0
frontend_pod_ready = false
frontend_pod_status contains CrashLoopBackOff

Result:
Frontend pod is crashing.
```

Another example:

```text
node_not_ready = true

Result:
A platform node health issue may be affecting workloads.
```

---

## 3. Platform scenarios added in Phase 24

Phase 24 adds the following platform incident scenarios:

| Scenario ID | Root cause category | Purpose |
|---|---|---|
| `frontend-pod-crashloop` | `workload-crash` | Detect frontend pod CrashLoopBackOff |
| `frontend-image-pull-backoff` | `image-pull-failure` | Detect image pull or registry problems |
| `frontend-failed-scheduling` | `scheduling-failure` | Detect scheduling failure |
| `node-not-ready` | `node-health` | Detect Kubernetes node health degradation |
| `frontend-oom-killed` | `memory-pressure` | Detect frontend OOMKilled events |
| `pvc-mount-failure` | `storage-mount-failure` | Detect PVC mount problems |
| `cilium-drop-spike` | `network-drops` | Detect Cilium/Hubble drop spikes |
| `longhorn-volume-degraded` | `storage-degradation` | Detect Longhorn volume degradation |
| `argocd-sync-drift` | `gitops-drift` | Detect GitOps desired-state drift |

---

## 4. Files changed or added

Phase 24 mainly touches these areas:

```text
app/rules/
app/signals/frontend_availability.py
app/scenarios/frontend_availability.py
app/scenarios/registry.py
app/engine/sample_signals.py
app/tests/test_platform_scenarios.py
```

The important design is that platform scenarios are added as **data-driven rules** and **scenario registry entries**, not as separate hardcoded endpoints.

---

## 5. Sample signal expansion

The sample signal function was extended to include platform signal keys.

File:

```text
app/engine/sample_signals.py
```

Expected additional Phase 24 keys:

```python
"pod_crashloop": False,
"image_pull_backoff": False,
"failed_scheduling": False,
"node_not_ready": False,
"oom_killed": False,
"pvc_mount_failure": False,
"cilium_drop_count": 0,
"longhorn_volume_degraded": False,
"argocd_sync_status": "Synced",
```

These signals allow the rule engine to test platform scenarios without requiring all real collectors to exist yet.

---

## 6. Platform rule YAML files

### 6.1 Frontend Pod CrashLoopBackOff

File:

```text
app/rules/frontend_pod_crashloop.yaml
```

Purpose:

```text
Detects when the frontend user path is unavailable because the frontend pod is repeatedly crashing.
```

Core conditions:

```yaml
conditions:
  - signal: probe_success
    operator: equals
    value: 0

  - signal: frontend_pod_ready
    operator: equals
    value: false

  - signal: frontend_pod_status
    operator: contains
    value: CrashLoopBackOff
```

Decision category:

```text
workload-crash
```

Safe action:

```text
Inspect frontend pod logs and recent rollout before restarting or rolling back the deployment.
```

---

### 6.2 Frontend ImagePullBackOff

File:

```text
app/rules/frontend_image_pull_backoff.yaml
```

Purpose:

```text
Detects when the frontend pod cannot start because Kubernetes cannot pull the container image.
```

Core conditions:

```yaml
conditions:
  - signal: frontend_pod_ready
    operator: equals
    value: false

  - signal: frontend_pod_status
    operator: contains
    value: ImagePullBackOff
```

Decision category:

```text
image-pull-failure
```

Safe action:

```text
Check image name, tag, registry credentials, and imagePullSecrets before redeploying.
```

---

### 6.3 Frontend FailedScheduling

File:

```text
app/rules/frontend_failed_scheduling.yaml
```

Purpose:

```text
Detects when Kubernetes cannot schedule the frontend pod onto a node.
```

Core condition:

```yaml
conditions:
  - signal: failed_scheduling
    operator: equals
    value: true
```

Decision category:

```text
scheduling-failure
```

Safe action:

```text
Inspect pod events, node capacity, taints, tolerations, affinity, and resource requests.
```

---

### 6.4 NodeNotReady

File:

```text
app/rules/node_not_ready.yaml
```

Purpose:

```text
Detects when one or more Kubernetes nodes are not ready.
```

Core condition:

```yaml
conditions:
  - signal: node_not_ready
    operator: equals
    value: true
```

Decision category:

```text
node-health
```

Safe action:

```text
Inspect node conditions, kubelet status, disk pressure, memory pressure, and network connectivity.
```

---

### 6.5 Frontend OOMKilled

File:

```text
app/rules/frontend_oom_killed.yaml
```

Purpose:

```text
Detects when the frontend container was killed because it exceeded its memory limit.
```

Core condition:

```yaml
conditions:
  - signal: oom_killed
    operator: equals
    value: true
```

Decision category:

```text
memory-pressure
```

Safe action:

```text
Inspect memory usage, container limits, recent traffic, and memory leak indicators before increasing limits.
```

---

### 6.6 PVC Mount Failure

File:

```text
app/rules/pvc_mount_failure.yaml
```

Purpose:

```text
Detects when Kubernetes cannot mount a persistent volume claim.
```

Core condition:

```yaml
conditions:
  - signal: pvc_mount_failure
    operator: equals
    value: true
```

Decision category:

```text
storage-mount-failure
```

Safe action:

```text
Inspect PVC, PV, storage class, Longhorn volume state, and pod mount events.
```

---

### 6.7 Cilium Drop Spike

File:

```text
app/rules/cilium_drop_spike.yaml
```

Purpose:

```text
Detects elevated Cilium/Hubble network drops.
```

Core condition:

```yaml
conditions:
  - signal: cilium_drop_count
    operator: greater_than
    value: 20
```

Decision category:

```text
network-drops
```

Safe action:

```text
Inspect Hubble flows, Cilium policy verdicts, and affected source/destination services.
```

---

### 6.8 Longhorn Volume Degraded

File:

```text
app/rules/longhorn_volume_degraded.yaml
```

Purpose:

```text
Detects when Longhorn reports degraded volume health.
```

Core condition:

```yaml
conditions:
  - signal: longhorn_volume_degraded
    operator: equals
    value: true
```

Decision category:

```text
storage-degradation
```

Safe action:

```text
Inspect Longhorn volume replicas, node disk health, and replica rebuild status.
```

---

### 6.9 Argo CD Sync Drift

File:

```text
app/rules/argocd_sync_drift.yaml
```

Purpose:

```text
Detects when desired Git state and live Kubernetes state are out of sync.
```

Core condition:

```yaml
conditions:
  - signal: argocd_sync_status
    operator: not_equals
    value: Synced
```

Decision category:

```text
gitops-drift
```

Safe action:

```text
Inspect Argo CD diff before syncing or rolling back.
```

---

## 7. Important rule-engine safety fix

During Phase 24, the `argocd-sync-drift` rule exposed an important bug.

The rule condition was:

```yaml
signal: argocd_sync_status
operator: not_equals
value: Synced
```

If `argocd_sync_status` was missing from the input signals, the engine saw:

```python
actual_value = None
```

Then this comparison incorrectly matched:

```python
None != "Synced"
```

That caused false positives for GitOps drift.

### Correct behavior

A missing signal should **not** match any rule condition.

The rule engine should reject missing signals before evaluating operators.

File:

```text
app/engine/decision_engine.py
```

Correct `condition_matches()` behavior:

```python
def condition_matches(
    actual_value: Any,
    operator: str,
    expected_value: Any,
) -> bool:
    if actual_value is None:
        return False

    if operator == "equals":
        return actual_value == expected_value

    if operator == "not_equals":
        return actual_value != expected_value

    if operator == "contains":
        return str(expected_value) in str(actual_value)

    if operator == "greater_than":
        return float(actual_value) > float(expected_value)

    if operator == "less_than":
        return float(actual_value) < float(expected_value)

    raise ValueError(f"Unsupported operator: {operator}")
```

This is a critical reliability improvement.

It prevents rules from matching based on missing data.

---

## 8. Normalized signal model expansion

File:

```text
app/signals/frontend_availability.py
```

Phase 24 extends normalized signals with platform-oriented signals:

```text
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

Each signal should include:

```text
name
domain
source
service
namespace
value
unit
severity
meaning
labels
raw
```

Example normalized platform signal:

```json
{
  "name": "node_not_ready",
  "domain": "platform",
  "source": "kubernetes",
  "service": null,
  "namespace": "fintech-workload",
  "value": true,
  "unit": "boolean",
  "severity": "unknown",
  "meaning": "Whether one or more Kubernetes nodes are NotReady",
  "labels": {},
  "raw": {
    "kubernetes_value": true
  }
}
```

---

## 9. Scenario registry expansion

File:

```text
app/scenarios/frontend_availability.py
```

Phase 24 adds platform scenario definitions such as:

```text
FRONTEND_IMAGE_PULL_BACKOFF
FRONTEND_FAILED_SCHEDULING
NODE_NOT_READY
FRONTEND_OOM_KILLED
PVC_MOUNT_FAILURE
CILIUM_DROP_SPIKE
LONGHORN_VOLUME_DEGRADED
ARGOCD_SYNC_DRIFT
```

File:

```text
app/scenarios/registry.py
```

The registry should include all Phase 24 scenarios:

```python
scenario_registry = ScenarioRegistry(
    scenarios=[
        FRONTEND_SERVICE_SELECTOR_MISMATCH,
        FRONTEND_HIGH_5XX_RATE,
        FRONTEND_HIGH_LATENCY,
        TRANSACTION_ERROR_SPIKE,
        BACKEND_TIMEOUT_SPIKE,
        LEDGER_DATABASE_ERROR_SPIKE,
        FRONTEND_IMAGE_PULL_BACKOFF,
        FRONTEND_FAILED_SCHEDULING,
        NODE_NOT_READY,
        FRONTEND_OOM_KILLED,
        PVC_MOUNT_FAILURE,
        CILIUM_DROP_SPIKE,
        LONGHORN_VOLUME_DEGRADED,
        ARGOCD_SYNC_DRIFT,
    ]
)
```

---

## 10. API behavior after Phase 24

No new API version is created.

The platform scenarios are visible through the existing scenario API:

```http
GET /api/v1/scenarios
```

The platform rules are visible through the existing rule evaluation API:

```http
GET /api/v1/incidents/frontend-availability/live/evaluations
```

And the generic evaluate API can evaluate platform scenarios when matching signals are supplied:

```http
POST /api/v1/incidents/evaluate
```

---

## 11. Tests added

File:

```text
app/tests/test_platform_scenarios.py
```

Expected tests:

```text
test_frontend_image_pull_backoff_rule_matches
test_failed_scheduling_rule_matches
test_node_not_ready_rule_matches
test_oom_killed_rule_matches
test_pvc_mount_failure_rule_matches
test_cilium_drop_spike_rule_matches
test_longhorn_volume_degraded_rule_matches
test_argocd_sync_drift_rule_matches
test_platform_scenarios_are_registered
```

---

## 12. Test file example

The test file uses a `base_signals()` helper with healthy defaults:

```python
def base_signals() -> dict:
    return {
        "probe_success": 1,
        "frontend_availability_5m": 1.0,
        "alert_state": "inactive",
        "frontend_endpoints": "10.244.8.229:8080",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 0,
        "frontend_5xx_rate": 0.0,
        "frontend_latency_p95_ms": 120,
        "transaction_error_rate": 0.0,
        "backend_timeout_count": 0,
        "ledger_database_error_count": 0,
        "pod_crashloop": False,
        "image_pull_backoff": False,
        "failed_scheduling": False,
        "node_not_ready": False,
        "oom_killed": False,
        "pvc_mount_failure": False,
        "cilium_drop_count": 0,
        "longhorn_volume_degraded": False,
        "argocd_sync_status": "Synced",
    }
```

Each test changes one signal to trigger a specific platform scenario.

Example:

```python
def test_node_not_ready_rule_matches():
    signals = base_signals()
    signals["node_not_ready"] = True

    decision = MultiRuleEngine(RULES_DIR).evaluate(signals)

    assert decision.likely_root_cause.category == "node-health"
```

---

## 13. Validation commands

### 13.1 Run platform scenario tests

```bash
pytest app/tests/test_platform_scenarios.py -q
```

Expected:

```text
9 passed
```

---

### 13.2 Run regression tests for related phases

```bash
pytest app/tests/test_multi_rule_engine.py -q
pytest app/tests/test_workload_scenarios.py -q
pytest app/tests/test_platform_scenarios.py -q
```

Expected:

```text
all passed
```

---

### 13.3 Run full test suite

```bash
pytest
```

Expected after the project reached Phase 26:

```text
62 passed
```

Warnings may appear, but they are not Phase 24 blockers.

---

## 14. Manual API validation

Start API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 14.1 Validate scenario registry

```bash
curl http://localhost:8000/api/v1/scenarios | jq '.[].id'
```

Expected Phase 24 scenario IDs include:

```text
"frontend-image-pull-backoff"
"frontend-failed-scheduling"
"node-not-ready"
"frontend-oom-killed"
"pvc-mount-failure"
"cilium-drop-spike"
"longhorn-volume-degraded"
"argocd-sync-drift"
```

---

### 14.2 Validate live rule evaluations

```bash
curl http://localhost:8000/api/v1/incidents/frontend-availability/live/evaluations | jq
```

On a healthy cluster, expected behavior:

```text
all platform scenario rules should show "matched": false
```

Some platform signals may show:

```json
"actual": null
```

This is acceptable at this phase if live collectors for Cilium, Longhorn, Argo CD, and extended Kubernetes conditions have not yet been implemented.

---

### 14.3 Validate synthetic platform scenario through generic evaluate

Example: NodeNotReady.

```bash
curl -X POST http://localhost:8000/api/v1/incidents/evaluate   -H "Content-Type: application/json"   -d '{
    "signals": {
      "probe_success": 1,
      "frontend_availability_5m": 1.0,
      "alert_state": "inactive",
      "frontend_endpoints": "10.244.8.229:8080",
      "frontend_pod_ready": true,
      "frontend_pod_status": "1/1 Running",
      "frontend_logs": "mostly INFO",
      "frontend_error_log_count": 0,
      "frontend_5xx_rate": 0.0,
      "frontend_latency_p95_ms": 120,
      "transaction_error_rate": 0.0,
      "backend_timeout_count": 0,
      "ledger_database_error_count": 0,
      "pod_crashloop": false,
      "image_pull_backoff": false,
      "failed_scheduling": false,
      "node_not_ready": true,
      "oom_killed": false,
      "pvc_mount_failure": false,
      "cilium_drop_count": 0,
      "longhorn_volume_degraded": false,
      "argocd_sync_status": "Synced"
    }
  }' | jq
```

Expected important response fields:

```json
{
  "matched": true,
  "decision": {
    "likely_root_cause": {
      "category": "node-health"
    }
  }
}
```

---

## 15. Important interpretation of `null` live values

During manual validation, the normalized signals endpoint may show:

```json
{
  "name": "node_not_ready",
  "value": null
}
```

or:

```json
{
  "name": "cilium_drop_count",
  "value": null
}
```

This does **not** mean Phase 24 failed.

It means the platform scenario model and rule engine support those signals, but the live collectors for those systems are not fully implemented yet.

This will be handled later in collector expansion phases.

Recommended interpretation:

```text
Rule/model support: implemented
Live collector support: partial / future expansion
```

---

## 16. Success criteria

Phase 24 is complete when:

```text
Platform rule YAML files exist
Platform scenario definitions exist
Scenario registry lists platform scenarios
MultiRuleEngine can match platform scenarios in tests
Missing signals do not accidentally match rules
Scenario API lists platform scenarios
Rule evaluation endpoint evaluates platform rules
Full pytest passes
```

---

## 17. Git commit

After validation:

```bash
git status
```

Then:

```bash
git add app/rules         app/engine/sample_signals.py         app/signals/frontend_availability.py         app/scenarios/frontend_availability.py         app/scenarios/registry.py         app/tests/test_platform_scenarios.py         app/engine/decision_engine.py
```

Commit:

```bash
git commit -m "feat: add platform incident scenarios"
git push
```

---

## 18. What Phase 24 gives the project

Before Phase 24:

```text
The platform could reason about workload-side degradation and frontend service-routing failures.
```

After Phase 24:

```text
The platform can reason about Kubernetes and platform-level failure signals:
CrashLoopBackOff, ImagePullBackOff, scheduling failures, node health, memory pressure,
storage mount problems, Cilium drops, Longhorn volume degradation, and Argo CD drift.
```

This turns the project into a stronger SRE decision platform because it can now connect:

```text
User impact
+
Application symptoms
+
Kubernetes/platform context
=
Decision intelligence
```

---

## 19. Next phase

The next planned phase is:

```text
Phase 25 — Generic Evaluate / Persist / Resolve API
```

Phase 25 makes the scenario/rule engine usable through generic API endpoints instead of relying mainly on frontend-specific endpoints.
