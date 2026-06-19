# Phase 29G — Pod Security Admission + Runtime Security Baseline

## Project

**SRE Decision Intelligence Platform**

## Phase status

**Enterprise implementation guide / documentation**

Phase 29G introduces a Kubernetes runtime security baseline for the `sre-decision-intelligence` namespace and its workloads.

This phase is about making the platform behave like an enterprise Kubernetes workload, not just an application that happens to run in a cluster.

It covers:

```text
Pod Security Admission
Pod Security Standards
restricted profile rollout strategy
namespace security labels
non-root workload execution
read-only root filesystem
Linux capabilities
seccomp
LimitRange
ResourceQuota
runtime validation
security test commands
common troubleshooting
```

---

## 1. Why Phase 29G exists

Before this phase, the platform already included:

```text
API runs as non-root
API uses read-only root filesystem
API drops Linux capabilities
API disables privilege escalation
API has resource requests and limits
PostgreSQL runs as StatefulSet with PVC
PostgreSQL is internal-only
ServiceAccount and RBAC are read-only
Cilium Gateway controls north-south access
CiliumNetworkPolicy controls traffic
```

However, those controls exist mostly at the workload manifest level.

Phase 29G adds **namespace-level admission guardrails** so Kubernetes itself can warn, audit, or reject insecure pods before they run.

Enterprise Kubernetes platforms do not rely only on developer discipline. They enforce baseline controls through admission policy, runtime policy, RBAC, network policy, and resource governance.

---

## 2. Core concept: Pod Security Admission

**Pod Security Admission** is the built-in Kubernetes admission controller that applies Pod Security Standards to pods at namespace level.

It uses namespace labels:

```text
pod-security.kubernetes.io/enforce
pod-security.kubernetes.io/audit
pod-security.kubernetes.io/warn
```

Each mode has a different purpose:

| Mode | Behavior | Enterprise use |
|---|---|---|
| `warn` | Allows pod creation but prints warnings | Developer feedback |
| `audit` | Allows pod creation but records audit annotations | Central audit visibility |
| `enforce` | Rejects non-compliant pods | Real guardrail enforcement |

Recommended rollout:

```text
Start with warn + audit
Fix violations
Move to enforce
Keep all three modes active
```

---

## 3. Core concept: Pod Security Standards

Kubernetes defines three standard policy levels:

| Level | Meaning | Use case |
|---|---|---|
| `privileged` | Almost unrestricted | System components only |
| `baseline` | Blocks known privilege escalations | General workloads with moderate hardening |
| `restricted` | Strongest built-in hardening profile | Enterprise workloads requiring strong isolation |

For this platform, the target is:

```text
restricted
```

because the Decision Intelligence API is part of a platform/security/SRE system and should not run with unnecessary privileges.

---

## 4. Target security posture

The target for the `sre-decision-intelligence` namespace is:

```text
Pod Security Admission: restricted
Runtime user: non-root
Privilege escalation: disabled
Linux capabilities: drop ALL
Seccomp: RuntimeDefault
API root filesystem: read-only
Writable path: /tmp only
Resources: requests and limits required
Namespace quota: enabled
PostgreSQL: internal-only and restricted as far as stateful DB allows
```

---

## 5. Workload-specific security goals

### 5.1 API Deployment

The API should be the most hardened workload.

Expected controls:

```text
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
fsGroup: 10001
seccompProfile: RuntimeDefault
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities.drop: ALL
/tmp mounted as emptyDir
resource requests/limits
livenessProbe
readinessProbe
```

Why this matters:

| Control | Why it matters |
|---|---|
| non-root user | Reduces impact if process is compromised |
| read-only root filesystem | Prevents runtime modification of container filesystem |
| `/tmp` emptyDir | Gives controlled writable space only where needed |
| drop capabilities | Removes unnecessary Linux kernel privileges |
| no privilege escalation | Prevents gaining more privileges inside the container |
| seccomp RuntimeDefault | Uses default syscall filtering |
| resource limits | Prevents runaway process from exhausting node resources |

