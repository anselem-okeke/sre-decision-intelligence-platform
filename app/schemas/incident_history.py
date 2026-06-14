from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class IncidentSummaryResponse(BaseModel):
    id: UUID
    incident_id: str
    service: str
    namespace: str
    severity: str
    status: str
    scenario: str
    created_at: datetime | None = None
    resolved_at: datetime | None = None


class IncidentSignalResponse(BaseModel):
    source: str
    name: str
    value: Any
    meaning: str
    collected_at: datetime | None = None


class IncidentEvidenceResponse(BaseModel):
    source: str
    category: str
    summary: str
    payload: Any = None
    created_at: datetime | None = None


class IncidentDecisionRecordResponse(BaseModel):
    impact_summary: str
    user_impact: str
    likely_root_cause: str
    root_cause_category: str
    confidence: str
    safe_action_summary: str
    safe_action_command: str | None = None
    created_at: datetime | None = None


class IncidentRuleEvaluationResponse(BaseModel):
    rule_id: str
    matched: bool
    confidence: str | None = None
    reason: str
    created_at: datetime | None = None


class IncidentTimelineEventResponse(BaseModel):
    event_type: str
    summary: str
    source: str
    payload: Any = None
    created_at: datetime | None = None


class IncidentDetailResponse(IncidentSummaryResponse):
    timeline: list[IncidentTimelineEventResponse]
    signals: list[IncidentSignalResponse]
    evidence: list[IncidentEvidenceResponse]
    decisions: list[IncidentDecisionRecordResponse]
    rule_evaluations: list[IncidentRuleEvaluationResponse]


class IncidentResolveResponse(BaseModel):
    status: str
    incident_id: str
    service: str
    namespace: str
    resolved_at: datetime | str | None = None


class ErrorDetailResponse(BaseModel):
    message: str
    reason: str | None = None


class ErrorResponse(BaseModel):
    detail: ErrorDetailResponse
