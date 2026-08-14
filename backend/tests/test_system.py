from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_system_online():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["system"] == "ARGOS"
    assert body["status"] == "online"


def test_health_returns_api_ok_and_database_status():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "ok"
    assert body["database"] in ("connected", "disconnected")
