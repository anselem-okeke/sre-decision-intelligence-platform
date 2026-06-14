from app.scenarios.models import ScenarioDomain, ScenarioStatus

from pydantic import BaseModel


class ScenarioResponse(BaseModel):
    id: str
    name: str
    description: str
    domain: ScenarioDomain
    status: ScenarioStatus
    required_signals: list[str]
    optional_signals: list[str]
    root_cause_category: str
    safe_action_summary: str
    risk_level: str
    tags: list[str]
