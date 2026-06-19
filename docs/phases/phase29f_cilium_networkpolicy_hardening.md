# Phase 29F — Cilium NetworkPolicy Hardening

## Project

**SRE Decision Intelligence Platform**

## Phase status

**Enterprise implementation guide / documentation**

Phase 29F adds network-level isolation using **CiliumNetworkPolicy**.

This phase hardens the runtime communication paths for the platform after the internal API Deployment and Cilium Gateway have been introduced.

The goal is to move from:

```text
Pods can talk freely inside the cluster
```

to:

```text
Only explicitly approved traffic is allowed
```

This is a core enterprise Kubernetes security practice.

---

## 1. Why Phase 29F exists

The platform currently contains several components:

```text
sre-decision-api
PostgreSQL StatefulSet
Cilium Gateway / HTTPRoute
Prometheus
OpenSearch
Kubernetes API
DNS
```

Without network policy, Kubernetes networking is usually permissive by default. That means unrelated pods may be able to attempt connections to internal services such as PostgreSQL or the API.

For an enterprise platform, that is not acceptable.

Phase 29F introduces explicit traffic rules:

```text
Gateway / approved clients → API
API → PostgreSQL
API → Kubernetes API
API → Prometheus
API → OpenSearch
API → DNS
API → nothing else
Other pods → PostgreSQL denied
PostgreSQL → broad egress denied
```

---

## 2. Enterprise security principle

The principle is:

```text
Default deny, explicit allow
```

That means services should not trust each other just because they are in the same cluster.

Instead, communication must be intentionally declared.

This gives:

```text
reduced lateral movement risk
stronger blast-radius control
clear documentation of allowed dependencies
auditable network paths
better alignment with zero-trust networking
```

---

## 3. High-level network architecture

```text
Client / Engineer / Platform Tool
        ↓
Cilium L2 announced Gateway IP
        ↓
Cilium Gateway
        ↓
HTTPRoute
        ↓
sre-decision-api Service :8000
        ↓
sre-decision-api Pod
        ↓
PostgreSQL :5432
```

Additional egress from API:

```text
sre-decision-api → Kubernetes API
sre-decision-api → Prometheus
sre-decision-api → OpenSearch
sre-decision-api → DNS
```

PostgreSQL remains:

```text
internal-only
not exposed through Gateway
not exposed by LoadBalancer
not reachable from random pods
```

---

## 4. What Phase 29F protects

| Component | Protection |
|---|---|
| API | Only approved ingress and required egress |
| PostgreSQL | Only API can connect |
| DNS | Explicitly allowed |
| Kubernetes API | Explicitly allowed for collectors |
| Prometheus | Explicitly allowed for metrics queries |
| OpenSearch | Explicitly allowed for log context |
| Random workloads | Blocked from database |
| External clients | Must enter through Gateway path |

---

## 5. What Phase 29F does not replace

CiliumNetworkPolicy does not replace:

```text
RBAC
Pod Security Admission
Secrets management
image scanning
API authentication
TLS/mTLS
database backup/restore
```

It complements them.

Layered model:

```text
RBAC controls Kubernetes API permissions
Pod Security Admission controls pod specs
CiliumNetworkPolicy controls network traffic
Secrets management controls sensitive data
CI scanning controls supply-chain risk
Gateway controls north-south routing
```

---

## 6. Expected folder structure

Create:

```text
k8s/base/network/
├── api-cilium-network-policy.yaml
├── postgres-cilium-network-policy.yaml
└── kustomization.yaml
```

---

## 7. Create network folder

```bash
mkdir -p k8s/base/network
```

---

## 8. Pre-checks before policy

Before applying policies, confirm Cilium CRDs exist:

```bash
kubectl get crd | grep ciliumnetworkpolicies
```

Expected:

```text
ciliumnetworkpolicies.cilium.io
```

Confirm API and PostgreSQL pods exist:

```bash
kubectl -n sre-decision-intelligence get pods
```

Confirm pod labels:

```bash
kubectl -n sre-decision-intelligence get pods --show-labels
```

You must see API labels:

```text
app.kubernetes.io/name=sre-decision-api
app.kubernetes.io/component=api
```

And PostgreSQL labels:

