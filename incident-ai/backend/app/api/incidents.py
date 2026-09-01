from fastapi import APIRouter, HTTPException, status

from app.models.incident import (
    AssistantQuestion,
    AssistantResponse,
    Incident,
    Service,
    TimelineEvent,
)
from app.repositories.incidents import incident_repository
from app.services.ollama import OllamaError, OllamaTimeoutError, ollama_service

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


@router.post("/{incident_id}/assistant", response_model=AssistantResponse)
async def ask_incident_assistant(
    incident_id: str,
    request: AssistantQuestion,
) -> AssistantResponse:
    incident = require_incident(incident_id)
    services = incident_repository.list_services(incident_id)
    timeline = incident_repository.list_timeline(incident_id)

    try:
        result = await ollama_service.generate(
            incident,
            services,
            timeline,
            request.question,
        )
    except OllamaTimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Ollama did not respond before the timeout",
        ) from error
    except OllamaError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ollama is unavailable",
        ) from error

    return AssistantResponse(
        answer=result.answer,
        model=result.model,
        total_latency_ms=result.total_latency_ms,
    )