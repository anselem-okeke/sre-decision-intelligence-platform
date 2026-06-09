from pydantic import BaseModel, Field

from app.schemas.impact import Impact
from app.schemas.root_cause import RootCause
from app.schemas.safe_action import SafeAction
from app.schemas.signal import SignalGroup


class DecisionMetadata(BaseModel):
    decision_engine_version: str = Field(..., description="Decision engine version")
    scenario: str = Field(..., description="Incident scenario")
    environment: str = Field(..., description="Environment name")


class DecisionResponse(BaseModel):
    incident_id: str = Field(..., description="Unique incident identifier")
    service: str = Field(..., description="Affected service")
    namespace: str = Field(..., description="Kubernetes namespace")
    severity: str = Field(..., description="Incident severity")
    status: str = Field(..., description="Incident status")
    impact: Impact
    signals: SignalGroup
    evidence: list[str] = Field(default_factory=list)
    likely_root_cause: RootCause
    safe_action: SafeAction
    metadata: DecisionMetadata
