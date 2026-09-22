import requests
import json
import base64

url = "http://100.72.85.102:8000/v1/videos/sync"

# Try sending prompt as a form field in multipart
files = {
    'prompt': (None, 'A cute cat playing with a ball of yarn'),
}

# Other params as form fields
data = {
    'width': '512',
    'height': '288',
    'fps': '24',
    'num_frames': '48',
    'aspect_ratio': '16:9',
    'seconds': '2',
}

print(f"Sending request to {url}...")
try:
    response = requests.post(url, files=files, data=data, timeout=600)
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text[:1000]}")
    if response.status_code == 200:
        result = response.json()
        print(f"Full response: {result}")
        if 'video' in result:
            video_b64 = result['video']
            video_data = base64.b64decode(video_b64)
            output_path = "/home/huntingvision/test_output_video.mp4"
            with open(output_path, "wb") as f:
                f.write(video_data)
            print(f"Video saved to {output_path} ({len(video_data)} bytes)")
except Exception as e:
    print(f"Request failed: {e}")
    import traceback
    traceback.print_exc()