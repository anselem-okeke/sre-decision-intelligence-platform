
---

# 8. Create project overview document

Put this in `docs/01-project-overview.md`:

```markdown
# Project Overview

## Name

SRE Decision Intelligence Platform

## Purpose

This project demonstrates how an SRE platform can move beyond raw observability dashboards and produce actionable incident decisions.

The system is designed around one principle:

> Observability should help teams make better decisions during production incidents.

## Problem Statement

Many teams collect large volumes of telemetry but still struggle during outages.

Common problems include:

- Too many alerts
- Too many dashboards
- Weak incident context
- Unclear root cause
- No clear safe next action
- High cognitive load during production pressure

This project addresses that gap by correlating telemetry signals into decision-oriented incident summaries.

## Core Concept

The platform starts from a user-impact signal, usually an SLO breach.

It then collects supporting evidence from metrics, logs, Kubernetes runtime state, and GitOps deployment history.

The final output should answer:

- What changed?
- Who is affected?
- Where is the failure spreading?
- What is the likely root cause?
- What action is safe now?

## Workload

The project uses Bank of Anthos as the realistic fintech workload.

Bank of Anthos provides a useful business context because it includes user-facing and backend service flows similar to real financial systems.

## Platform Components

| Component                     | Role                                 |
| ----------------------------- | ------------------------------------ |
| **Bank of Anthos**            | Production-style workload            |
| **Prometheus**                | Metrics and SLO detection            |
| **Fluent Bit**                | Log collection                       |
| **OpenSearch**                | Log storage and search               |
| **Kubernetes API**            | Runtime and workload context         |
| **Argo CD**                   | GitOps and deployment-change context |
| **Grafana**                   | Visualization                        |
| **Decision Intelligence API** | Correlation and decision generation  |


## Outcome

The final platform should demonstrate:

- SLO-driven incident detection
- OpenSearch-based log investigation
- Kubernetes-aware runtime context
- GitOps-aware change correlation
- Decision-oriented incident summaries
- Safe action recommendations








