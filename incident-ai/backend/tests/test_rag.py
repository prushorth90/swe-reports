import asyncio

from app.services.rag import RagService


class FakeEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        normalized = text.lower()
        if normalized.startswith("inventory service operations guide"):
            return [0.0, 1.0, 0.0]
        if normalized.startswith("payment authorization troubleshooting notes"):
            return [0.0, 0.0, 1.0]
        if normalized.startswith((
            "checkout latency response runbook",
            "historical incident: redis pool exhaustion",
        )):
            return [1.0, 0.0, 0.0]
        if "inventory" in normalized or "cache invalidation" in normalized:
            return [0.0, 1.0, 0.0]
        if "checkout" in normalized or "redis pool" in normalized:
            return [1.0, 0.0, 0.0]
        if "certificate" in normalized or "authorization" in normalized:
            return [0.0, 0.0, 1.0]
        return [0.1, 0.1, 0.1]


def test_retrieves_checkout_runbook_and_similar_incident() -> None:
    service = RagService(FakeEmbeddingProvider(), top_k=2)

    result = asyncio.run(
        service.retrieve("Have we seen a similar checkout Redis pool incident?")
    )

    assert {chunk.title for chunk in result.chunks} == {
        "Checkout Latency Response Runbook",
        "Historical Incident: Redis Pool Exhaustion",
    }
    assert all(chunk.similarity_score == 1.0 for chunk in result.chunks)


def test_retrieves_inventory_service_documentation() -> None:
    service = RagService(FakeEmbeddingProvider(), top_k=1)

    result = asyncio.run(
        service.retrieve("Why is inventory cache invalidation falling behind?")
    )

    assert result.chunks[0].title == "Inventory Service Operations Guide"
    assert "consumer lag" in result.chunks[0].text


def test_retrieves_payment_troubleshooting_notes() -> None:
    service = RagService(FakeEmbeddingProvider(), top_k=1)

    result = asyncio.run(
        service.retrieve("How do certificate failures affect payment authorization?")
    )

    assert result.chunks[0].title == "Payment Authorization Troubleshooting Notes"
    assert result.chunks[0].document_type == "troubleshooting notes"