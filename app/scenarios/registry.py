from app.scenarios.frontend_availability import FRONTEND_SERVICE_SELECTOR_MISMATCH
from app.scenarios.models import ScenarioDefinition, ScenarioStatus


class ScenarioRegistry:
    def __init__(self, scenarios: list[ScenarioDefinition]) -> None:
        self._scenarios = {
            scenario.id: scenario
            for scenario in scenarios
        }

    def list_scenarios(
        self,
        include_disabled: bool = False,
    ) -> list[ScenarioDefinition]:
        scenarios = list(self._scenarios.values())

        if include_disabled:
            return scenarios

        return [
            scenario
            for scenario in scenarios
            if scenario.status != ScenarioStatus.DISABLED
        ]

    def get_scenario(self, scenario_id: str) -> ScenarioDefinition | None:
        return self._scenarios.get(scenario_id)

    def require_scenario(self, scenario_id: str) -> ScenarioDefinition:
        scenario = self.get_scenario(scenario_id)

        if scenario is None:
            raise KeyError(f"Scenario not found: {scenario_id}")

        return scenario

    def has_scenario(self, scenario_id: str) -> bool:
        return scenario_id in self._scenarios


scenario_registry = ScenarioRegistry(
    scenarios=[
        FRONTEND_SERVICE_SELECTOR_MISMATCH,
    ]
)
