import json
from starlette.websockets import WebSocketDisconnect

def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "python_info" in body or "process_cpu_seconds_total" in body

def test_websocket_broadcast(client):
    with client.websocket_connect("/chat/test") as ws1:
        with client.websocket_connect("/chat/test") as ws2:
            ws1.send_text("hello")
            recv = ws2.receive_text()
            assert "hello" in recv
    try:
        client.websocket_connect("/chat/room").close()
    except WebSocketDisconnect:
        pass