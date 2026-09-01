import hashlib
import json
import os
import re
from typing import Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.models.incident import AssistantResponse, Incident, Service, TimelineEvent
from app.services.query_router import QueryRoute


class CacheService:
    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        client: Optional[Redis] = None,
    ) -> None:
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl_seconds = ttl_seconds or int(os.getenv("CACHE_TTL_SECONDS", "300"))
        self.client = client or Redis.from_url(self.redis_url, decode_responses=True)

    def build_key(
        self,
        incident: Incident,
        services: list[Service],
        timeline: list[TimelineEvent],
        question: str,
        route: QueryRoute,
    ) -> str:
        normalized_question = re.sub(r"[^a-z0-9%]+", " ", question.lower()).strip()
        context = {
            "incident": incident.model_dump(mode="json"),
            "services": [service.model_dump(mode="json") for service in services],
            "timeline": [event.model_dump(mode="json") for event in timeline],
        }
        context_version = self._digest(json.dumps(context, sort_keys=True))
        question_digest = self._digest(normalized_question)
        return f"incident-assistant:{incident.id}:{context_version}:{route.value}:{question_digest}"

    async def get(self, key: str) -> Optional[AssistantResponse]:
        try:
            cached_value = await self.client.get(key)
            if cached_value is None:
                return None
            response = AssistantResponse.model_validate_json(cached_value)
            return response.model_copy(update={"cache_hit": True})
        except (RedisError, ValueError):
            return None

    async def set(self, key: str, response: AssistantResponse) -> None:
        try:
            await self.client.set(
                key,
                response.model_dump_json(),
                ex=self.ttl_seconds,
            )
        except RedisError:
            return

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


cache_service = CacheService()