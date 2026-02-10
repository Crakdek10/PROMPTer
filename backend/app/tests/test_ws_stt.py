import base64
from fastapi.testclient import TestClient
from app.main import app

def test_ws_stt_mock_flow():
    client = TestClient(app)

    with client.websocket_connect("/ws/stt") as ws:
        ws.send_json({"type": "start", "session_id": "s1", "config": {"lang": "es"}})
        msg = ws.receive_json()
        assert msg["type"] == "ready"
        assert msg["session_id"] == "s1"

        fake_audio = base64.b64encode(b"\x00\x01\x02\x03").decode("ascii")

        for i in range(3):
            ws.send_json({"type": "audio", "format": "pcm16", "sample_rate": 16000, "data": fake_audio})
            partial = ws.receive_json()
            assert partial["type"] == "partial"
            assert partial["session_id"] == "s1"

        final_msg = ws.receive_json()
        assert final_msg["type"] == "final"
        assert final_msg["session_id"] == "s1"

        ws.send_json({"type": "stop"})
        stop_final = ws.receive_json()
        assert stop_final["type"] == "final"
