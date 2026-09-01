import asyncio
import math
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Optional, Protocol


DEFAULT_KNOWLEDGE_PATH = Path(__file__).resolve().parents[2] / "data" / "knowledge"


@dataclass(frozen=True)
class KnowledgeDocument:
    title: str
    document_type: str
    path: str
    content: str


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    title: str
    document_type: str
    text: str

    @property
    def embedding_text(self) -> str:
        return f"{self.title}\nDocument type: {self.document_type}\n{self.text}"


@dataclass(frozen=True)
class RetrievedChunk:
    title: str
    document_type: str
    text: str
    similarity_score: float


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    latency_ms: int


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


def load_documents(knowledge_path: Path = DEFAULT_KNOWLEDGE_PATH) -> list[KnowledgeDocument]:
    documents = []
    for path in sorted(knowledge_path.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 3 or not lines[0].startswith("# ") or not lines[1].startswith("Type: "):
            raise ValueError(f"Knowledge document has invalid metadata: {path.name}")
        documents.append(
            KnowledgeDocument(
                title=lines[0][2:].strip(),
                document_type=lines[1][6:].strip(),
                path=str(path),
                content="\n".join(lines[2:]).strip(),
            )
        )
    return documents


def chunk_document(
    document: KnowledgeDocument,
    max_chars: int = 700,
    overlap_chars: int = 100,
) -> list[KnowledgeChunk]:
    if max_chars <= 0 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Chunk sizes must satisfy 0 <= overlap_chars < max_chars")

    chunks = []
    start = 0
    chunk_number = 0
    while start < len(document.content):
        end = min(start + max_chars, len(document.content))
        if end < len(document.content):
            boundary = document.content.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        text = document.content[start:end].strip()
        if text:
            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"{Path(document.path).stem}-{chunk_number}",
                    title=document.title,
                    document_type=document.document_type,
                    text=text,
                )
            )
            chunk_number += 1

        if end >= len(document.content):
            break
        start = max(end - overlap_chars, start + 1)

    return chunks


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Embedding vectors must be non-empty and have equal dimensions")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._entries: list[tuple[KnowledgeChunk, list[float]]] = []

    def add(self, chunks: list[KnowledgeChunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Each knowledge chunk must have one embedding vector")
        self._entries.extend(zip(chunks, vectors))

    def search(self, query_vector: list[float], top_k: int = 3) -> list[RetrievedChunk]:
        scored_chunks = [
            RetrievedChunk(
                title=chunk.title,
                document_type=chunk.document_type,
                text=chunk.text,
                similarity_score=cosine_similarity(query_vector, vector),
            )
            for chunk, vector in self._entries
        ]
        return sorted(
            scored_chunks,
            key=lambda chunk: chunk.similarity_score,
            reverse=True,
        )[:top_k]


class RagService:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        knowledge_path: Path = DEFAULT_KNOWLEDGE_PATH,
        top_k: int = 3,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.knowledge_path = knowledge_path
        self.top_k = top_k
        self.vector_store = InMemoryVectorStore()
        self._indexed = False
        self._index_lock: Optional[asyncio.Lock] = None

    async def _ensure_index(self) -> None:
        if self._indexed:
            return
        if self._index_lock is None:
            self._index_lock = asyncio.Lock()
        async with self._index_lock:
            if self._indexed:
                return
            chunks = [
                chunk
                for document in load_documents(self.knowledge_path)
                for chunk in chunk_document(document)
            ]
            vectors = await self.embedding_provider.embed(
                [chunk.embedding_text for chunk in chunks]
            )
            self.vector_store.add(chunks, vectors)
            self._indexed = True

    async def retrieve(self, question: str) -> RetrievalResult:
        started_at = perf_counter()
        await self._ensure_index()
        query_vectors = await self.embedding_provider.embed([question])
        if len(query_vectors) != 1:
            raise ValueError("Question embedding returned an unexpected vector count")
        chunks = self.vector_store.search(query_vectors[0], self.top_k)
        return RetrievalResult(
            chunks=chunks,
            latency_ms=round((perf_counter() - started_at) * 1000),
        )