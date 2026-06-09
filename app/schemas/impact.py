from pydantic import BaseModel, Field


class Impact(BaseModel):
    summary: str = Field(..., description="Short impact summary")
    user_impact: str = Field(..., description="User-facing impact explanation")
    slo_affected: str = Field(..., description="Affected SLO")
