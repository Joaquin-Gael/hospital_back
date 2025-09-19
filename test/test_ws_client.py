import pytest
import json

from fastapi.testclient import TestClient

@pytest.mark.integration
def test_ws_client_connection(client: TestClient, secret):
    """
    Test de integración que verifica la conexión WebSocket.
    Debe recibir un mensaje de bienvenida al conectarse.
    """
    with client.websocket_connect(f"/{secret}/ws") as websocket:
        data = websocket.receive_json()
        assert "message" in data
        assert data["message"] == "Hello WebSocket"

@pytest.mark.integration
def test_ws_client_echo(client: TestClient, secret):
    """
    Test de integración que verifica que el WebSocket hace eco de los mensajes enviados.
    """
    with client.websocket_connect(f"/{secret}/ws") as websocket:
        # Recibir mensaje de bienvenida
        websocket.receive_json()
        
        # Enviar mensaje y verificar eco
        test_message = {"message": "Test echo message"}
        websocket.send_json(test_message)
        response = websocket.receive_json()
        
        assert response == test_message