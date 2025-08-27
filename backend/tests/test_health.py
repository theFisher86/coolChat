from fastapi.testclient import TestClient

from backend.main import app


def test_health_endpoint():
    """Ensure the health endpoint returns an OK status."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