---

### 5.2 Migration Job

The migration Job should follow the same runtime-hardening pattern as the API.

Expected controls:

```text
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
fsGroup: 10001
seccompProfile: RuntimeDefault
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities.drop: ALL
/tmp mounted as emptyDir
resource requests/limits
restartPolicy: Never
```

Why:

```text
Database schema migration is a privileged operational activity, but the container itself does not need Linux privileges.
```

The Job should only have the database credentials needed to run:

```text
alembic upgrade head
```

It should not have cluster-admin permissions.

---

### 5.3 PostgreSQL StatefulSet

PostgreSQL is different from the API because it is a stateful database and needs writable storage.

Expected controls:

```text
StatefulSet
Longhorn-backed PVC
internal-only service
resource requests/limits
livenessProbe
readinessProbe
allowPrivilegeEscalation: false
capabilities.drop: ALL
seccompProfile: RuntimeDefault
fsGroup aligned with postgres user
NetworkPolicy allows only API ingress
```

Important:

```text
Do not force readOnlyRootFilesystem: true for PostgreSQL unless all required writable paths are explicitly mounted and tested.
```

For PostgreSQL, the data directory must remain writable:

```text
/var/lib/postgresql/data
```

The enterprise target is not to make PostgreSQL read-only. The target is controlled writes, non-root runtime, no privilege escalation, internal-only access, and backup/restore readiness.

---

## 6. Namespace security labels

The namespace should first be configured with `warn` and `audit`.

File:

```text
k8s/base/postgres/namespace.yaml
```

Recommended Stage 1 namespace manifest:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sre-decision-intelligence
  labels:
    app.kubernetes.io/name: sre-decision-intelligence
    app.kubernetes.io/part-of: sre-decision-intelligence-platform

    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: latest
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: latest
```

Apply:

```bash
kubectl apply -f k8s/base/postgres/namespace.yaml
```

Validate:

```bash
kubectl get namespace sre-decision-intelligence --show-labels
```

Expected:

```text
pod-security.kubernetes.io/audit=restricted
pod-security.kubernetes.io/warn=restricted
```

---

## 7. Move to enforce mode

After API, migration Job, and PostgreSQL run cleanly without restricted warnings, patch the namespace:

```bash
kubectl label namespace sre-decision-intelligence \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=latest \
  --overwrite
```

Validate:

```bash
kubectl get namespace sre-decision-intelligence --show-labels
```

Expected labels:

```text
pod-security.kubernetes.io/enforce=restricted
pod-security.kubernetes.io/audit=restricted
pod-security.kubernetes.io/warn=restricted
```

This means:

```text
warn: developers see issues immediately
audit: violations are logged
enforce: violating pods are rejected
```

---

## 8. API Deployment security baseline

File:

```text
k8s/base/api/api-deployment.yaml
```

Expected pod-level security context:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  fsGroup: 10001
  seccompProfile:
    type: RuntimeDefault
```

Expected container-level security context:

```yaml
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

Expected writable temporary storage:

```yaml
volumeMounts:
  - name: tmp
    mountPath: /tmp

volumes:
  - name: tmp
    emptyDir: {}
```

Expected resources:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

Expected probes:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: http

readinessProbe:
  httpGet:
    path: /health/db
    port: http
```

Probe split:

| Probe | Endpoint | Purpose |
|---|---|---|
| liveness | `/health` | Restart pod if app process is unhealthy |
| readiness | `/health/db` | Remove pod from traffic if DB is unavailable |

Do not use `/health/db` for liveness. A temporary database outage should not automatically restart the API container.

---

## 9. Migration Job security baseline

File:

```text
k8s/base/migration/migration-job.yaml
```

Expected pod-level security context:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  fsGroup: 10001
  seccompProfile:
    type: RuntimeDefault
