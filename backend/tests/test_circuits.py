from fastapi.testclient import TestClient

from backend.main import app
from backend.database import create_tables

create_tables()

client = TestClient(app)


def test_circuit_crud_cycle():
    resp = client.get("/circuits/")
    assert resp.status_code == 200
    assert resp.json() == []

    payload = {"name": "Test", "description": "desc", "data": {"nodes": []}}
    resp = client.post("/circuits/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    cid = data["id"]
    assert data["name"] == payload["name"]

    resp = client.get(f"/circuits/{cid}")
    assert resp.status_code == 200
    assert resp.json()["data"] == payload["data"]

    update = {"name": "Test2", "description": "d2", "data": {"nodes": [1]}}
    resp = client.put(f"/circuits/{cid}", json=update)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test2"

    resp = client.delete(f"/circuits/{cid}")
    assert resp.status_code == 204

    resp = client.get(f"/circuits/{cid}")
    assert resp.status_code == 404
