from enum import StrEnum

from pydantic import BaseModel, Field


class SliType(StrEnum):
    AVAILABILITY = "availability"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    SUCCESS_RATE = "success_rate"
    SATURATION = "saturation"


class SloWindow(StrEnum):
    FIVE_MINUTES = "5m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"


class SloStatus(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    BURNING_FAST = "burning_fast"
    EXHAUSTED = "exhausted"


class SliDefinition(BaseModel):
    id: str = Field(..., description="Stable SLI identifier")
    name: str = Field(..., description="Human-readable SLI name")
    description: str = Field(..., description="What the SLI measures")
    service: str = Field(..., description="Service measured by this SLI")
    sli_type: SliType = Field(..., description="Availability, latency, error rate, etc.")
    source: str = Field(..., description="Telemetry source, e.g. Prometheus")
    signal_name: str = Field(..., description="Normalized signal used for this SLI")
    unit: str = Field(..., description="ratio, milliseconds, count, etc.")
    good_event_description: str = Field(..., description="What counts as good")
    bad_event_description: str = Field(..., description="What counts as bad")


class SloDefinition(BaseModel):
    id: str = Field(..., description="Stable SLO identifier")
    name: str = Field(..., description="Human-readable SLO name")
    description: str = Field(..., description="What reliability promise this SLO represents")
    sli: SliDefinition
    target: float = Field(..., ge=0.0, le=1.0, description="Target ratio, e.g. 0.995")
    window: SloWindow = Field(..., description="SLO evaluation window")
    warning_threshold: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Budget consumed ratio that becomes warning",
    )
    critical_threshold: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description="Budget consumed ratio that becomes burning_fast",
    )
    tags: list[str] = Field(default_factory=list)


class ErrorBudgetEvaluation(BaseModel):
    slo_id: str
    slo_name: str
    service: str
    sli_id: str
    sli_name: str
    target: float
    current_value: float
    window: SloWindow

    allowed_failure_ratio: float
    current_failure_ratio: float
    budget_consumed_ratio: float
    budget_remaining_ratio: float

    status: SloStatus
    summary: str
