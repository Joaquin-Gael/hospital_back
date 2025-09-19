import http.client

import json

def fetch_id_secret(host: str = "localhost", port: int = 8000, path: str = "/id_prefix_api_secret/") -> dict:
    conn = http.client.HTTPConnection(host, port)
    conn.request("GET", path)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()
    return json.loads(data)

def fetch_health_check(host: str = "localhost", port: int = 8000, path: str = "/_health_check/") -> dict:
    conn = http.client.HTTPConnection(host, port)
    conn.request("GET", path)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()
    return json.loads(data)


def fetch_auth_login(host: str = "localhost", port: int = 8000, path: str = "/auth/login", password: str = "<PASSWORD>") -> dict:
    conn = http.client.HTTPConnection(host, port)
    conn.request("POST", path,
                 json.dumps(
                     {"email": "admin@admin.com", "password": password}
                 ),
                 {"Content-Type": "application/json"})
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()
    return json.loads(data)


def fetch_api_with_token(host: str = "localhost", port: int = 8000, path: str = "/users/me", method: str = "GET", token: str = None, body: dict = None) -> dict:
    """
    Función genérica para hacer peticiones a la API con token de autenticación
    """
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    conn = http.client.HTTPConnection(host, port)
    
    if body and method in ["POST", "PUT", "PATCH"]:
        conn.request(method, path, json.dumps(body), headers)
    else:
        conn.request(method, path, headers=headers)
    
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()
    
    return json.loads(data)