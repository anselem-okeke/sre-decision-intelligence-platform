# Phase 29E — Cilium Gateway API + HTTPRoute

## Project

**SRE Decision Intelligence Platform**

## Phase status

**Enterprise implementation guide / documentation**

Phase 29E exposes the internal SRE Decision Intelligence API through **Cilium Gateway API** and **HTTPRoute**.

This phase intentionally avoids classic Ingress controllers such as NGINX or Traefik because the platform already uses Cilium as the networking layer.

The goal is to expose the API through an enterprise-style controlled entry point:

```text
Client / Engineer / Platform Tool
        ↓
Cilium L2 announced LoadBalancer IP
        ↓
Cilium Gateway
        ↓
HTTPRoute
        ↓
sre-decision-api Service
        ↓
sre-decision-api Pod
```

PostgreSQL remains internal-only and is not exposed through the Gateway.

---

## 1. Why Phase 29E exists

The API is now running as an internal Kubernetes service:

```text
sre-decision-api.sre-decision-intelligence.svc.cluster.local:8000
```

That is good for internal pod-to-pod communication, but enterprise platform services need a governed access layer for:

```text
engineers
internal dashboards
incident response tools
future UI
platform automation
CI/CD validation
SRE workflows
```

The Gateway provides that access layer without exposing the pod or service directly.

---

## 2. Why Cilium Gateway API instead of classic Ingress

Your cluster already uses:

```text
Cilium
Cilium Gateway Controller
Cilium L2 Announcements
Cilium LoadBalancer IP Pool
```

So the enterprise-aligned choice is:

```text
Gateway API + HTTPRoute
```

not:

```text
NGINX Ingress
Traefik
NodePort
direct LoadBalancer on the app service
```

Comparison:

| Approach | Enterprise fit | Comment |
|---|---:|---|
| NodePort | Low | Exposes node ports directly |
| LoadBalancer on app Service | Medium | Works but mixes app service and external exposure |
| Classic Ingress | Good | Common, but adds another controller |
| Cilium Gateway API | Strong | Uses existing Cilium datapath and Gateway API model |

Using Cilium Gateway gives:

```text
centralized traffic entry
clean hostname routing
HTTPRoute path control
better GitOps visibility
future policy integration
no extra ingress controller
alignment with Cilium L7/security capabilities
```

---

## 3. Existing cluster readiness

The cluster was validated with:

```bash
kubectl get gatewayclass

kubectl get crd | grep gateway.networking.k8s.io

kubectl get ciliuml2announcementpolicy -A

kubectl get svc -A | grep LoadBalancer

kubectl get ippool -A 2>/dev/null || true
```

Observed output confirmed:

```text
GatewayClass: cilium
Controller: io.cilium/gateway-controller
ACCEPTED: True

Gateway API CRDs installed:
- gatewayclasses.gateway.networking.k8s.io
- gateways.gateway.networking.k8s.io
- httproutes.gateway.networking.k8s.io
- referencegrants.gateway.networking.k8s.io
- tcproutes.gateway.networking.k8s.io
- tlsroutes.gateway.networking.k8s.io
- udproutes.gateway.networking.k8s.io

Cilium L2 policies:
- lan-l2-policy
- lan-lb-services-policy

Existing LoadBalancer examples:
- deploy-confidence Gateway IP: 192.168.0.230
- fintech-workload frontend IP: 192.168.0.231

Cilium LB IP pool:
- lan-pool
- disabled: false
- conflicting: false
- available IPs: 8
```

This confirms the cluster is ready for Cilium Gateway API.

---

## 4. Target traffic flow

```text
Client / Browser
        ↓
sre-decision-api.platform.local
        ↓
Cilium L2 announced LoadBalancer IP
        ↓
Cilium Gateway
        ↓
HTTPRoute rules
        ↓
sre-decision-api ClusterIP Service
        ↓
sre-decision-api Pod on port 8000
```

The API Service remains:

```text
ClusterIP
```

The Gateway owns external/north-south access.

