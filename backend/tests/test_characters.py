from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_character_crud_cycle():
    # ensure initially empty
    resp = client.get("/api/characters")
    assert resp.status_code == 200
    assert resp.json() == []

    # create a character
    payload = {"name": "Alice", "description": "A curious adventurer"}
    resp = client.post("/api/characters", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == payload["name"]

    char_id = data["id"]

    # fetch it individually
    resp = client.get(f"/api/characters/{char_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == payload["name"]

    # delete it
    resp = client.delete(f"/api/characters/{char_id}")
    assert resp.status_code == 204

    # ensure gone
    resp = client.get(f"/api/characters/{char_id}")
    assert resp.status_code == 404
