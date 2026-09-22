import requests
import json

# Get detailed schema for video sync endpoint
url = "http://100.72.85.102:8000/openapi.json"

print("Fetching OpenAPI spec for video sync endpoint schema...")
try:
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        spec = response.json()
        components = spec.get('components', {})
        schemas = components.get('schemas', {})
        
        # Find the video sync schema
        for name, schema in schemas.items():
            if 'sync' in name.lower() and 'video' in name.lower():
                print(f"\n=== Schema: {name} ===")
                print(json.dumps(schema, indent=2))
                print()
except Exception as e:
    print(f"Request failed: {e}")