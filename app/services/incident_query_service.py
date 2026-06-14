from uuid import UUID

from sqlalchemy.orm import Session

from app.api.v1.incident_presenters import (
    incident_timeline_to_response,
    incident_to_detail,
    incident_to_summary,
)
from app.db.repository import get_incident_by_id, list_incidents


def get_incident_history_response(
    db: Session,
    limit: int = 20,
) -> list[dict]:
    incidents = list_incidents(
        db=db,
        limit=limit,
    )

    return [incident_to_summary(incident) for incident in incidents]


def get_open_incidents_response(
    db: Session,
    limit: int = 20,
) -> list[dict]:
    incidents = list_incidents(
        db=db,
        status="detected",
        limit=limit,
    )

    return [incident_to_summary(incident) for incident in incidents]


def get_resolved_incidents_response(
    db: Session,
    limit: int = 20,
) -> list[dict]:
    incidents = list_incidents(
        db=db,
        status="resolved",
        limit=limit,
    )

    return [incident_to_summary(incident) for incident in incidents]


def get_incident_detail_response(
    db: Session,
    incident_db_id: UUID,
) -> dict | None:
    incident = get_incident_by_id(
        db=db,
        incident_db_id=incident_db_id,
    )

    if incident is None:
        return None

    return incident_to_detail(incident)


def get_incident_timeline_response(
    db: Session,
    incident_db_id: UUID,
) -> list[dict] | None:
    incident = get_incident_by_id(
        db=db,
        incident_db_id=incident_db_id,
    )

    if incident is None:
        return None

    return incident_timeline_to_response(incident)
