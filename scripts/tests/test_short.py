import requests

url = "http://100.72.85.102:8000/v1/videos/sync"

# Send as multipart/form-data as the API expects - shorter test
files = {
    'prompt': (None, 'A cute cat playing'),
    'width': (None, '512'),
    'height': (None, '288'),
    'fps': (None, '24'),
    'num_frames': (None, '48'),  # 2 seconds
    'aspect_ratio': (None, '16:9'),
    'seconds': (None, '2'),
}

print(f"Sending multipart request to {url}...")
try:
    response = requests.post(url, files=files, timeout=600)
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text[:1000]}")
    if response.status_code == 200:
        result = response.json()
        print(f"Full response: {result}")
except Exception as e:
    print(f"Request failed: {e}")
    import traceback
    traceback.print_exc()