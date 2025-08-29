from backend.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_update_config_preserves_blank_api_key():
    client.put(
        "/config",
        json={
            "active_provider": "gemini",
            "providers": {"gemini": {"api_key": "test-key", "model": "gemini-1.5-flash"}},
        },
    )
    r = client.put(
        "/config",
        json={"providers": {"gemini": {"api_key": ""}}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["providers"]["gemini"]["api_key_masked"] is not None

