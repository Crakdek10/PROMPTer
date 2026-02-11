from fastapi.testclient import TestClient
from app.main import app

def test_get_providers_stt():
    client = TestClient(app)
    r = client.get("/providers/stt")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    names = [x["name"] for x in data["items"]]
    assert "cloud_stub" in names

def test_get_providers_llm():
    client = TestClient(app)
    r = client.get("/providers/llm")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    names = [x["name"] for x in data["items"]]
    assert "openai_compat" in names