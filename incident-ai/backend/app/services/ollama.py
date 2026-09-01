import json
import os
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Any, Optional

import httpx

from app.models.incident import Incident, Service, TimelineEvent

if TYPE_CHECKING:
    from app.services.rag import RetrievedChunk


SYSTEM_INSTRUCTION = (
    "You are an SRE incident assistant. Answer only using the supplied incident "
    "context and retrieved knowledge. If the supplied context does not support an "
    "answer, say there is insufficient evidence. Do not invent a root cause or any facts."
)


class OllamaError(Exception):
    """Raised when Ollama cannot return a valid response."""


class OllamaTimeoutError(OllamaError):
    """Raised when Ollama exceeds the configured timeout."""


@dataclass(frozen=True)
class OllamaResult:
    answer: str
    model: str
    total_latency_ms: int


class OllamaService:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 30.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def build_prompt(
        self,
        incident: Incident,
        services: list[Service],
        timeline: list[TimelineEvent],
        question: str,
        knowledge_chunks: Optional[list["RetrievedChunk"]] = None,
    ) -> str:
        context = {
            "incident": incident.model_dump(mode="json"),
            "services": [service.model_dump(mode="json") for service in services],
            "timeline": [event.model_dump(mode="json") for event in timeline],
            "retrieved_knowledge": [
                {
                    "title": chunk.title,
                    "document_type": chunk.document_type,
                    "snippet": chunk.text,
                    "similarity_score": round(chunk.similarity_score, 4),
                }
                for chunk in knowledge_chunks or []
            ],
        }
        return (
            "Supplied context:\n"
            f"{json.dumps(context, indent=2)}\n\n"
            f"Question: {question}\n"
            "Answer concisely and identify the incident facts or retrieved knowledge "
            "that support the answer."
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": self.model,
            "input": texts,
            "truncate": True,
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(f"{self.base_url}/api/embed", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as error:
            raise OllamaTimeoutError("Ollama did not respond before the timeout") from error
        except httpx.HTTPError as error:
            raise OllamaError("Ollama embedding request failed") from error

        try:
            body: dict[str, Any] = response.json()
            embeddings = body["embeddings"]
            if not isinstance(embeddings, list) or len(embeddings) != len(texts):
                raise ValueError
            vectors = [
                [float(value) for value in embedding]
                for embedding in embeddings
                if isinstance(embedding, list) and embedding
            ]
            if len(vectors) != len(texts):
                raise ValueError
            return vectors
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise OllamaError("Ollama returned invalid embeddings") from error

    async def generate(
        self,
        incident: Incident,
        services: list[Service],
        timeline: list[TimelineEvent],
        question: str,
        knowledge_chunks: Optional[list["RetrievedChunk"]] = None,
    ) -> OllamaResult:
        payload = {
            "model": self.model,
            "system": SYSTEM_INSTRUCTION,
            "prompt": self.build_prompt(
                incident,
                services,
                timeline,
                question,
                knowledge_chunks,
            ),
            "stream": False,
        }
        started_at = perf_counter()

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as error:
            raise OllamaTimeoutError("Ollama did not respond before the timeout") from error
        except httpx.HTTPError as error:
            raise OllamaError("Ollama request failed") from error

        total_latency_ms = round((perf_counter() - started_at) * 1000)
        try:
            body: dict[str, Any] = response.json()
            answer = body["response"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise OllamaError("Ollama returned an invalid response") from error

        if not isinstance(answer, str) or not answer.strip():
            raise OllamaError("Ollama returned an empty response")

        return OllamaResult(
            answer=answer.strip(),
            model=str(body.get("model") or self.model),
            total_latency_ms=total_latency_ms,
        )


ollama_service = OllamaService()