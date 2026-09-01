import re
from enum import Enum


class QueryRoute(str, Enum):
    SIMPLE = "simple"
    RAG = "rag"


class QueryRouter:
    RAG_PHRASES = (
        "have we seen",
        "seen this before",
        "seen before",
        "similar incident",
        "previous incident",
        "historical incident",
        "last time",
        "which runbook",
        "what runbook",
        "which playbook",
        "what should i investigate",
        "investigate next",
        "investigate first",
        "what should i do next",
        "next steps",
        "how do i troubleshoot",
    )
    RAG_KEYWORDS = (
        "runbook",
        "playbook",
        "documentation",
        "troubleshooting",
        "recommendation",
    )
    SIMPLE_PHRASES = (
        "which services are affected",
        "what services are affected",
        "affected services",
        "when did the incident start",
        "when did this incident start",
        "start time",
        "what happened",
        "summarize this incident",
        "downstream service",
    )
    SIMPLE_KEYWORDS = (
        "severity",
        "status",
        "latency",
        "error rate",
        "cpu",
        "timeline",
        "healthy",
        "unhealthy",
        "degraded",
        "outage",
        "incident id",
    )

    def classify(self, question: str) -> QueryRoute:
        normalized = re.sub(r"[^a-z0-9%]+", " ", question.lower()).strip()

        if self._contains_any(normalized, self.RAG_PHRASES):
            return QueryRoute.RAG
        if self._contains_keyword(normalized, self.RAG_KEYWORDS):
            return QueryRoute.RAG
        if self._contains_any(normalized, self.SIMPLE_PHRASES):
            return QueryRoute.SIMPLE
        if self._contains_keyword(normalized, self.SIMPLE_KEYWORDS):
            return QueryRoute.SIMPLE
        return QueryRoute.RAG

    @staticmethod
    def _contains_any(question: str, phrases: tuple[str, ...]) -> bool:
        return any(phrase in question for phrase in phrases)

    @staticmethod
    def _contains_keyword(question: str, keywords: tuple[str, ...]) -> bool:
        padded_question = f" {question} "
        return any(f" {keyword} " in padded_question for keyword in keywords)


query_router = QueryRouter()