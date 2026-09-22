import requests
import json

# Check available endpoints
url = "http://100.72.85.102:8000/openapi.json"

print("Fetching OpenAPI spec...")
try:
    response = requests.get(url, timeout=30)
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        spec = response.json()
        paths = spec.get('paths', {})
        for path, methods in paths.items():
            for method, details in methods.items():
                print(f"  {method.upper()} {path}: {details.get('summary', 'No summary')}")
    else:
        print(f"Error: {response.text[:500]}")
except Exception as e:
    print(f"Request failed: {e}")