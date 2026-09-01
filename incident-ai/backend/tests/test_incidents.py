from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.incidents import cache_service, ollama_service, rag_service
from app.main import app
from app.models.incident import AssistantResponse
from app.services.ollama import OllamaResult, OllamaTimeoutError
from app.services.rag import RetrievalResult, RetrievedChunk

client = TestClient(app)


def test_list_incidents() -> None:
    response = client.get("/api/incidents")

    assert response.status_code == 200
    incidents = response.json()
    assert len(incidents) == 3
    assert incidents[0] == {
        "id": "inc-2026-001",
        "title": "Checkout requests timing out",
        "severity": "SEV1",
        "status": "monitoring",
        "start_time": "2026-08-31T09:12:00Z",
        "affected_services": ["checkout-api", "payments-service", "redis"],
        "summary": (
            "Checkout requests experienced elevated latency after Redis connection "
            "pool exhaustion caused retries across payment processing."
        ),
    }


def test_get_incident() -> None:
    response = client.get("/api/incidents/inc-2026-002")

    assert response.status_code == 200
    assert response.json()["title"] == "Inventory availability lag"
    assert response.json()["affected_services"] == ["inventory-service", "redis"]


def test_get_incident_services() -> None:
    response = client.get("/api/incidents/inc-2026-001/services")

    assert response.status_code == 200
    services = response.json()
    assert [service["name"] for service in services] == [
        "checkout-api",
        "payments-service",
        "redis",
    ]
    assert services[0]["p95_latency_ms"] == 1840.0
    assert services[0]["error_rate_percent"] == 8.7
    assert services[0]["cpu_percent"] == 76.4


def test_get_incident_timeline() -> None:
    response = client.get("/api/incidents/inc-2026-003/timeline")

    assert response.status_code == 200
    timeline = response.json()
    assert [event["event_type"] for event in timeline] == [
        "detected",
        "mitigation",
        "resolved",
    ]
    assert timeline[-1]["timestamp"] == "2026-08-29T13:31:00Z"


def test_incident_endpoints_return_not_found() -> None:
    for path in (
        "/api/incidents/missing",
        "/api/incidents/missing/services",
        "/api/incidents/missing/timeline",
    ):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json() == {"detail": "Incident 'missing' not found"}


def test_ask_incident_assistant() -> None:
    retrieved_chunk = RetrievedChunk(
        title="Checkout Latency Response Runbook",
        document_type="runbook",
        text="Check Redis connection pool utilization and retry concurrency.",
        similarity_score=0.92341,
    )
    retrieve = AsyncMock(
        return_value=RetrievalResult(chunks=[retrieved_chunk], latency_ms=12)
    )
    generate = AsyncMock(
        return_value=OllamaResult(
            answer="Redis pool exhaustion increased checkout retries and latency.",
            model="llama3.2:3b",
            total_latency_ms=418,
        )
    )
    original_retrieve = rag_service.retrieve
    original_generate = ollama_service.generate
    rag_service.retrieve = retrieve
    ollama_service.generate = generate

    try:
        response = client.post(
            "/api/incidents/inc-2026-001/assistant",
            json={"question": "Which runbook should I follow?"},
        )
    finally:
        rag_service.retrieve = original_retrieve
        ollama_service.generate = original_generate

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Redis pool exhaustion increased checkout retries and latency.",
        "model": "llama3.2:3b",
        "total_latency_ms": 430,
        "retrieval_latency_ms": 12,
        "cache_hit": False,
        "route": "rag",
        "sources": [
            {
                "title": "Checkout Latency Response Runbook",
                "excerpt": "Check Redis connection pool utilization and retry concurrency.",
                "similarity_score": 0.9234,
            }
        ],
    }
    incident, services, timeline, question, chunks = generate.await_args.args
    assert incident.id == "inc-2026-001"
    assert [service.name for service in services] == [
        "checkout-api",
        "payments-service",
        "redis",
    ]
    assert timeline[0].event_type == "detected"
    assert question == "Which runbook should I follow?"
    assert chunks == [retrieved_chunk]
    retrieve.assert_awaited_once_with("Which runbook should I follow?")