```text
app.kubernetes.io/name=sre-decision-postgres
app.kubernetes.io/component=database
```

These labels are what the policies select.

If labels do not match, policies will not apply to the intended pods.

---

## 9. Inspect Gateway identity before tightening

Because traffic enters through Cilium Gateway, inspect the generated Gateway service:

```bash
kubectl -n sre-decision-intelligence get svc --show-labels
```

Likely Gateway service:

```text
cilium-gateway-sre-decision-gateway
```

Inspect it:

```bash
kubectl -n sre-decision-intelligence get svc cilium-gateway-sre-decision-gateway -o yaml
```

Also inspect Cilium/Envoy/Gateway pods if present:

```bash
kubectl get pods -A --show-labels | grep -Ei "gateway|envoy|cilium"
```

This is needed because the final API ingress policy should ideally allow traffic from the real Gateway identity, not from the entire cluster.

For the first policy version, allow cluster ingress to API port `8000`, then tighten after Hubble confirms the real source identity.

---

## 10. API CiliumNetworkPolicy

File:

```text
k8s/base/network/api-cilium-network-policy.yaml
```

Create:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: sre-decision-api-network-policy
  namespace: sre-decision-intelligence
  labels:
    app.kubernetes.io/name: sre-decision-api
    app.kubernetes.io/component: network-policy
    app.kubernetes.io/part-of: sre-decision-intelligence-platform
spec:
  endpointSelector:
    matchLabels:
      app.kubernetes.io/name: sre-decision-api
      app.kubernetes.io/component: api

  ingress:
    # Allow HTTP traffic to the API from inside the cluster.
    # This supports Cilium Gateway traffic during the first validation.
    # After observing Gateway traffic identity, tighten this rule.
    - fromEntities:
        - cluster
      toPorts:
        - ports:
            - port: "8000"
              protocol: TCP

  egress:
    # Allow DNS resolution.
    - toEndpoints:
        - matchLabels:
            io.kubernetes.pod.namespace: kube-system
            k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
            - port: "53"
              protocol: TCP

    # Allow access to Kubernetes API server for in-cluster collectors.
    - toEntities:
        - kube-apiserver

    # Allow API to connect to PostgreSQL.
    - toEndpoints:
        - matchLabels:
            io.kubernetes.pod.namespace: sre-decision-intelligence
            app.kubernetes.io/name: sre-decision-postgres
            app.kubernetes.io/component: database
      toPorts:
        - ports:
            - port: "5432"
              protocol: TCP

    # Allow API to connect to Prometheus.
    # Start namespace-wide, then tighten after confirming labels.
    - toEndpoints:
        - matchLabels:
            io.kubernetes.pod.namespace: monitoring
      toPorts:
        - ports:
            - port: "9090"
              protocol: TCP

    # Allow API to connect to OpenSearch.
    # Adjust namespace/labels/port if your deployment differs.
    - toEndpoints:
        - matchLabels:
            io.kubernetes.pod.namespace: logging
      toPorts:
        - ports:
            - port: "9200"
              protocol: TCP
```

---

## 11. API policy explanation

### 11.1 Endpoint selector

```yaml
endpointSelector:
  matchLabels:
    app.kubernetes.io/name: sre-decision-api
    app.kubernetes.io/component: api
```

This means the policy applies only to API pods.

---

### 11.2 API ingress

```yaml
ingress:
  - fromEntities:
      - cluster
    toPorts:
      - ports:
          - port: "8000"
            protocol: TCP
```

This allows cluster-origin traffic to the API on port `8000`.

Why not tighter immediately?

Because Cilium Gateway traffic identity must be observed first. Once confirmed with Hubble, this should be tightened to the Gateway source identity.

Enterprise approach:

```text
Validate function first
Observe real identity
Tighten selectors
Validate again
```

---

### 11.3 DNS egress

DNS is required so the API can resolve services such as:

```text
sre-decision-postgres
kube-prometheus-stack-prometheus.monitoring
opensearch.logging
```

Policy:

```yaml
toEndpoints:
  - matchLabels:
      io.kubernetes.pod.namespace: kube-system
      k8s-app: kube-dns