---

## 5. Security boundary

Only the API is exposed.

PostgreSQL remains private:

```text
sre-decision-postgres:5432
```

There is no:

```text
PostgreSQL Gateway route
PostgreSQL LoadBalancer service
PostgreSQL NodePort
public database access
```

This is the correct enterprise boundary:

```text
external clients → API only
API → PostgreSQL internally
```

---

## 6. Resources introduced in Phase 29E

Phase 29E adds:

```text
k8s/base/gateway/
├── gateway.yaml
├── httproute.yaml
└── kustomization.yaml
```

Kubernetes resources:

| Resource | Purpose |
|---|---|
| `Gateway` | Defines the external HTTP listener |
| `HTTPRoute` | Defines hostname/path routing to the API Service |
| `Kustomization` | Groups Gateway resources for deployment |

---

## 7. Hostname design

Recommended hostname:

```text
sre-decision-api.platform.local
```

Why this name:

```text
clear service identity
platform-oriented
not tied to pod/service internals
works with local DNS or /etc/hosts
easy to document
```

Until real DNS exists, test with:

```bash
curl -H "Host: sre-decision-api.platform.local" http://<GATEWAY_IP>/health
```

Later, add local DNS or `/etc/hosts`:

```text
<GATEWAY_IP> sre-decision-api.platform.local
```

---

## 8. Create gateway folder

From the repository root:

```bash
mkdir -p k8s/base/gateway
```

---

## 9. Gateway manifest

File:

```text
k8s/base/gateway/gateway.yaml
```

Manifest:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: sre-decision-gateway
  namespace: sre-decision-intelligence
  labels:
    app.kubernetes.io/name: sre-decision-gateway
    app.kubernetes.io/component: gateway
    app.kubernetes.io/part-of: sre-decision-intelligence-platform
spec:
  gatewayClassName: cilium
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      hostname: sre-decision-api.platform.local
      allowedRoutes:
        namespaces:
          from: Same
```

---

## 10. Gateway manifest explanation

### 10.1 `gatewayClassName: cilium`

This tells Kubernetes:

```text
Cilium should implement this Gateway.
```

Your cluster already confirmed:

```text
GatewayClass cilium Accepted=True
```

---

### 10.2 Listener

```yaml
listeners:
  - name: http
    protocol: HTTP
    port: 80
    hostname: sre-decision-api.platform.local
```

This defines an HTTP listener on port `80` for the platform hostname.

---

### 10.3 `allowedRoutes: Same`

```yaml
allowedRoutes:
  namespaces:
    from: Same
```

This means only HTTPRoutes in the same namespace can attach to this Gateway.

That is safer than allowing arbitrary namespaces to bind routes to the Gateway.

```text
Gateway namespace: sre-decision-intelligence
HTTPRoute namespace: sre-decision-intelligence
```

---

## 11. HTTPRoute manifest

File:

```text
k8s/base/gateway/httproute.yaml
```

Manifest:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: sre-decision-api-route
  namespace: sre-decision-intelligence
  labels:
    app.kubernetes.io/name: sre-decision-api
    app.kubernetes.io/component: route
    app.kubernetes.io/part-of: sre-decision-intelligence-platform
spec:
  parentRefs:
    - name: sre-decision-gateway
      namespace: sre-decision-intelligence

  hostnames:
    - sre-decision-api.platform.local

  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /health
        - path:
            type: PathPrefix
            value: /health/db
        - path:
            type: PathPrefix
            value: /api/v1
        - path:
            type: PathPrefix
            value: /openapi.json
        - path:
            type: PathPrefix
            value: /docs
      backendRefs:
        - name: sre-decision-api
          port: 8000
```

---

## 12. HTTPRoute explanation

### 12.1 Parent reference

```yaml
parentRefs:
  - name: sre-decision-gateway
```

This attaches the route to the Gateway.

---

### 12.2 Hostname

```yaml
hostnames:
  - sre-decision-api.platform.local
```

