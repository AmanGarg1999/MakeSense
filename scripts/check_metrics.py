import requests
import json

# Check metrics endpoint
url = "http://100.72.85.102:8000/metrics"
try:
    response = requests.get(url, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response (first 2000 chars): {response.text[:2000]}")
except Exception as e:
    print(f"Error: {e}")