```

If your DNS pods use another label, such as `k8s-app=coredns`, adjust it.

Check DNS labels:

```bash
kubectl -n kube-system get pods --show-labels | grep -E "coredns|kube-dns"
```

---

### 11.4 Kubernetes API egress

The API uses the Kubernetes Python client for live collectors.

It needs egress to:

```text
kube-apiserver
```

Policy:

```yaml
toEntities:
  - kube-apiserver
```

This allows network reachability. RBAC still controls what the API is allowed to read.

---

### 11.5 PostgreSQL egress

The API needs database access:

```text
API → sre-decision-postgres:5432
```

Only PostgreSQL pods with the expected labels are allowed.

---

### 11.6 Prometheus egress

The API may query:

```text
Prometheus / Blackbox metrics
```

Initial policy allows namespace-wide egress to `monitoring:9090`.

Later, tighten to exact Prometheus pod labels after checking:

```bash
kubectl -n monitoring get pods --show-labels
kubectl -n monitoring get svc --show-labels
```

---

### 11.7 OpenSearch egress

The API may query OpenSearch for log context.

Initial policy allows namespace-wide egress to `logging:9200`.

Later, tighten to exact OpenSearch pod labels after checking:

```bash
kubectl -n logging get pods --show-labels
kubectl -n logging get svc --show-labels
```

---

## 12. PostgreSQL CiliumNetworkPolicy

File:

```text
k8s/base/network/postgres-cilium-network-policy.yaml
```

Create:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: sre-decision-postgres-network-policy
  namespace: sre-decision-intelligence
  labels:
    app.kubernetes.io/name: sre-decision-postgres
    app.kubernetes.io/component: network-policy
    app.kubernetes.io/part-of: sre-decision-intelligence-platform
spec:
  endpointSelector:
    matchLabels:
      app.kubernetes.io/name: sre-decision-postgres
      app.kubernetes.io/component: database

  ingress:
    # Only the Decision Intelligence API may connect to PostgreSQL.
    - fromEndpoints:
        - matchLabels:
            io.kubernetes.pod.namespace: sre-decision-intelligence
            app.kubernetes.io/name: sre-decision-api
            app.kubernetes.io/component: api
      toPorts:
        - ports:
            - port: "5432"
              protocol: TCP

  egress:
    # DNS only, if required by runtime.
    - toEndpoints:
        - matchLabels:
            io.kubernetes.pod.namespace: kube-system
            k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
            - port: "53"
              protocol: TCP
```

---

## 13. PostgreSQL policy explanation

### 13.1 Endpoint selector

```yaml
endpointSelector:
  matchLabels:
    app.kubernetes.io/name: sre-decision-postgres
    app.kubernetes.io/component: database
```

This applies only to PostgreSQL pods.

---

### 13.2 PostgreSQL ingress

```yaml
fromEndpoints:
  - matchLabels:
      io.kubernetes.pod.namespace: sre-decision-intelligence
      app.kubernetes.io/name: sre-decision-api
      app.kubernetes.io/component: api
```

Only API pods may connect.

This blocks:

```text
random pods in same namespace
workload pods from fintech-workload
pods from monitoring/logging
external clients
```

---

### 13.3 PostgreSQL egress

PostgreSQL does not need broad outbound traffic.

Allowed:

```text
DNS only
```

This reduces lateral movement risk if the database pod is compromised.

---

## 14. Network kustomization

File:

```text
k8s/base/network/kustomization.yaml
```

Create:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - api-cilium-network-policy.yaml
  - postgres-cilium-network-policy.yaml
