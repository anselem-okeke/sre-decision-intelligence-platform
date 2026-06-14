from pydantic import BaseModel, Field

from app.slo.models import ErrorBudgetEvaluation, SloDefinition


class SloResponse(SloDefinition):
    pass


class ErrorBudgetEvaluateRequest(BaseModel):
    slo_id: str = Field(..., description="SLO identifier")
    current_value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Current SLI value as a ratio, e.g. 0.982",
    )


class ErrorBudgetEvaluateResponse(ErrorBudgetEvaluation):
    pass
