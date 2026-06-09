from pydantic import BaseModel, Field


class SafeAction(BaseModel):
    summary: str = Field(..., description="Recommended safe action")
    command: str | None = Field(default=None, description="Optional remediation command")
    risk: str = Field(..., description="Risk level: low, medium, or high")
