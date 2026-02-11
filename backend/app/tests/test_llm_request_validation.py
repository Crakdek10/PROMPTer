from fastapi.testclient import TestClient
from app.main import app

def test_llm_generate_invalid_body_returns_422():
    client = TestClient(app)

    payload = {"messages": "hola"}
    r = client.post("/llm/generate", json=payload)

    assert r.status_code == 422
    data = r.json()
    assert "error" in data
    assert data["error"]["code"] == "REQUEST_VALIDATION_ERROR"