import asyncio
import json

import httpx
import pytest

from app.repositories.incidents import incident_repository
from app.services.ollama import (
    SYSTEM_INSTRUCTION,
    OllamaService,
    OllamaTimeoutError,
)


def incident_context():
    incident = incident_repository.get_incident("inc-2026-001")
    assert incident is not None
    return (
        incident,
        incident_repository.list_services(incident.id),
        incident_repository.list_timeline(incident.id),
    )


def test_ollama_service_sends_grounded_prompt() -> None:
    captured_request = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"model": "test-model", "response": "Redis was unhealthy."},
        )

    incident, services, timeline = incident_context()
    service = OllamaService(
        base_url="http://ollama.test",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(
        service.generate(
            incident,
            services,
            timeline,
            "Why did checkout latency spike?",
        )
    )

    assert result.answer == "Redis was unhealthy."
    assert result.model == "test-model"
    assert result.total_latency_ms >= 0
    assert captured_request["system"] == SYSTEM_INSTRUCTION
    assert captured_request["stream"] is False
    assert "checkout-api" in captured_request["prompt"]
    assert "Redis capacity was increased" in captured_request["prompt"]
    assert "Why did checkout latency spike?" in captured_request["prompt"]


def test_ollama_service_handles_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    incident, services, timeline = incident_context()
    service = OllamaService(
        base_url="http://ollama.test",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(OllamaTimeoutError):
        asyncio.run(
            service.generate(
                incident,
                services,
                timeline,
                "What should I investigate first?",
            )
        )