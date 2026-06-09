from typing import Any

from pydantic import BaseModel, Field


class Signal(BaseModel):
    name: str = Field(..., description="Signal name")
    value: Any = Field(..., description="Signal value")
    meaning: str = Field(..., description="Human-readable signal meaning")


class SignalGroup(BaseModel):
    prometheus: list[Signal] = Field(default_factory=list)
    kubernetes: list[Signal] = Field(default_factory=list)
    opensearch: list[Signal] = Field(default_factory=list)
    argocd: list[Signal] = Field(default_factory=list)
