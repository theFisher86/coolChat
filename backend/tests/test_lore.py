from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_lore_crud_cycle():
    resp = client.get("/api/lore")
    assert resp.status_code == 200
    assert resp.json() == []

    payload = {"keyword": "wizard", "content": "Wizards channel arcane energy"}
    resp = client.post("/api/lore", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 1
    assert data["keyword"] == payload["keyword"]

    entry_id = data["id"]

    resp = client.get(f"/api/lore/{entry_id}")
    assert resp.status_code == 200
    assert resp.json()["content"] == payload["content"]

    resp = client.delete(f"/api/lore/{entry_id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/lore/{entry_id}")
    assert resp.status_code == 404
