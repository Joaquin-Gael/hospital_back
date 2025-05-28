import pytest

from fastapi.testclient import TestClient

@pytest.mark.integration
def test_ws_client(client: TestClient):
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data == {"message": "Hello WebSocket"}