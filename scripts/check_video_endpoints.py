import requests
import json

# Get detailed spec for video endpoints
url = "http://100.72.85.102:8000/openapi.json"

print("Fetching OpenAPI spec for video endpoints...")
try:
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        spec = response.json()
        paths = spec.get('paths', {})
        
        # Print video-related endpoints
        for path, methods in paths.items():
            if 'video' in path.lower():
                for method, details in methods.items():
                    print(f"\n=== {method.upper()} {path} ===")
                    print(f"Summary: {details.get('summary', 'No summary')}")
                    print(f"Description: {details.get('description', 'No description')}")
                    
                    # Print request body schema
                    if 'requestBody' in details:
                        content = details['requestBody'].get('content', {})
                        for ct, schema_info in content.items():
                            print(f"Content-Type: {ct}")
                            if 'schema' in schema_info:
                                schema = schema_info['schema']
                                print(f"Schema ref: {schema.get('$ref', 'inline')}")
                                # Print properties if available
                                if 'properties' in schema:
                                    print("Properties:")
                                    for prop_name, prop_schema in schema['properties'].items():
                                        prop_type = prop_schema.get('type', 'unknown')
                                        prop_desc = prop_schema.get('description', '')
                                        print(f"  {prop_name} ({prop_type}): {prop_desc}")
                    print()
except Exception as e:
    print(f"Request failed: {e}")