from app.main import app


def test_incident_routes_are_still_registered_after_service_refactor():
    paths = {
        route.path
        for route in app.routes
        if "/api/v1/incidents" in route.path
    }

    expected_paths = {
        "/api/v1/incidents/frontend-availability",
        "/api/v1/incidents/frontend-availability/live",
        "/api/v1/incidents/frontend-availability/live/signals",
        "/api/v1/incidents/frontend-availability/live/signals/normalized",
        "/api/v1/incidents/frontend-availability/live/evaluations",
        "/api/v1/incidents/frontend-availability/sample/persist",
        "/api/v1/incidents/frontend-availability/live/persist",
        "/api/v1/incidents/frontend-availability/live/resolve",
        "/api/v1/incidents/history",
        "/api/v1/incidents/open",
        "/api/v1/incidents/resolved",
        "/api/v1/incidents/evaluate",
        "/api/v1/incidents/evaluate/live",
        "/api/v1/incidents/persist",
        "/api/v1/incidents/live/persist",
        "/api/v1/incidents/{incident_db_id}/timeline",
        "/api/v1/incidents/{incident_db_id}/resolve",
        "/api/v1/incidents/{incident_db_id}",
    }

    assert expected_paths.issubset(paths)