```

Validate:

```bash
kubectl kustomize k8s/base/network
```

---

## 15. Apply policies

```bash
kubectl apply -k k8s/base/network
```

Check:

```bash
kubectl -n sre-decision-intelligence get ciliumnetworkpolicy
```

Expected:

```text
sre-decision-api-network-policy
sre-decision-postgres-network-policy
```

Describe:

```bash
kubectl -n sre-decision-intelligence describe ciliumnetworkpolicy sre-decision-api-network-policy
kubectl -n sre-decision-intelligence describe ciliumnetworkpolicy sre-decision-postgres-network-policy
```

---

## 16. Validate API through Gateway

Set Gateway IP:

```bash
export GATEWAY_IP=<your-sre-decision-gateway-ip>
```

Test:

```bash
curl -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/health | jq
```

```bash
curl -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/health/db | jq
```

```bash
curl -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/api/v1/slo | jq
```

Expected:

```text
/health works
/health/db works
/api/v1/slo works
```

Interpretation:

| Test | What it proves |
|---|---|
| `/health` works | Gateway → API traffic is allowed |
| `/health/db` works | API → PostgreSQL traffic is allowed |
| `/api/v1/slo` works | API application path is functioning |

---

## 17. Validate PostgreSQL is blocked from random pods

Create a temporary client pod:

```bash
kubectl -n sre-decision-intelligence run blocked-pg-client \
  --rm -it \
  --image=postgres:16 \
  --restart=Never \
  -- bash
```

Inside the pod:

```bash
PGPASSWORD=sre_password psql \
  -h sre-decision-postgres \
  -U sre \
  -d sre_decision_intelligence \
  -c "SELECT 1;"
```

Expected:

```text
connection timeout
```

or:

```text
connection blocked
```

Exit:

```bash
exit
```

Interpretation:

```text
Random pod → PostgreSQL is denied
```

This is one of the most important validation points.

---

## 18. Validate API can still connect to PostgreSQL

Through Gateway:

```bash
curl -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/health/db | jq
```

Expected:

```json
{
  "status": "ok"
}
```

Interpretation:

```text
API → PostgreSQL is allowed
```

---

## 19. Validate Kubernetes API access

Network policy permits Kubernetes API access, but RBAC still controls permissions.

Check RBAC:

```bash
kubectl auth can-i list pods \
  --as=system:serviceaccount:sre-decision-intelligence:sre-decision-api \
  -n fintech-workload
```

Expected:

```text
yes
```

Check mutation denial:

```bash
kubectl auth can-i delete pods \
  --as=system:serviceaccount:sre-decision-intelligence:sre-decision-api \
  -n fintech-workload
```

Expected:

```text
no
```

Test live endpoint:

```bash
curl -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/api/v1/incidents/frontend-availability/live/signals | jq
```

Possible outcomes:

| Result | Meaning |
|---|---|
| Full live signals | Kubernetes, Prometheus/OpenSearch paths work |
| Kubernetes works but Prometheus fails | Prometheus service name/policy needs tuning |
| 403 Forbidden | RBAC issue |
| timeout/drop | Cilium policy issue |
| DNS error | DNS egress policy issue |

---

## 20. Tighten Prometheus and OpenSearch selectors

Initial egress uses namespace-wide selectors:

```yaml
io.kubernetes.pod.namespace: monitoring
io.kubernetes.pod.namespace: logging
```

Enterprise target is more precise.

Find actual labels:

```bash
kubectl -n monitoring get pods --show-labels
kubectl -n monitoring get svc --show-labels

kubectl -n logging get pods --show-labels
kubectl -n logging get svc --show-labels
```

Then replace namespace-wide selectors with exact labels.

Example:

```yaml
toEndpoints:
  - matchLabels:
      io.kubernetes.pod.namespace: monitoring
      app.kubernetes.io/name: prometheus
```

Only use labels that actually exist in your cluster.

---

## 21. Tighten API ingress to Gateway identity

The first policy allows:

```yaml
fromEntities:
  - cluster
```

This is acceptable for initial validation.

Enterprise target:

```text
Only Cilium Gateway may call API externally
Approved internal namespaces may call API if needed
```

To tighten, observe the actual traffic identity with Hubble:

```bash
hubble observe --namespace sre-decision-intelligence
```

Or observe API pod traffic:

```bash
API_POD=$(kubectl -n sre-decision-intelligence get pod \
  -l app.kubernetes.io/name=sre-decision-api \
  -o jsonpath='{.items[0].metadata.name}')

hubble observe \
  --namespace sre-decision-intelligence \
  --pod "$API_POD"
