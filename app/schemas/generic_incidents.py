from typing import Any

from pydantic import BaseModel, Field

from app.schemas.decision import DecisionResponse


class GenericEvaluateRequest(BaseModel):
    signals: dict[str, Any] = Field(
        ...,
        description="Raw signal dictionary used by the multi-rule engine",
    )


class RuleEvaluationResponse(BaseModel):
    rule_id: str
    scenario_id: str | None = None
    name: str | None = None
    matched: bool
    priority: int
    failed_conditions: list[dict[str, Any]] = Field(default_factory=list)


class GenericEvaluateResponse(BaseModel):
    matched: bool
    decision: DecisionResponse | None = None
    evaluations: list[RuleEvaluationResponse]
    message: str | None = None


class GenericPersistRequest(BaseModel):
    signals: dict[str, Any] = Field(
        ...,
        description="Raw signal dictionary to evaluate and persist if a rule matches",
    )


class GenericPersistResponse(BaseModel):
    persisted: bool
    incident_db_id: str | None = None
    incident_id: str | None = None
    status: str | None = None
    service: str | None = None
    namespace: str | None = None
    message: str


class GenericResolveRequest(BaseModel):
    recovery_signals: dict[str, Any] = Field(
        default_factory=dict,
        description="Signals proving that the incident has recovered",
    )


class GenericResolveResponse(BaseModel):
    status: str
    incident_db_id: str
    incident_id: str
    service: str
    namespace: str
    message: str
