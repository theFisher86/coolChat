from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_memory_crud_cycle():
    # initially empty
    resp = client.get("/memory")
    assert resp.status_code == 200
    assert resp.json() == []

    payload = {"content": "This is a fairly long message that should be summarized into a shorter snippet for storage."}
    resp = client.post("/memory", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == payload["content"]
    assert len(data["summary"]) < len(payload["content"])
    mem_id = data["id"]

    # retrieve
    resp = client.get(f"/memory/{mem_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == mem_id

    # delete
    resp = client.delete(f"/memory/{mem_id}")
    assert resp.status_code == 204

    resp = client.get("/memory")
    assert resp.status_code == 200
    assert resp.json() == []
