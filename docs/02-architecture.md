# Architecture

## High-Level Architecture

```text
GitHub Repo
   ↓
Argo CD
   ↓
Kubernetes Cluster
   ├── Bank of Anthos
   ├── Prometheus
   ├── Fluent Bit
   ├── OpenSearch
   ├── Kubernetes API
   ├── Grafana
   └── Decision Intelligence API
   ```

   ## Data Flow

   Bank of Anthos
   ├── Metrics → Prometheus
   └── Logs → Fluent Bit → OpenSearch

Prometheus
   └── SLO signals → Decision Intelligence API

OpenSearch
   └── Log evidence → Decision Intelligence API

Kubernetes API
   └── Runtime state → Decision Intelligence API

Argo CD
   └── Deployment/change context → Decision Intelligence API

Decision Intelligence API
   └── Incident summary → Grafana

   ## Design Principle

   > The architecture separates signal detection from investigation. Prometheus is used to detect symptoms. OpenSearch is used to investigate logs. Kubernetes API is used to understand runtime state. Argo CD is used to understand what changed. The Decision Intelligence API correlates all of these sources into one incident summary.

   ## Core Incident Questions

  ### The platform is designed to answer:

  | Question                       | Source                               |
| ------------------------------ | ------------------------------------ |
| Who is affected?               | SLO metrics                          |
| What changed?                  | Argo CD, Kubernetes API              |
| Where is it spreading?         | Metrics, logs, service relationships |
| What is the likely root cause? | Logs, events, correlation rules      |
| What action is safe now?       | Rule engine and runbooks             |
