from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_basic_chat_flow():
    payload = {"message": "Hello"}
    resp = client.post("/chat", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"reply": "You said: Hello"}
