import asyncio
from unittest.mock import AsyncMock

from redis.exceptions import ConnectionError

from app.models.incident import AssistantResponse
from app.repositories.incidents import incident_repository
from app.services.cache import CacheService
from app.services.query_router import QueryRoute


def incident_context():
    incident = incident_repository.get_incident("inc-2026-001")
    assert incident is not None
    return (
        incident,
        incident_repository.list_services(incident.id),
        incident_repository.list_timeline(incident.id),
    )


def test_cache_key_normalizes_question_and_tracks_context_version() -> None:
    incident, services, timeline = incident_context()
    service = CacheService(client=AsyncMock())

    first_key = service.build_key(
        incident,
        services,
        timeline,
        " What  severity is THIS incident? ",
        QueryRoute.SIMPLE,
    )
    normalized_key = service.build_key(
        incident,
        services,
        timeline,
        "what severity is this incident",
        QueryRoute.SIMPLE,
    )
    changed_services = [
        services[0].model_copy(update={"error_rate_percent": 9.1}),
        *services[1:],
    ]
    changed_context_key = service.build_key(
        incident,
        changed_services,
        timeline,
        "what severity is this incident",
        QueryRoute.SIMPLE,
    )
    rag_key = service.build_key(
        incident,
        services,
        timeline,
        "what severity is this incident",
        QueryRoute.RAG,
    )

    assert first_key == normalized_key
    assert changed_context_key != first_key
    assert rag_key != first_key


def test_cache_get_marks_response_as_hit() -> None:
    response = AssistantResponse(
        answer="SEV1",
        model="test-model",
        total_latency_ms=100,
        route="simple",
    )
    client = AsyncMock()
    client.get.return_value = response.model_dump_json()
    service = CacheService(client=client)

    cached = asyncio.run(service.get("test-key"))

    assert cached is not None
    assert cached.cache_hit is True
    assert cached.answer == "SEV1"


def test_cache_set_uses_configured_ttl() -> None:
    response = AssistantResponse(
        answer="SEV1",
        model="test-model",
        total_latency_ms=100,
        route="simple",
    )
    client = AsyncMock()
    service = CacheService(client=client, ttl_seconds=45)

    asyncio.run(service.set("test-key", response))

    client.set.assert_awaited_once_with(
        "test-key",
        response.model_dump_json(),
        ex=45,
    )


def test_cache_fails_open_when_redis_is_unavailable() -> None:
    client = AsyncMock()
    client.get.side_effect = ConnectionError("Redis unavailable")
    client.set.side_effect = ConnectionError("Redis unavailable")
    service = CacheService(client=client)
    response = AssistantResponse(
        answer="SEV1",
        model="test-model",
        total_latency_ms=100,
        route="simple",
    )

    assert asyncio.run(service.get("test-key")) is None
    asyncio.run(service.set("test-key", response))