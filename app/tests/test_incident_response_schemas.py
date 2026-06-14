from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.incident_history import (
    IncidentDetailResponse,
    IncidentSummaryResponse,
    IncidentTimelineEventResponse,
)


def test_incident_summary_response_accepts_expected_fields():
    response = IncidentSummaryResponse(
        id=uuid4(),
        incident_id="frontend-availability-breach",
        service="frontend",
        namespace="fintech-workload",
        severity="warning",
        status="detected",
        scenario="frontend-availability-breach",
        created_at=datetime.now(timezone.utc),
        resolved_at=None,
    )

    assert response.incident_id == "frontend-availability-breach"
    assert response.status == "detected"


def test_timeline_event_response_accepts_payload():
    response = IncidentTimelineEventResponse(
        event_type="incident_detected",
        summary="Incident detected for service frontend",
        source="decision-engine",
        payload={"service": "frontend"},
        created_at=datetime.now(timezone.utc),
    )

    assert response.event_type == "incident_detected"
    assert response.payload["service"] == "frontend"


def test_incident_detail_response_accepts_nested_sections():
    incident_id = uuid4()

    response = IncidentDetailResponse(
        id=incident_id,
        incident_id="frontend-availability-breach",
        service="frontend",
        namespace="fintech-workload",
        severity="warning",
        status="detected",
        scenario="frontend-availability-breach",
        created_at=datetime.now(timezone.utc),
        resolved_at=None,
        timeline=[],
        signals=[],
        evidence=[],
        decisions=[],
        rule_evaluations=[],
    )

    assert response.id == incident_id
    assert response.timeline == []
