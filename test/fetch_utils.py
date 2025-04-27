import http.client

import json

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