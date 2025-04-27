import pytest

from test.fetch_utils import (
    fetch_health_check,
    fetch_auth_login
)


@pytest.mark.integration
def test_fetch_health_check_response(console):
    """
    Test de integración que llama al endpoint real.
    Debe de retornar un json con el status de la DB
    """
    data = fetch_health_check(host="localhost", port=8000)
    console.print("[green]Respuesta recibida:[/]", data)
    assert isinstance(data, dict) and "status" in data.keys()

@pytest.mark.integration
def test_fetch_health_check_success(console):
    """
    Test de integración que llama al endpoint real.
    Debe estar ejecutándose un servidor en localhost:80 que responda en /_health_check/.
    """
    data = fetch_health_check(host="localhost", port=8000)
    console.print("[green]Respuesta recibida:[/]", data)
    assert data["status"] == True

@pytest.mark.integration
def test_fetch_health_check_failed(console):
    """
    Test de integración que llama al endpoint real.
    Resultado esperado {"status":False}
    """
    data = fetch_health_check(host="localhost", port=8000)
    console.print("[green]Respuesta recibida:[/]", data)
    assert data["status"] != False

@pytest.mark.integration
def test_fetch_auth_login_success(console):
    """
    Test de integración que llama al endpoint real.
    Resultado esterado {"access_token":<TOKEN>, "token_type":"Bearer"}
    """
    data = fetch_auth_login(password="12345678")
    console.print("[green]Respuesta recibida:[/]", data)
    assert "access_token" in data.keys() and "token_type" in data.keys()

@pytest.mark.integration
def test_fetch_auth_login_failed(console):
    """
    Test de integración que llama al endpoint real.
    Resultado esperado: {"detail":"Invalid credentials"}
    """
    data = fetch_auth_login()
    console.print("[green]Respuesta recibida:[/]", data)
    assert data["detail"] == "Invalid credentials payload"