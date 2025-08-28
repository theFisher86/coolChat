from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_chat_flow():
    messages = ["Hi", "How are you?"]
    for msg in messages:
        resp = client.post("/chat", json={"message": msg})
        assert resp.status_code == 200
        assert resp.json()["reply"] == f"Echo: {msg}"
