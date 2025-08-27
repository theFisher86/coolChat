from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_create_and_read_character():
    payload = {
        "name": "Alice",
        "description": "Adventurer",
        "avatar_url": "http://example.com/avatar.png",
    }
    response = client.post("/characters/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    char_id = data["id"]

    list_resp = client.get("/characters/")
    assert list_resp.status_code == 200
    assert any(item["id"] == char_id for item in list_resp.json())

    get_resp = client.get(f"/characters/{char_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == char_id
