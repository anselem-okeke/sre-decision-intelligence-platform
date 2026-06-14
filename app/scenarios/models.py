from enum import StrEnum

from pydantic import BaseModel, Field


class ScenarioDomain(StrEnum):
    WORKLOAD = "workload"
    PLATFORM = "platform"
    CORRELATION = "correlation"


class ScenarioStatus(StrEnum):
    ACTIVE = "active"
    EXPERIMENTAL = "experimental"
    DISABLED = "disabled"


class ScenarioDefinition(BaseModel):
    id: str = Field(..., description="Stable scenario identifier")
    name: str = Field(..., description="Human-readable scenario name")
    description: str = Field(..., description="What this scenario detects")
    domain: ScenarioDomain = Field(..., description="workload, platform, or correlation")
    status: ScenarioStatus = Field(default=ScenarioStatus.ACTIVE)

    required_signals: list[str] = Field(
        default_factory=list,
        description="Signals required for this scenario to be evaluated",
    )
    optional_signals: list[str] = Field(
        default_factory=list,
        description="Signals that improve confidence but are not mandatory",
    )

    root_cause_category: str = Field(..., description="Root cause category")
    safe_action_summary: str = Field(..., description="Recommended safe action")
    risk_level: str = Field(..., description="Risk level of the recommended action")

    tags: list[str] = Field(default_factory=list)
