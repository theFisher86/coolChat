from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_chat_echo():
    payload = {"message": "Hello"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    assert response.json() == {"reply": "Echo: Hello"}
