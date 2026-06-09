# Decision Engine

## Objective

The Decision Engine is the core reasoning layer of the SRE Decision Intelligence Platform.

It converts normalized signals into:

- impact
- evidence
- likely root cause
- confidence
- safe action

The engine should not guess blindly.

It should make decisions based on explicit rules, validated evidence, and clear correlation logic.

---

## First Supported Scenario

```text
Bank of Anthos frontend availability breach
```

Validated incident evidence:

```text
probe_success = 0
availability = 0.7
alertstate = pending
frontend endpoints = <none>
frontend pod = 1/1 Running
frontend logs = mostly INFO
```

Expected decision:

```text
Likely root cause: frontend Service selector mismatch
Safe action: restore the frontend Service selector
```

---

## Engine Flow

```text
Raw signals
    ↓
Signal classifier
    ↓
Correlation layer
    ↓
Rule evaluation
    ↓
Impact analysis
    ↓
Root cause analysis
    ↓
Safe action mapping
    ↓
Decision output
```

---

## Engine Components

### 1. Signal Classifier

The classifier converts raw metrics, logs, and Kubernetes state into normalized signal types.

Example:

```text
probe_success = 0
```

becomes:

```json
{
  "type": "availability_failure",
  "source": "prometheus",
  "service": "frontend",
  "severity": "warning",
  "meaning": "Frontend probe failed"
}
```

### 2. Correlator

The correlator combines signals that belong to the same incident context.

Example correlation:

```text
probe_success = 0
frontend endpoints = <none>
frontend pod = Running
```

Correlation result:

```text
User-facing service path failed, but pod did not crash.
```

### 3. Decision Engine

The decision engine evaluates rules and chooses the most likely explanation.

It answers:

- What happened?
- Which evidence supports it?
- What is the likely root cause?
- How confident are we?
- What action is safe?

### 4. Safe Action Mapper

The safe action mapper converts root cause categories into recommended actions.

Example:

```text
Root cause category: service-routing
```

Safe action:

```text
Restore the Service selector so it matches the pod labels.
```

---

## Rule Format

Rules should be readable and stored as YAML.

Example:

```yaml
id: frontend-service-selector-mismatch
name: Frontend Service Selector Mismatch
scenario: frontend-availability-breach
severity: warning

conditions:
  - signal: probe_success
    operator: equals
    value: 0

  - signal: frontend_endpoints
    operator: equals
    value: none

  - signal: frontend_pod_ready
    operator: equals
    value: true

decision:
  impact: Frontend endpoint unavailable
  likely_root_cause: Frontend Service selector does not match frontend pod labels
  confidence: high
  safe_action: Restore the frontend Service selector
  category: service-routing
```

---

## Initial Rule: Service Selector Mismatch

### Logic

```text
IF probe_success = 0
AND frontend Service endpoints are empty
AND frontend pod is Running/Ready
THEN likely root cause = Service selector mismatch
```

### Why this rule is valid

The frontend probe confirms user-facing failure.

The empty endpoint list confirms the frontend Service has no backend pod.

The running frontend pod confirms the pod itself did not crash.

Together, these signals point to a Service routing problem.

---

## Additional Future Rules

### Pod Crash / Rollout Failure

```text
IF probe_success = 0
AND frontend pod is not Ready
AND restart count increased
THEN likely root cause = frontend pod crash or rollout regression
```

### Application Error

```text
IF probe_success = 0
AND frontend endpoints exist
AND frontend pod is Ready
AND OpenSearch shows elevated ERROR logs
THEN likely root cause = application-level failure
```

### Network Policy / Cilium Drop

```text
IF probe_success = 0
AND endpoints exist
AND pod is Ready
AND Cilium/Hubble shows traffic drops
THEN likely root cause = network policy or connectivity issue
```

### Storage Problem

```text
IF application errors mention database/storage
AND Longhorn shows volume attach/degraded events
THEN likely root cause = storage-related service degradation
```

### GitOps Rollout Regression

```text
IF SLO breach occurs shortly after Argo CD sync
AND deployment/pod instability appears
THEN likely root cause = rollout regression
```

---

## Confidence Model

Initial confidence can be rule-based.

| Confidence | Meaning |
|---|---|
| high | Multiple independent signals support the same cause |
| medium | Main signal and one supporting signal agree |
| low | Evidence is incomplete or conflicting |

For the first scenario:

```text
probe_success = 0
endpoints = <none>
pod = Running
```

Confidence:

```text
high
```

---

## Decision Output

The engine should produce:

```json
{
  "impact": "Frontend endpoint unavailable",
  "evidence": [
    "probe_success = 0",
    "frontend endpoints = <none>",
    "frontend pod = 1/1 Running"
  ],
  "likely_root_cause": "Service selector mismatch",
  "confidence": "high",
  "safe_action": "Restore the frontend Service selector"
}
```

---

## Design Constraints

The first version should be:

- deterministic
- rule-based
- explainable
- testable
- easy to extend

It should not:

- make unsafe automatic changes
- hide raw evidence
- invent causes without supporting signals
- depend on AI generation for correctness

---

## Testing Strategy

Each decision rule should have tests.

Example tests:

```text
test_service_selector_mismatch_detected
test_pod_crash_not_misclassified_as_selector_mismatch
test_application_error_not_misclassified_as_service_routing
test_decision_output_contains_safe_action
```

---

## Future Direction

Later versions can add:

- live collector integration
- rule scoring
- historical decision storage
- PostgreSQL-backed decision history
- Argo CD change correlation
- Cilium/Hubble network evidence
- optional LLM-generated incident summaries based only on verified evidence
