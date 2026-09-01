from fastapi import APIRouter, HTTPException, status

from app.models.incident import Incident, Service, TimelineEvent
from app.repositories.incidents import incident_repository

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


def require_incident(incident_id: str) -> Incident:
    incident = incident_repository.get_incident(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )
    return incident


@router.get("", response_model=list[Incident])
def list_incidents() -> list[Incident]:
    return incident_repository.list_incidents()


@router.get("/{incident_id}", response_model=Incident)
def get_incident(incident_id: str) -> Incident:
    return require_incident(incident_id)


@router.get("/{incident_id}/services", response_model=list[Service])
def list_incident_services(incident_id: str) -> list[Service]:
    require_incident(incident_id)
    return incident_repository.list_services(incident_id)


@router.get("/{incident_id}/timeline", response_model=list[TimelineEvent])
def list_incident_timeline(incident_id: str) -> list[TimelineEvent]:
    require_incident(incident_id)
    return incident_repository.list_timeline(incident_id)