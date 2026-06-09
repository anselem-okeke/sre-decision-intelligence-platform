from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    summary: str = Field(..., description="Human-readable evidence summary")
    source: str = Field(..., description="Evidence source")
    category: str = Field(..., description="Evidence category")
