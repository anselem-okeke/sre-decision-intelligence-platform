from pathlib import Path

from fastapi import APIRouter

from app.engine.decision_engine import RuleEngine
from app.engine.sample_signals import get_frontend_availability_sample_signals
from app.schemas.decision import DecisionResponse

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])

RULE_PATH = Path("app/rules/frontend_availability_breach.yaml")


@router.get("/frontend-availability", response_model=DecisionResponse)
def get_frontend_availability_incident() -> DecisionResponse:
    signals = get_frontend_availability_sample_signals()
    engine = RuleEngine(RULE_PATH)

    return engine.evaluate(signals)
