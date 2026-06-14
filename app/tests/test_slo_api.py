from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_slos_endpoint_returns_defined_slos():
    response = client.get("/api/v1/slo")

    assert response.status_code == 200

    body = response.json()
    slo_ids = {slo["id"] for slo in body}

    assert "frontend-availability-30d" in slo_ids
    assert "frontend-availability-5m" in slo_ids
    assert "transaction-success-30d" in slo_ids


def test_get_slo_endpoint_returns_detail():
    response = client.get("/api/v1/slo/frontend-availability-30d")

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == "frontend-availability-30d"
    assert body["target"] == 0.995
    assert body["sli"]["id"] == "frontend-availability"


def test_get_unknown_slo_returns_404():
    response = client.get("/api/v1/slo/unknown-slo")

    assert response.status_code == 404

    body = response.json()

    assert body["detail"]["message"] == "SLO not found."
    assert body["detail"]["slo_id"] == "unknown-slo"


def test_evaluate_error_budget_endpoint_returns_budget_status():
    response = client.post(
        "/api/v1/slo/evaluate",
        json={
            "slo_id": "frontend-availability-30d",
            "current_value": 0.990,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["slo_id"] == "frontend-availability-30d"
    assert body["status"] == "exhausted"
    assert body["budget_consumed_ratio"] >= 1.0


def test_evaluate_unknown_slo_returns_404():
    response = client.post(
        "/api/v1/slo/evaluate",
        json={
            "slo_id": "unknown-slo",
            "current_value": 0.990,
        },
    )

    assert response.status_code == 404

    body = response.json()

    assert body["detail"]["message"] == "SLO not found."