def test_simple_assistant_question_skips_retrieval() -> None:
    cache_get = AsyncMock(return_value=None)
    cache_set = AsyncMock()
    retrieve = AsyncMock()
    generate = AsyncMock(
        return_value=OllamaResult(
            answer="The payments-service error rate is 5.2 percent.",
            model="llama3.2:3b",
            total_latency_ms=205,
        )
    )
    original_cache_get = cache_service.get
    original_cache_set = cache_service.set
    original_retrieve = rag_service.retrieve
    original_generate = ollama_service.generate
    cache_service.get = cache_get
    cache_service.set = cache_set
    rag_service.retrieve = retrieve
    ollama_service.generate = generate

    try:
        response = client.post(
            "/api/incidents/inc-2026-001/assistant",
            json={"question": "What is the payments-service error rate?"},
        )
    finally:
        cache_service.get = original_cache_get
        cache_service.set = original_cache_set
        rag_service.retrieve = original_retrieve
        ollama_service.generate = original_generate

    assert response.status_code == 200
    assert response.json() == {
        "answer": "The payments-service error rate is 5.2 percent.",
        "model": "llama3.2:3b",
        "total_latency_ms": 205,
        "retrieval_latency_ms": 0,
        "cache_hit": False,
        "route": "simple",
        "sources": [],
    }
    retrieve.assert_not_awaited()
    incident, services, timeline, question, chunks = generate.await_args.args
    assert incident.id == "inc-2026-001"
    assert services[1].name == "payments-service"
    assert timeline
    assert question == "What is the payments-service error rate?"
    assert chunks == []
    cache_get.assert_awaited_once()
    cached_response = cache_set.await_args.args[1]
    assert cached_response.cache_hit is False
    assert cached_response.route == "simple"


def test_cached_assistant_response_skips_ai_pipeline() -> None:
    cached_response = AssistantResponse(
        answer="The incident severity is SEV1.",
        model="llama3.2:3b",
        total_latency_ms=190,
        route="simple",
        cache_hit=True,
    )
    cache_get = AsyncMock(return_value=cached_response)
    cache_set = AsyncMock()
    retrieve = AsyncMock()
    generate = AsyncMock()
    original_cache_get = cache_service.get
    original_cache_set = cache_service.set
    original_retrieve = rag_service.retrieve
    original_generate = ollama_service.generate
    cache_service.get = cache_get
    cache_service.set = cache_set
    rag_service.retrieve = retrieve
    ollama_service.generate = generate

    try:
        response = client.post(
            "/api/incidents/inc-2026-001/assistant",
            json={"question": "What severity is this incident?"},
        )
    finally:
        cache_service.get = original_cache_get
        cache_service.set = original_cache_set
        rag_service.retrieve = original_retrieve
        ollama_service.generate = original_generate

    assert response.status_code == 200
    assert response.json()["answer"] == "The incident severity is SEV1."
    assert response.json()["cache_hit"] is True
    assert response.json()["route"] == "simple"
    cache_get.assert_awaited_once()
    cache_set.assert_not_awaited()
    retrieve.assert_not_awaited()
    generate.assert_not_awaited()


def test_assistant_returns_not_found_without_calling_ollama() -> None:
    retrieve = AsyncMock()
    generate = AsyncMock()
    original_retrieve = rag_service.retrieve
    original_generate = ollama_service.generate
    rag_service.retrieve = retrieve
    ollama_service.generate = generate

    try:
        response = client.post(
            "/api/incidents/missing/assistant",
            json={"question": "What happened?"},
        )
    finally:
        rag_service.retrieve = original_retrieve
        ollama_service.generate = original_generate

    assert response.status_code == 404
    retrieve.assert_not_awaited()
    generate.assert_not_awaited()


def test_assistant_handles_ollama_timeout() -> None:
    cache_get = AsyncMock(return_value=None)
    cache_set = AsyncMock()
    retrieve = AsyncMock(
        return_value=RetrievalResult(chunks=[], latency_ms=8)
    )
    generate = AsyncMock(side_effect=OllamaTimeoutError())
    original_cache_get = cache_service.get
    original_cache_set = cache_service.set
    original_retrieve = rag_service.retrieve
    original_generate = ollama_service.generate
    cache_service.get = cache_get
    cache_service.set = cache_set
    rag_service.retrieve = retrieve
    ollama_service.generate = generate

    try:
        response = client.post(
            "/api/incidents/inc-2026-001/assistant",
            json={"question": "Summarize this incident."},
        )
    finally:
        cache_service.get = original_cache_get
        cache_service.set = original_cache_set
        rag_service.retrieve = original_retrieve
        ollama_service.generate = original_generate

    assert response.status_code == 504
    assert response.json() == {"detail": "Ollama did not respond before the timeout"}
    cache_set.assert_not_awaited()


def test_assistant_rejects_blank_question() -> None:
    response = client.post(
        "/api/incidents/inc-2026-001/assistant",
        json={"question": "   "},
    )

    assert response.status_code == 422