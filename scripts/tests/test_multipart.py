import requests

url = "http://100.72.85.102:8000/v1/videos/sync"

# Send as multipart/form-data as the API expects
files = {
    'prompt': (None, 'A cute cat playing with a ball of yarn in a sunny living room, 4K quality, cinematic lighting'),
    'width': (None, '1024'),
    'height': (None, '576'),
    'fps': (None, '24'),
    'num_frames': (None, '180'),  # 7.5 seconds * 24 fps = 180 frames
    'aspect_ratio': (None, '16:9'),
    'seconds': (None, '8'),
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