Only requests with this host should match this route.

---

### 12.3 Allowed paths

The route exposes:

```text
/health
/health/db
/api/v1
/openapi.json
/docs
```

Why these paths:

| Path | Purpose |
|---|---|
| `/health` | Basic app health |
| `/health/db` | DB readiness validation |
| `/api/v1` | Main API surface |
| `/openapi.json` | API schema |
| `/docs` | FastAPI Swagger docs |

Enterprise note:

```text
/docs and /openapi.json are useful during platform validation.
For production, they should be restricted or disabled unless internal-only access is guaranteed.
```

---

### 12.4 Backend reference

```yaml
backendRefs:
  - name: sre-decision-api
    port: 8000
```

This sends matched traffic to the internal ClusterIP Service:

```text
sre-decision-api:8000
```

The API Service remains internal.

---

## 13. Gateway kustomization

File:

```text
k8s/base/gateway/kustomization.yaml
```

Manifest:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - gateway.yaml
  - httproute.yaml
```

Validate:

```bash
kubectl kustomize k8s/base/gateway
```

---

## 14. Pre-apply validation

Before applying Gateway resources, confirm the API Service exists:

```bash
kubectl -n sre-decision-intelligence get svc sre-decision-api
```

Expected:

```text
sre-decision-api   ClusterIP   ...   8000/TCP
```

Confirm API pod is ready:

```bash
kubectl -n sre-decision-intelligence get pods \
  -l app.kubernetes.io/name=sre-decision-api
```

Expected:

```text
READY 1/1
STATUS Running
```

Confirm PostgreSQL is not externally exposed:

```bash
kubectl -n sre-decision-intelligence get svc sre-decision-postgres
```

Expected:

```text
ClusterIP: None
Type: ClusterIP/headless
No external IP
```

---

## 15. Apply Gateway resources

```bash
kubectl apply -k k8s/base/gateway
```

Check resources:

```bash
kubectl -n sre-decision-intelligence get gateway
kubectl -n sre-decision-intelligence get httproute
```

---

## 16. Gateway status validation

Describe Gateway:

```bash
kubectl -n sre-decision-intelligence describe gateway sre-decision-gateway
```

Expected conditions:

```text
Accepted=True
Programmed=True
```

Describe HTTPRoute:

```bash
kubectl -n sre-decision-intelligence describe httproute sre-decision-api-route
```

Expected conditions:

```text
Accepted=True
ResolvedRefs=True
```

Meaning:

| Condition | Meaning |
|---|---|
| `Accepted=True` | Controller accepted the resource |
| `Programmed=True` | Gateway has been configured by implementation |
| `ResolvedRefs=True` | HTTPRoute backend references are valid |

---

## 17. Cilium L2 announcement behavior

Because the cluster uses Cilium L2 announcements, Cilium should create or manage a LoadBalancer Service for the Gateway.

Expected generated service name pattern:

```text
cilium-gateway-sre-decision-gateway
```

Check:

```bash
kubectl get svc -A | grep -Ei "sre-decision|gateway|cilium-gateway"
```

Expected:

```text
sre-decision-intelligence   cilium-gateway-sre-decision-gateway   LoadBalancer   ...   192.168.0.xxx   80/TCP
```

The external IP should come from:

```text
lan-pool
```

Your cluster already showed:

```text
lan-pool available IPs: 8
```

---

## 18. Get Gateway IP

Try:

```bash
kubectl -n sre-decision-intelligence get gateway sre-decision-gateway -o wide
```

Or:

```bash
export GATEWAY_IP=$(kubectl -n sre-decision-intelligence get gateway sre-decision-gateway \
  -o jsonpath='{.status.addresses[0].value}')

