from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_chat_echo():
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert response.json() == {"reply": "Echo: Hello"}
