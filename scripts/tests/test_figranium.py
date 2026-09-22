import requests
import json

# Test Figranium MCP endpoint
url = "http://localhost:11345/mcp"
headers = {
    "Authorization": "Bearer 5756f7be550308a031f33d060a556508099c0460bb88311684f01da714f404a9",
    "Content-Type": "application/json"
}

# List available tools
payload = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
}

print("Testing Figranium MCP...")
try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"Response status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Request failed: {e}")
    import traceback
    traceback.print_exc()