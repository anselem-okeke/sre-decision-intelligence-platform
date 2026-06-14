from app.scenarios.registry import scenario_registry


def test_scenario_registry_contains_frontend_selector_mismatch():
    scenario = scenario_registry.get_scenario("frontend-service-selector-mismatch")

    assert scenario is not None
    assert scenario.id == "frontend-service-selector-mismatch"
    assert scenario.root_cause_category == "service-routing"
    assert "probe_success" in scenario.required_signals
    assert "frontend_endpoints" in scenario.required_signals
    assert "frontend_pod_ready" in scenario.required_signals


def test_scenario_registry_lists_active_scenarios():
    scenarios = scenario_registry.list_scenarios()

    scenario_ids = {scenario.id for scenario in scenarios}

    assert "frontend-service-selector-mismatch" in scenario_ids
