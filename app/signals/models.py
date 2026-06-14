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
