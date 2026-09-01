from fastapi.testclient import TestClient

from app.main import app

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