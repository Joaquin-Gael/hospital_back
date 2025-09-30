import pytest

from test.fetch_utils import (
    fetch_health_check,
    fetch_auth_login,
    fetch_id_secret,
    fetch_api_with_token
)


@pytest.mark.integration
def test_fetch_health_check_response(console, secret):
    """
    Test de integración que llama al endpoint real.
    Debe de retornar un json con el status de la DB
    """
    data = fetch_health_check(host="localhost", port=8000, path=f"/{secret}/_health_check/")
    console.print("[green]Respuesta recibida:[/]", data)
    assert isinstance(data, dict) and "status" in data.keys()

@pytest.mark.integration
def test_fetch_health_check_success(console, secret):
    """
    Test de integración que llama al endpoint real.
    Debe estar ejecutándose un servidor en localhost:80 que responda en /_health_check/.
    """
    data = fetch_health_check(host="localhost", port=8000, path=f"/{secret}/_health_check/")
    console.print("[green]Respuesta recibida:[/]", data)
    assert data["status"] == True

@pytest.mark.integration
def test_fetch_health_check_failed(console, secret):
    """
    Test de integración que llama al endpoint real.
    Resultado esperado {"status":False}
    """
    data = fetch_health_check(host="localhost", port=8000, path=f"/{secret}/_health_check/")
    console.print("[green]Respuesta recibida:[/]", data)
    assert data["status"] != False

@pytest.mark.integration
def test_fetch_auth_login_success(console, secret):
    """
    Test de integración que llama al endpoint real.
    Resultado esperado {"access_token":<TOKEN>, "token_type":"Bearer"}
    """
    data = fetch_auth_login(password="12345678", path=f"/{secret}/auth/login")
    console.print("[green]Respuesta recibida:[/]", data)
    assert "access_token" in data.keys() and "token_type" in data.keys()

@pytest.mark.integration
def test_fetch_auth_login_failed(console, secret):
    """
    Test de integración que llama al endpoint real con credenciales incorrectas.
    Resultado esperado: {"detail":"Invalid credentials"}
    """
    data = fetch_auth_login(password="contraseña_incorrecta", path=f"/{secret}/auth/login")
    console.print("[green]Respuesta recibida:[/]", data)
    assert "detail" in data.keys() and "access_token" not in data.keys()
    assert data["detail"] == "Invalid credentials payload"

@pytest.mark.integration
def test_fetch_id_secret(console):
    """
    Test de integración que verifica el endpoint de id_prefix_api_secret.
    Debe retornar un json con el id_prefix_api_secret.
    """
    data = fetch_id_secret()
    console.print("[green]Respuesta recibida:[/]", data)
    assert isinstance(data, dict) and "id_prefix_api_secret" in data.keys()
    assert isinstance(data["id_prefix_api_secret"], str)

@pytest.mark.integration
def test_fetch_user_me(console, secret):
    """
    Test de integración que verifica el endpoint de usuarios/me con autenticación.
    Debe retornar la información del usuario autenticado.
    """
    # Primero obtenemos el token de autenticación
    login_data = fetch_auth_login(password="12345678", path=f"/{secret}/auth/login")
    console.print("[green]Login exitoso:[/]", login_data)
    assert "access_token" in login_data.keys()
    
    # Usamos el token para obtener la información del usuario
    user_data = fetch_api_with_token(
        path=f"/{secret}/users/me", 
        token=login_data["access_token"]
    )
    console.print("[green]Datos de usuario:[/]", user_data)
    
    # Verificamos que la respuesta contenga la información del usuario
    assert "email" in user_data.keys()
    assert user_data["email"] == "admin@admin.com"

@pytest.mark.integration
def test_create_and_get_user(console, secret):
    """
    Test de integración que verifica la creación y obtención de un usuario.
    """
    # Primero obtenemos el token de autenticación del admin
    login_data = fetch_auth_login(password="12345678", path=f"/{secret}/auth/login")
    assert "access_token" in login_data.keys()
    admin_token = login_data["access_token"]
    
    # Creamos un nuevo usuario
    import uuid
    random_suffix = str(uuid.uuid4())[:8]
    new_user_data = {
        "email": f"test_user_{random_suffix}@example.com",
        "password": "password123",
        "full_name": "Test User",
        "is_active": True
    }
    
    create_response = fetch_api_with_token(
        path=f"/{secret}/users/", 
        method="POST",
        token=admin_token,
        body=new_user_data
    )
    console.print("[green]Usuario creado:[/]", create_response)
    
    # Verificamos que el usuario se haya creado correctamente
    assert "id" in create_response.keys()
    assert create_response["email"] == new_user_data["email"]
    
    # Obtenemos el usuario creado por su ID
    user_id = create_response["id"]
    get_user_response = fetch_api_with_token(
        path=f"/{secret}/users/{user_id}", 
        token=admin_token
    )
    console.print("[green]Usuario obtenido:[/]", get_user_response)
    
    # Verificamos que la información del usuario sea correcta
    assert get_user_response["id"] == user_id
    assert get_user_response["email"] == new_user_data["email"]
    assert get_user_response["full_name"] == new_user_data["full_name"]