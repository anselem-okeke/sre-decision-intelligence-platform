from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_scenarios_endpoint_returns_frontend_selector_mismatch():
    response = client.get("/api/v1/scenarios")

    assert response.status_code == 200

    body = response.json()

    assert isinstance(body, list)
    assert len(body) >= 1

    scenario_ids = {scenario["id"] for scenario in body}

    assert "frontend-service-selector-mismatch" in scenario_ids


def test_get_scenario_endpoint_returns_scenario_detail():
    response = client.get("/api/v1/scenarios/frontend-service-selector-mismatch")

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == "frontend-service-selector-mismatch"
    assert body["root_cause_category"] == "service-routing"
    assert "probe_success" in body["required_signals"]
    assert "frontend_endpoints" in body["required_signals"]


def test_get_unknown_scenario_returns_404():
    response = client.get("/api/v1/scenarios/unknown-scenario")

    assert response.status_code == 404

    body = response.json()

    assert body["detail"]["message"] == "Scenario not found."
    assert body["detail"]["scenario_id"] == "unknown-scenario"