```

Expected container-level security context:

```yaml
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

Expected writable temporary storage:

```yaml
volumeMounts:
  - name: tmp
    mountPath: /tmp

volumes:
  - name: tmp
    emptyDir: {}
```

Expected resources:

```yaml
resources:
  requests:
    cpu: 50m
    memory: 128Mi
  limits:
    cpu: 250m
    memory: 256Mi
```

---

## 10. PostgreSQL StatefulSet security baseline

File:

```text
k8s/base/postgres/postgres-statefulset.yaml
```

Recommended pod-level security context:

```yaml
securityContext:
  fsGroup: 999
  seccompProfile:
    type: RuntimeDefault
```

If the official PostgreSQL image runs correctly as UID `999`, make it explicit:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 999
  runAsGroup: 999
  fsGroup: 999
  seccompProfile:
    type: RuntimeDefault
```

Recommended container-level security context:

```yaml
securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

Do not set this blindly:

```yaml
readOnlyRootFilesystem: true
```

because PostgreSQL may need writable paths besides the mounted data directory depending on image behavior.

---

## 11. LimitRange

Pod Security Admission does not enforce CPU/memory defaults.

Add a LimitRange.

File:

```text
k8s/base/security/limitrange.yaml
```

Manifest:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: sre-decision-default-limits
  namespace: sre-decision-intelligence
  labels:
    app.kubernetes.io/name: sre-decision-security-baseline
    app.kubernetes.io/component: runtime-security
    app.kubernetes.io/part-of: sre-decision-intelligence-platform
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: 100m
        memory: 128Mi
      default:
        cpu: 500m
        memory: 512Mi
      min:
        cpu: 25m
        memory: 64Mi
      max:
        cpu: "1"
        memory: 1Gi
```

Purpose:

```text
Prevent containers from being created without reasonable resource defaults.
```

---

## 12. ResourceQuota

Add a namespace quota.

File:

```text
k8s/base/security/resourcequota.yaml
```

Manifest:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: sre-decision-namespace-quota
  namespace: sre-decision-intelligence
  labels:
    app.kubernetes.io/name: sre-decision-security-baseline
    app.kubernetes.io/component: runtime-security
    app.kubernetes.io/part-of: sre-decision-intelligence-platform
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.cpu: "4"
    limits.memory: 8Gi
    pods: "20"
    services: "10"
    secrets: "20"
    configmaps: "20"
    persistentvolumeclaims: "5"
```

Purpose:

```text
Prevent namespace-level resource exhaustion and uncontrolled object growth.
```

---

## 13. Security kustomization

File:

```text
k8s/base/security/kustomization.yaml
```

Manifest:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - limitrange.yaml
  - resourcequota.yaml
```

Apply:

```bash
kubectl apply -k k8s/base/security
```

Validate:

```bash
kubectl -n sre-decision-intelligence get limitrange
kubectl -n sre-decision-intelligence get resourcequota
kubectl -n sre-decision-intelligence describe resourcequota sre-decision-namespace-quota
```

---

## 14. Validate Pod Security warnings

After enabling warn/audit restricted, reapply workloads:

```bash
kubectl apply -k k8s/base/postgres
kubectl apply -k k8s/base/migration
kubectl apply -k k8s/base/api
kubectl apply -k k8s/base/gateway
```

Watch for warnings such as:

```text
would violate PodSecurity "restricted:latest"
```

Common warnings:

| Warning | Meaning | Fix |
|---|---|---|
| `allowPrivilegeEscalation != false` | Container could escalate privileges | Set `allowPrivilegeEscalation: false` |
| `unrestricted capabilities` | Container keeps default Linux capabilities | Drop `ALL` |
| `runAsNonRoot != true` | Pod may run as root | Set `runAsNonRoot: true` |
| `seccompProfile` missing | No seccomp profile defined | Set `RuntimeDefault` |
| `privileged=true` | Container is privileged | Remove privileged mode |
| `hostPath` volume | Host filesystem access | Avoid unless absolutely required |

---

## 15. Validate enforce mode with a bad pod

After setting `enforce=restricted`, test that Kubernetes rejects a privileged pod:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: psa-should-fail
  namespace: sre-decision-intelligence
spec:
  containers:
    - name: bad
      image: busybox
      command: ["sh", "-c", "sleep 3600"]
      securityContext:
        privileged: true
EOF
```