echo $GATEWAY_IP
```

Expected:

```text
192.168.0.xxx
```

If empty, check generated service:

```bash
kubectl get svc -A | grep -Ei "sre-decision|gateway"
```

Then export manually:

```bash
export GATEWAY_IP=<external-ip-from-service>
```

---

## 19. If Gateway does not get an IP

Inspect generated service:

```bash
kubectl -n sre-decision-intelligence describe svc cilium-gateway-sre-decision-gateway
```

Check Cilium L2 policies:

```bash
kubectl get ciliuml2announcementpolicy -A -o yaml
```

Check LB IP pools:

```bash
kubectl get ippool -A 2>/dev/null || true
kubectl get ciliumloadbalancerippool -A
```

Check Gateway events:

```bash
kubectl -n sre-decision-intelligence describe gateway sre-decision-gateway
```

Possible causes:

```text
no available IP in pool
L2 announcement policy selector does not match service
Gateway service labels do not match L2 policy
Gateway controller issue
```

Because your cluster already has working Cilium Gateway and LoadBalancer services, this is likely to work.

---

## 20. Test through Gateway with Host header

Test basic health:

```bash
curl -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/health | jq
```

Expected:

```json
{
  "status": "ok"
}
```

Test DB health:

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

Test SLO API:

```bash
curl -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/api/v1/slo | jq
```

Expected:

```text
List of registered SLOs
```

Test OpenAPI docs:

```bash
curl -I -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/docs
```

Expected:

```text
HTTP/1.1 200 OK
```

---

## 21. Add local DNS entry

Once Gateway IP is confirmed, add a local hosts entry.

Linux:

```bash
sudo nano /etc/hosts
```

Add:

```text
192.168.0.xxx sre-decision-api.platform.local
```

Windows hosts file:

```text
C:\Windows\System32\drivers\etc\hosts
```

Add:

```text
192.168.0.xxx sre-decision-api.platform.local
```

Then test without Host header:

```bash
curl http://sre-decision-api.platform.local/health | jq
curl http://sre-decision-api.platform.local/api/v1/slo | jq
```

---

## 22. Validate unknown paths

Run:

```bash
curl -i -H "Host: sre-decision-api.platform.local" \
  http://$GATEWAY_IP/unknown
```

Expected:

```text
404
```

This proves unknown paths are not routed as intended.

---

## 23. Validate PostgreSQL remains private

Check services:

```bash
kubectl -n sre-decision-intelligence get svc
```

Expected:

```text
sre-decision-api        ClusterIP
sre-decision-postgres   ClusterIP/headless
cilium-gateway...       LoadBalancer
```

There should be no PostgreSQL LoadBalancer or NodePort.

Validate Gateway routes:

```bash
kubectl -n sre-decision-intelligence get httproute sre-decision-api-route -o yaml
```

Only backend should be:

```text
sre-decision-api:8000
```

There should be no route to PostgreSQL.

---

## 24. Enterprise note about `/docs` and `/openapi.json`

During platform validation, exposing `/docs` and `/openapi.json` is useful.

For production-style operation, choose one of:

```text
disable docs in production
restrict docs behind authentication
allow docs only from trusted internal networks
move docs to a separate internal-only route
```

Possible later FastAPI config:

```text
docs_url=None in production
openapi_url=None in production
```

For now, keep them while building and validating.

---

## 25. Troubleshooting: HTTPRoute not accepted

Check:

```bash
kubectl -n sre-decision-intelligence describe httproute sre-decision-api-route
```

Common causes:

| Problem | Fix |
|---|---|
| Parent Gateway name wrong | Check `parentRefs.name` |
| Namespace mismatch | Check `parentRefs.namespace` |
| Gateway `allowedRoutes` blocks route | Use same namespace or adjust allowedRoutes |
| Backend Service missing | Check `kubectl get svc sre-decision-api` |
| Backend port wrong | Use port `8000` |

---

## 26. Troubleshooting: Gateway has no address

Check:

```bash
kubectl -n sre-decision-intelligence describe gateway sre-decision-gateway
kubectl get svc -A | grep -Ei "gateway|sre-decision"
kubectl get ciliumloadbalancerippool -A
kubectl get ciliuml2announcementpolicy -A
```

Possible causes:

```text
No IP available in lan-pool
Gateway-generated service not selected by L2 announcement policy
Cilium Gateway controller not programming service
LoadBalancer service pending
```

---

## 27. Troubleshooting: 503 Service Unavailable

Check API pod readiness:

```bash
kubectl -n sre-decision-intelligence get pods \
  -l app.kubernetes.io/name=sre-decision-api
