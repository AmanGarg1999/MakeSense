import requests
import json

# Quick test to see initial response
url = "http://100.72.85.102:8000/v1/videos"

prompt = "test"

files = {
    'prompt': (None, prompt),
    'seconds': (None, '1'),
    'size': (None, '128x72'),
    'num_inference_steps': (None, '2'),
    'flow_shift': (None, '12'),
    'seed': (None, '42'),
    'generate_sound': (None, 'false'),
    'extra_params': (None, '{"task": "t2va"}'),
}

print("Creating minimal async job...")
try:
    response = requests.post(url, files=files, timeout=10)
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")