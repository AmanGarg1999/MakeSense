import requests
try:
    response = requests.get("http://100.72.85.102:8000/health", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")