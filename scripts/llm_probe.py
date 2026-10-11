import json, socket, sys, urllib.request

def probe(host, port, path="/v1/models"):
    try:
        socket.create_connection((host, port), timeout=4).close()
        with urllib.request.urlopen(f"http://{host}:{port}{path}", timeout=5) as r:
            return [m["id"] for m in json.loads(r.read()).get("data", [])]
    except Exception as e:
        return f"FAIL: {type(e).__name__}: {e}"

for h, p in [("100.72.85.102", 18300), ("192.168.1.4", 18300),
             ("192.168.1.4", 8000), ("172.17.0.1", 8000)]:
    print(f"{h}:{p} ->", probe(h, p))
