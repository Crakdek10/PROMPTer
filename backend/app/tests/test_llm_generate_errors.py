from fastapi.testclient import TestClient
from app.main import app

def test_llm_generate_missing_config_returns_400():
    client = TestClient(app)
    payload = {
        "messages": [{"role": "user", "content": "Hola"}],
        "provider": "openai_compat",
        "config": {}
    }
    r = client.post("/llm/generate", json=payload)
    assert r.status_code == 400

    data = r.json()
    assert "error" in data
    assert data["error"]["code"] in ("CONFIG_ERROR", "APP_ERROR")
    assert "message" in data["error"]