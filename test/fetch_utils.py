import http.client

import json

def fetch_health_check(host: str = "localhost", port: int = 80, path: str = "/_health_check/") -> dict:
    conn = http.client.HTTPConnection(host, port)
    conn.request("GET", path)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()
    return json.loads(data)