from fastapi import APIRouter, HTTPException

from app.scenarios.registry import scenario_registry
from app.schemas.scenarios import ScenarioResponse


router = APIRouter(
    prefix="/api/v1/scenarios",
    tags=["scenarios"],
)


@router.get("", response_model=list[ScenarioResponse])
def list_scenarios() -> list[dict]:
    scenarios = scenario_registry.list_scenarios()

    return [
        scenario.model_dump(mode="json")
        for scenario in scenarios
    ]


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: str) -> dict:
    scenario = scenario_registry.get_scenario(scenario_id)

    if scenario is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Scenario not found.",
                "scenario_id": scenario_id,
            },
        )

    return scenario.model_dump(mode="json")
