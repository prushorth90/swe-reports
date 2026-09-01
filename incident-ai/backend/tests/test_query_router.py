import pytest

from app.services.query_router import QueryRoute, QueryRouter


@pytest.mark.parametrize(
    ("question", "expected_route"),
    [
        ("What severity is this incident?", QueryRoute.SIMPLE),
        ("Which services are affected?", QueryRoute.SIMPLE),
        ("What is the payments-service error rate?", QueryRoute.SIMPLE),
        ("Why did checkout latency spike?", QueryRoute.SIMPLE),
        ("Which downstream service is unhealthy?", QueryRoute.SIMPLE),
        ("Summarize this incident.", QueryRoute.SIMPLE),
        ("Have we seen this before?", QueryRoute.RAG),
        ("Have we seen a similar incident before?", QueryRoute.RAG),
        ("Which runbook should I follow?", QueryRoute.RAG),
        ("What should I investigate next?", QueryRoute.RAG),
        ("How do I troubleshoot payment failures?", QueryRoute.RAG),
        ("Explain the broader operational risk.", QueryRoute.RAG),
    ],
)
def test_classifies_query(question: str, expected_route: QueryRoute) -> None:
    assert QueryRouter().classify(question) is expected_route


def test_rag_intent_takes_precedence_over_metric_keyword() -> None:
    question = "Which runbook covers elevated checkout latency?"

    assert QueryRouter().classify(question) is QueryRoute.RAG