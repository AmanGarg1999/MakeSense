import requests
import json

# Test async endpoint
url = "http://100.72.85.102:8000/v1/videos/async"

prompt = "test"

files = {
    'prompt': (None, prompt),
    'width': (None, '256'),
    'height': (None, '144'),
    'fps': (None, '8'),
    'num_inference_steps': (None, '2'),
    'flow_shift': (None, '12'),
    'seed': (None, '42'),
    'aspect_ratio': (None, '16:9'),
    'extra_params': (None, '{"task": "t2va", "duration": 1, "audio_flow_shift": 3.0}'),
}

print("Testing async endpoint...")
try:
    response = requests.post(url, files=files, timeout=30)
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Request failed: {e}")