Expected:

```text
Error from server (Forbidden): pods "psa-should-fail" is forbidden
```

Cleanup if needed:

```bash
kubectl -n sre-decision-intelligence delete pod psa-should-fail --ignore-not-found
```

This proves the namespace guardrail works.

---

## 16. Validate API runtime identity

Get API pod:

```bash
API_POD=$(kubectl -n sre-decision-intelligence get pod \
  -l app.kubernetes.io/name=sre-decision-api \
  -o jsonpath='{.items[0].metadata.name}')

echo $API_POD
```

Check user:

```bash
kubectl -n sre-decision-intelligence exec -it "$API_POD" -- id
```

Expected:

```text
uid=10001 gid=10001
```

---

## 17. Validate read-only API root filesystem

Try writing to root filesystem:

```bash
kubectl -n sre-decision-intelligence exec -it "$API_POD" -- sh -c 'touch /test-file'
```

Expected:

```text
Read-only file system
```

Validate `/tmp` works:

```bash
kubectl -n sre-decision-intelligence exec -it "$API_POD" -- sh -c 'touch /tmp/test-file && echo ok'
```

Expected:

```text
ok
```

This proves the application has only controlled write access.

---

## 18. Validate API still works

Through Gateway:

```bash
curl -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/health | jq
```

```bash
curl -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/health/db | jq
```

Expected:

```text
API healthy
DB healthy
```

Validate SLO API:

```bash
curl -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/api/v1/slo | jq
```

---

## 19. Validate PostgreSQL runtime

Check PostgreSQL pod user:

```bash
kubectl -n sre-decision-intelligence exec -it sre-decision-postgres-0 -- id
```

Expected if explicit non-root is configured:

```text
uid=999 gid=999
```

Validate DB still works:

```bash
kubectl -n sre-decision-intelligence exec -it sre-decision-postgres-0 -- \
  psql -U sre -d sre_decision_intelligence -c "SELECT 1;"
```

Expected:

```text
1
```

---

## 20. Validate quota and limits

Check quota:

```bash
kubectl -n sre-decision-intelligence describe resourcequota sre-decision-namespace-quota
```

Check LimitRange:

```bash
kubectl -n sre-decision-intelligence describe limitrange sre-decision-default-limits
```

Check workload resources:

```bash
kubectl -n sre-decision-intelligence get pod "$API_POD" -o jsonpath='{.spec.containers[0].resources}{"\n"}'
kubectl -n sre-decision-intelligence get pod sre-decision-postgres-0 -o jsonpath='{.spec.containers[0].resources}{"\n"}'
```

Expected:

```text
requests and limits are set
```

---

## 21. Runtime baseline checklist

| Control | API | Migration Job | PostgreSQL |
|---|---:|---:|---:|
| `runAsNonRoot` | yes | yes | target yes |
| non-root UID | `10001` | `10001` | usually `999` |
| `allowPrivilegeEscalation: false` | yes | yes | yes |
| `capabilities.drop: ALL` | yes | yes | yes |
| `seccompProfile: RuntimeDefault` | yes | yes | yes |
| read-only root filesystem | yes | yes | no / conditional |
| writable `/tmp` only | yes | yes | no |
| resource requests | yes | yes | yes |
| resource limits | yes | yes | yes |
| liveness/readiness probes | yes | n/a | yes |
| NetworkPolicy/CiliumNetworkPolicy | yes | n/a | yes |
| external exposure | Gateway only | no | no |

