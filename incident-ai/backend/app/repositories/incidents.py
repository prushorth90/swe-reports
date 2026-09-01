from datetime import datetime, timezone
from typing import Optional

from app.models.incident import Incident, Service, TimelineEvent


def utc_datetime(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


INCIDENTS = (
    Incident(
        id="inc-2026-001",
        title="Checkout requests timing out",
        severity="SEV1",
        status="monitoring",
        start_time=utc_datetime(2026, 8, 31, 9, 12),
        affected_services=["checkout-api", "payments-service", "redis"],
        summary=(
            "Checkout requests experienced elevated latency after Redis connection "
            "pool exhaustion caused retries across payment processing."
        ),
    ),
    Incident(
        id="inc-2026-002",
        title="Inventory availability lag",
        severity="SEV2",
        status="identified",
        start_time=utc_datetime(2026, 8, 30, 16, 40),
        affected_services=["inventory-service", "redis"],
        summary=(
            "Inventory updates are delayed because a cache invalidation worker is "
            "processing events below its normal throughput."
        ),
    ),
    Incident(
        id="inc-2026-003",
        title="Payment authorization errors",
        severity="SEV2",
        status="resolved",
        start_time=utc_datetime(2026, 8, 29, 13, 5),
        affected_services=["payments-service", "checkout-api"],
        summary=(
            "A stale upstream certificate briefly increased payment authorization "
            "errors before the certificate bundle was refreshed."
        ),
    ),
)


SERVICES_BY_INCIDENT = {
    "inc-2026-001": (
        Service(
            name="checkout-api",
            health_status="degraded",
            p95_latency_ms=1840.0,
            error_rate_percent=8.7,
            cpu_percent=76.4,
        ),
        Service(
            name="payments-service",
            health_status="degraded",
            p95_latency_ms=1210.0,
            error_rate_percent=5.2,
            cpu_percent=68.1,
        ),
        Service(
            name="redis",
            health_status="outage",
            p95_latency_ms=930.0,
            error_rate_percent=12.4,
            cpu_percent=94.6,
        ),
    ),
    "inc-2026-002": (
        Service(
            name="inventory-service",
            health_status="degraded",
            p95_latency_ms=680.0,
            error_rate_percent=2.8,
            cpu_percent=82.3,
        ),
        Service(
            name="redis",
            health_status="healthy",
            p95_latency_ms=18.0,
            error_rate_percent=0.1,
            cpu_percent=42.7,
        ),
    ),
    "inc-2026-003": (
        Service(
            name="payments-service",
            health_status="healthy",
            p95_latency_ms=245.0,
            error_rate_percent=0.3,
            cpu_percent=48.2,
        ),
        Service(
            name="checkout-api",
            health_status="healthy",
            p95_latency_ms=310.0,
            error_rate_percent=0.2,
            cpu_percent=44.9,
        ),
    ),
}


TIMELINE_BY_INCIDENT = {
    "inc-2026-001": (
        TimelineEvent(
            timestamp=utc_datetime(2026, 8, 31, 9, 12),
            event_type="detected",
            message="Checkout timeout alert crossed the critical threshold.",
        ),
        TimelineEvent(
            timestamp=utc_datetime(2026, 8, 31, 9, 24),
            event_type="update",
            message="Responders linked request retries to Redis pool exhaustion.",
        ),
        TimelineEvent(
            timestamp=utc_datetime(2026, 8, 31, 9, 41),
            event_type="mitigation",
            message="Redis capacity was increased and retry concurrency was reduced.",
        ),
    ),
    "inc-2026-002": (
        TimelineEvent(
            timestamp=utc_datetime(2026, 8, 30, 16, 40),
            event_type="detected",
            message="Inventory freshness checks reported delayed updates.",
        ),
        TimelineEvent(
            timestamp=utc_datetime(2026, 8, 30, 17, 2),
            event_type="update",
            message="The cache invalidation worker was identified as the bottleneck.",
        ),
    ),
    "inc-2026-003": (
        TimelineEvent(
            timestamp=utc_datetime(2026, 8, 29, 13, 5),
            event_type="detected",
            message="Payment authorization failures exceeded five percent.",
        ),
        TimelineEvent(
            timestamp=utc_datetime(2026, 8, 29, 13, 18),
            event_type="mitigation",
            message="The upstream certificate bundle was refreshed.",
        ),
        TimelineEvent(
            timestamp=utc_datetime(2026, 8, 29, 13, 31),
            event_type="resolved",
            message="Authorization success rates returned to baseline.",
        ),
    ),
}


class IncidentRepository:
    def list_incidents(self) -> list[Incident]:
        return list(INCIDENTS)

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return next((incident for incident in INCIDENTS if incident.id == incident_id), None)

    def list_services(self, incident_id: str) -> list[Service]:
        return list(SERVICES_BY_INCIDENT.get(incident_id, ()))

    def list_timeline(self, incident_id: str) -> list[TimelineEvent]:
        return list(TIMELINE_BY_INCIDENT.get(incident_id, ()))


incident_repository = IncidentRepository()