```

Check service endpoints:

```bash
kubectl -n sre-decision-intelligence get endpoints sre-decision-api
```

Expected:

```text
endpoint IP exists for port 8000
```

If no endpoints exist, the API pod is not ready.

Check:

```bash
kubectl -n sre-decision-intelligence describe pod \
  -l app.kubernetes.io/name=sre-decision-api
```

Common cause:

```text
readinessProbe /health/db failing
database unreachable
wrong DATABASE_URL
migration not applied
```

---

## 28. Troubleshooting: hostname mismatch

If this works:

```bash
curl -H "Host: sre-decision-api.platform.local" http://$GATEWAY_IP/health
```

but this does not:

```bash
curl http://$GATEWAY_IP/health
```

that is expected because the route is hostname-specific.

Use the Host header or configure DNS/hosts file.

---

## 29. Gateway validation checklist

| Check | Command | Expected |
|---|---|---|
| GatewayClass | `kubectl get gatewayclass` | `cilium Accepted=True` |
| Gateway | `kubectl get gateway -n sre-decision-intelligence` | gateway exists |
| HTTPRoute | `kubectl get httproute -n sre-decision-intelligence` | route exists |
| Gateway conditions | `kubectl describe gateway ...` | `Accepted=True`, `Programmed=True` |
| Route conditions | `kubectl describe httproute ...` | `Accepted=True`, `ResolvedRefs=True` |
| Generated service | `kubectl get svc -A | grep gateway` | LoadBalancer service |
| L2 IP | service external IP | `192.168.0.xxx` |
| Health | `curl ... /health` | status ok |
| DB health | `curl ... /health/db` | status ok |
| SLO API | `curl ... /api/v1/slo` | SLO list |
| Unknown path | `curl ... /unknown` | 404 |
| PostgreSQL exposure | `kubectl get svc` | no external DB service |

---

## 30. Enterprise explanation

You can explain Phase 29E like this:

```text
I exposed the Decision Intelligence API through Cilium Gateway API instead of using a classic Ingress controller. The API remains an internal ClusterIP Service, while the Gateway owns north-south access. HTTPRoute defines the allowed hostname and paths, and Cilium L2 announcements advertise the Gateway LoadBalancer IP on the LAN. PostgreSQL remains private and is not exposed through the Gateway. This separates external access control from service internals and creates a clean enterprise traffic entry point.
```

---

## 31. Files created

```text
k8s/base/gateway/gateway.yaml
k8s/base/gateway/httproute.yaml
k8s/base/gateway/kustomization.yaml
```

---

## 32. Recommended commit

After validation:

```bash
git status
```

Then:

```bash
git add k8s/base/gateway
```

Commit:

```bash
git commit -m "feat: expose decision API with Cilium Gateway API"
git push
```

---

## 33. Phase 29E success criteria

Phase 29E is complete when:

```text
Gateway exists
HTTPRoute exists
Gateway Accepted=True
Gateway Programmed=True
HTTPRoute Accepted=True
HTTPRoute ResolvedRefs=True
Cilium creates LoadBalancer service
LoadBalancer IP comes from lan-pool
L2 announcement makes Gateway IP reachable on LAN
/health works through Gateway
/health/db works through Gateway
/api/v1/slo works through Gateway
/docs or /openapi.json works through Gateway
unknown routes return 404
API Service remains ClusterIP
PostgreSQL remains internal-only
```

---

## 34. Next enterprise phase

After Phase 29E, continue with:

```text
Phase 29F — Cilium NetworkPolicy Hardening
```

Why:

```text
Once Gateway traffic works, network policies can be tightened around the real traffic path.
```
