import requests
import json

# Test different Figranium MCP endpoints
endpoints = [
    "http://localhost:11345/mcp",
    "http://localhost:11345/mcp/",
    "http://localhost:11345/api/mcp",
    "http://localhost:11345/rpc",
    "http://localhost:11345/jsonrpc",
    "http://localhost:11345/tools/list",
]

headers = {
    "Authorization": "Bearer 5756f7be550308a031f33d060a556508099c0460bb88311684f01da714f404a9",
    "Content-Type": "application/json"
}

payload = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
}

for url in endpoints:
    print(f"\n=== Testing {url} ===")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")