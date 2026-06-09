from pydantic import BaseModel, Field


class RootCause(BaseModel):
    summary: str = Field(..., description="Likely root cause summary")
    confidence: str = Field(..., description="Confidence level: low, medium, or high")
    category: str = Field(..., description="Root cause category")
