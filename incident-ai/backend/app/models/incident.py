from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Severity(str, Enum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"


class IncidentStatus(str, Enum):
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class ServiceHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OUTAGE = "outage"


class TimelineEventType(str, Enum):
    DETECTED = "detected"
    UPDATE = "update"
    MITIGATION = "mitigation"
    RESOLVED = "resolved"


class Incident(BaseModel):
    id: str
    title: str
    severity: Severity
    status: IncidentStatus
    start_time: datetime
    affected_services: list[str]
    summary: str


class Service(BaseModel):
    name: str
    health_status: ServiceHealth
    p95_latency_ms: float
    error_rate_percent: float
    cpu_percent: float


class TimelineEvent(BaseModel):
    timestamp: datetime
    event_type: TimelineEventType
    message: str