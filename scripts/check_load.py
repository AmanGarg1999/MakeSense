import requests
import json

# Check server metrics/load
url = "http://100.72.85.102:8000/load"
try:
    response = requests.get(url, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")