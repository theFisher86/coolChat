from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import models
from backend.database import get_db
from backend.routers import characters

# Create an in-memory SQLite database for testing
engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(characters.router)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_character_router_crud_cycle():
    # Initially empty
    resp = client.get("/characters/")
    assert resp.status_code == 200
    assert resp.json() == []

    # Create character
    payload = {"name": "Alice", "description": "A curious adventurer"}
    resp = client.post("/characters/", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == payload["name"]

    char_id = data["id"]

    # Read list
    resp = client.get("/characters/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Read single
    resp = client.get(f"/characters/{char_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == payload["name"]

    # Update
    update_payload = {"name": "Alice", "description": "Updated"}
    resp = client.put(f"/characters/{char_id}", json=update_payload)
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated"

    # Delete
    resp = client.delete(f"/characters/{char_id}")
    assert resp.status_code == 204

    # Ensure deleted
    resp = client.get(f"/characters/{char_id}")
    assert resp.status_code == 404
