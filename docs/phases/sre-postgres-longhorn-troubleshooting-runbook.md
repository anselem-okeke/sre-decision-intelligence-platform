# Runbook: Fix PostgreSQL StatefulSet with Longhorn PVC Issues

## Context

Workload: `sre-decision-postgres`  
Namespace: `sre-decision-intelligence`  
Storage backend: Longhorn  
Kubernetes object: StatefulSet with PVC from `volumeClaimTemplates`

Final working state:

```bash
kubectl -n sre-decision-intelligence get pods,pvc
```

Expected:

```text
pod/sre-decision-postgres-0   1/1   Running
persistentvolumeclaim/postgres-data-sre-decision-postgres-0   Bound   longhorn-retain-dev
```

---

## 1. Initial Symptom

Postgres pod was stuck in:

```text
ContainerCreating
```

Service had no endpoints:

```bash
kubectl -n sre-decision-intelligence get endpoints
```

Result:

```text
sre-decision-postgres   <none>
```

---

## 2. Root Cause 1: Longhorn Volume Could Not Attach

Check pod events:

```bash
kubectl -n sre-decision-intelligence describe pod sre-decision-postgres-0
```

Observed:

```text
FailedAttachVolume
volume ... is not ready for workloads
```

Check Longhorn volume:

```bash
kubectl -n longhorn-system describe volumes.longhorn.io <volume-id>
```

Observed:

```text
Reason: ReplicaSchedulingFailure
Message: precheck new replica failed: disks are unavailable
Robustness: faulted
State: detached
```

Meaning: PVC/PV existed, but Longhorn could not schedule the volume replicas.

---

## 3. Root Cause 2: Longhorn DiskPressure

Check Longhorn nodes:

```bash
kubectl -n longhorn-system describe nodes.longhorn.io talos-w1
kubectl -n longhorn-system describe nodes.longhorn.io talos-w2
```

Observed:

```text
Reason: DiskPressure
Status: False
Type: Schedulable
```

Meaning: Longhorn disks were ready, but not schedulable for new replicas because free space was below the configured safety threshold.

---

## 4. Clean Old Broken PostgreSQL Storage

Check PVC:

```bash
kubectl -n sre-decision-intelligence get pvc
```

Delete old PostgreSQL PVC if disposable:

```bash
kubectl -n sre-decision-intelligence delete pvc postgres-data-sre-decision-postgres-0
```

Check PV:

```bash
kubectl get pv | grep sre-decision
```

Delete old PV if still present:

```bash
kubectl delete pv <old-pv-name>
```

Check Longhorn volumes:

```bash
kubectl -n longhorn-system get volumes.longhorn.io \
  -o custom-columns=NAME:.metadata.name,STATE:.status.state,ROBUSTNESS:.status.robustness,SIZE:.spec.size,PV:.status.kubernetesStatus.pvName,PVC:.status.kubernetesStatus.pvcName,NAMESPACE:.status.kubernetesStatus.namespace
```

Delete old faulted SRE Postgres Longhorn volumes:

```bash
kubectl -n longhorn-system delete volumes.longhorn.io <old-faulted-sre-postgres-volume>
```

Do not delete healthy volumes used by Grafana, Loki, Prometheus, MinIO, or active OpenSearch.

---

## 5. Clean Orphaned Longhorn Volumes Carefully

Check live OpenSearch PVC:

```bash
kubectl -n observability get pods,pvc
```

Only the PVC shown as `Bound` is active.

Check whether suspicious Longhorn volumes still have PVs:

```bash
kubectl get pv | grep -E '<volume-id-1>|<volume-id-2>|<volume-id-3>'
```

If no PV exists and the Longhorn volume is detached/unknown from an old workload, it is likely orphaned retained storage.

Delete only if data is disposable:

```bash
kubectl -n longhorn-system delete volumes.longhorn.io <orphaned-volume-id>
```

---

## 6. Confirm Longhorn Is Healthy Again

Check PVC/PV cleanup:

```bash
kubectl -n sre-decision-intelligence get pvc
kubectl get pv | grep sre-decision
kubectl -n longhorn-system get volumes.longhorn.io | grep sre-decision
```

Expected:

```text
No old SRE Postgres PVC/PV/Longhorn volume exists
```

Check Longhorn disk schedulability:

```bash
kubectl -n longhorn-system describe nodes.longhorn.io talos-w1 | grep -A8 -B3 "Type:                  Schedulable"
kubectl -n longhorn-system describe nodes.longhorn.io talos-w2 | grep -A8 -B3 "Type:                  Schedulable"
```

Expected:

```text
Status: True
Type: Schedulable
Disk ... is schedulable
```

---

## 7. Use a Dev StorageClass with 1 Replica

Create/use this StorageClass for dev Postgres:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn-retain-dev
provisioner: driver.longhorn.io
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: Immediate
parameters:
  numberOfReplicas: "1"
  staleReplicaTimeout: "2880"
  fromBackup: ""
  fsType: "ext4"
```

In the StatefulSet PVC template:

```yaml
volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes:
        - ReadWriteOnce
      storageClassName: longhorn-retain-dev
      resources:
        requests:
          storage: 5Gi
```

Reason: the original `longhorn-retain` class used 2 replicas, which failed while Longhorn disks were under pressure.

---

## 8. Apply with Kustomize Correctly

Do not use:

```bash
kubectl apply -f k8s/base/postgres
```

Use:

```bash
kubectl apply -k k8s/base/postgres
```

Reason: `kustomization.yaml` is not a normal Kubernetes resource. It must be processed by Kustomize.

---

## 9. Root Cause 3: Postgres CrashLoopBackOff

After storage was fixed, the pod moved from volume attach failure to:

```text
CrashLoopBackOff
Exit Code: 1
```

Check logs:

```bash
kubectl -n sre-decision-intelligence logs sre-decision-postgres-0 -c postgres --previous
```

Fix: set `PGDATA` to a subdirectory inside the mounted volume:

```yaml
env:
  - name: PGDATA
    value: /var/lib/postgresql/data/pgdata
```

Reason: PostgreSQL should initialize in a clean subdirectory instead of the root of the mounted volume.

---

## 10. PodSecurity Fix

If you see:

```text
would violate PodSecurity "restricted:latest": runAsNonRoot != true
```

Add this container security context:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 999
  runAsGroup: 999
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

Keep pod-level security context:

```yaml
securityContext:
  fsGroup: 999
  seccompProfile:
    type: RuntimeDefault
```

---

## 11. Final Verification

```bash
kubectl -n sre-decision-intelligence get pods,pvc,svc,statefulset
```

Expected:

```text
pod/sre-decision-postgres-0   1/1   Running
pvc/postgres-data-sre-decision-postgres-0   Bound   longhorn-retain-dev
service/sre-decision-postgres   ClusterIP None   5432/TCP
statefulset.apps/sre-decision-postgres   1/1
```

Check logs:

```bash
kubectl -n sre-decision-intelligence logs sre-decision-postgres-0 -c postgres
```

Expected:

```text
database system is ready to accept connections
```

---

## Summary

Actual failure chain:

```text
Longhorn DiskPressure
  -> replica scheduling failed
  -> Longhorn volume faulted/detached
  -> Postgres pod stuck ContainerCreating
  -> no Service endpoints
  -> cleaned orphaned/faulted volumes
  -> used 1-replica dev StorageClass
  -> storage attached successfully
  -> fixed Postgres PGDATA
  -> pod Running
```