```

Also observe drops:

```bash
hubble observe --verdict DROPPED
```

After identifying Gateway source labels/entity, replace broad ingress with a more precise allow rule.

---

## 22. Using Hubble for evidence

Hubble gives runtime evidence.

Useful commands:

```bash
hubble observe --namespace sre-decision-intelligence
```

```bash
hubble observe --verdict FORWARDED --namespace sre-decision-intelligence
```

```bash
hubble observe --verdict DROPPED --namespace sre-decision-intelligence
```

Expected security evidence:

```text
Gateway → API forwarded
API → PostgreSQL forwarded
random pod → PostgreSQL dropped
API → DNS forwarded
API → kube-apiserver forwarded
```

This is excellent for enterprise documentation and LinkedIn/GitHub proof.

---

## 23. Common issue: API health fails after policy

Symptom:

```text
/health fails through Gateway
```

Likely cause:

```text
API ingress policy too restrictive
Gateway traffic source not allowed
```

Temporary validation fix:

```yaml
fromEntities:
  - cluster
```

Then use Hubble to identify the source and tighten later.

---

## 24. Common issue: DB health fails after policy

Symptom:

```text
/health works
/health/db fails
```

Likely cause:

```text
API egress to PostgreSQL denied
or PostgreSQL ingress from API denied
```

Check labels:

```bash
kubectl -n sre-decision-intelligence get pods --show-labels
```

Validate the API and PostgreSQL labels match the policy selectors.

---

## 25. Common issue: DNS fails

Symptom:

```text
could not resolve host
```

Check kube-dns/CoreDNS labels:

```bash
kubectl -n kube-system get pods --show-labels | grep -E "coredns|kube-dns"
```

If your cluster uses:

```text
k8s-app=coredns
```

instead of:

```text
k8s-app=kube-dns
```

adjust the DNS selector.

---

## 26. Common issue: Prometheus/OpenSearch blocked

Symptoms:

```text
live collector timeout
connection refused
connection timeout
```

Check actual service names:

```bash
kubectl get svc -A | grep -Ei "prometheus|opensearch"
```

Check pod labels:

```bash
kubectl -n monitoring get pods --show-labels
kubectl -n logging get pods --show-labels
```

Then adjust egress policy.

---

## 27. Common issue: random pod can still reach PostgreSQL

Check:

```bash
kubectl -n sre-decision-intelligence get ciliumnetworkpolicy
```

Check PostgreSQL pod labels:

```bash
kubectl -n sre-decision-intelligence get pod sre-decision-postgres-0 --show-labels
```

Check whether the policy endpoint selector matches the PostgreSQL pod.

If it does not match, the policy does not apply.

Also check whether another broader policy allows the traffic.

---

## 28. Enterprise explanation

You can explain Phase 29F like this:

```text
I implemented CiliumNetworkPolicy to move the platform toward zero-trust networking. The API only receives traffic through the controlled Gateway path and only has egress to the services it requires: PostgreSQL, Kubernetes API, DNS, Prometheus, and OpenSearch. PostgreSQL only accepts traffic from the API and is not externally exposed. I validated the policy by confirming the API can reach the database while a random pod cannot.
```

This is a strong enterprise Platform/SRE/DevSecOps explanation.

---

## 29. Files created

```text
k8s/base/network/api-cilium-network-policy.yaml
k8s/base/network/postgres-cilium-network-policy.yaml
k8s/base/network/kustomization.yaml
```

---

## 30. Recommended commit

After validation:

```bash
git status
```

Then:

```bash
git add k8s/base/network
```

Commit:

```bash
git commit -m "feat: add Cilium network policies for API and PostgreSQL"
git push
```

---

## 31. Phase 29F success criteria

Phase 29F is complete when:

```text
CiliumNetworkPolicy exists for API
CiliumNetworkPolicy exists for PostgreSQL
API works through Cilium Gateway
API can reach PostgreSQL
API can reach Kubernetes API
API can resolve DNS
API can reach Prometheus/OpenSearch where configured
Random pods cannot connect to PostgreSQL
RBAC remains read-only
PostgreSQL has no external exposure
Policies are committed as code
```

---

## 32. Next enterprise phase

Recommended next phase:

```text
Phase 29G — Pod Security Admission + Runtime Security Baseline
```

After that:

```text
Phase 29H — Secret Management Strategy for GitOps
Phase 30 — GitOps Repo + Argo CD Deployment
Phase 31 — CI Pipeline: Test, Build, Scan, SBOM, Sign, Push
```
