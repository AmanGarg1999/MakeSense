import requests
import json

try:
    response = requests.get("http://100.72.85.102:8000/health", timeout=5)
    print(f"Health: {response.status_code}")
    print(response.text)
except Exception as e:
    print(f"Health check failed: {e}")

try:
    response = requests.get("http://100.72.85.102:8000/v1/models", timeout=5)
    print(f"Models: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Models check failed: {e}")