---

## 22. Common issue: PostgreSQL rejected by restricted policy

If PostgreSQL fails after enforcing restricted, check warnings:

```bash
kubectl describe pod -n sre-decision-intelligence sre-decision-postgres-0
```

Common causes:

```text
runAsNonRoot missing
seccompProfile missing
capabilities not dropped
allowPrivilegeEscalation not false
```

Fix the pod or container securityContext.

If the official image requires a specific UID/GID, use that UID explicitly rather than running as root.

---

## 23. Common issue: API cannot write temporary files

If the API crashes with errors involving `/tmp`, ensure:

```yaml
volumeMounts:
  - name: tmp
    mountPath: /tmp

volumes:
  - name: tmp
    emptyDir: {}
```

If a Python library writes to another path, add a specific `emptyDir` for that path.

Do not disable the read-only root filesystem unless absolutely necessary.

---

## 24. Common issue: ResourceQuota blocks rollout

If new pods fail with quota errors:

```bash
kubectl -n sre-decision-intelligence describe resourcequota sre-decision-namespace-quota
```

Either:

```text
lower resource requests
increase quota
remove unused pods/jobs
```

Enterprise approach:

```text
Do not remove ResourceQuota permanently.
Adjust capacity intentionally.
```

---

## 25. Why this matters in an enterprise interview

You can explain:

```text
I did not only deploy the API to Kubernetes. I hardened the namespace and workloads using Kubernetes-native security controls. I applied Pod Security Admission with the restricted profile, validated warnings before enforcement, enforced non-root runtime, disabled privilege escalation, dropped Linux capabilities, used RuntimeDefault seccomp, applied resource quotas and limits, and validated enforcement by attempting to create a privileged pod.
```

That is a strong Platform/SRE/DevSecOps answer.

---

## 26. How this connects to Cilium and GitOps

Pod Security Admission controls pod specifications at admission time.

Cilium controls network behavior at runtime.

GitOps controls desired state.

Together:

```text
GitOps defines desired manifests
Pod Security Admission rejects insecure pods
Cilium restricts runtime traffic
RBAC restricts API permissions
ResourceQuota restricts resource consumption
```

This is enterprise platform layering.

---

## 27. Files created or updated

Expected files:

```text
k8s/base/postgres/namespace.yaml
k8s/base/security/limitrange.yaml
k8s/base/security/resourcequota.yaml
k8s/base/security/kustomization.yaml
```

Existing files to verify:

```text
k8s/base/api/api-deployment.yaml
k8s/base/migration/migration-job.yaml
k8s/base/postgres/postgres-statefulset.yaml
```

---

## 28. Recommended commit

After validation:

```bash
git status
```

Then:

```bash
git add k8s/base/postgres/namespace.yaml \
        k8s/base/security \
        k8s/base/api/api-deployment.yaml \
        k8s/base/migration/migration-job.yaml \
        k8s/base/postgres/postgres-statefulset.yaml
```

Commit:

```bash
git commit -m "feat: add pod security admission and runtime baseline"
git push
```

---

## 29. Phase 29G success criteria

Phase 29G is complete when:

```text
Namespace has PSA warn/audit restricted
Workloads show no restricted warnings
Namespace moves to enforce restricted
Privileged test pod is rejected
API still runs
PostgreSQL still runs
Migration Job still runs
LimitRange exists
ResourceQuota exists
API runs as non-root
API root filesystem is read-only
/tmp remains writable
Gateway health checks still work
Resource requests and limits are defined
```

---

## 30. Next enterprise phase

Recommended next phase:

```text
Phase 29H — Secret Management Strategy for GitOps
```

Why:

```text
Before moving manifests into a GitOps repository, we must avoid committing plaintext database credentials.
```

After that:

```text
Phase 30 — GitOps Repo + Argo CD Deployment
Phase 31 — CI Pipeline: Test, Build, Scan, SBOM, Sign, Push
```
