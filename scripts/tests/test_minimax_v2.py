import requests
import json
import base64

url = "http://100.72.85.102:8000/v1/videos/sync"

# Format 2: prompt inside extra_params
payload = {
    "width": 1024,
    "height": 576,
    "fps": 24,
    "num_inference_steps": 15,
    "flow_shift": 12,
    "seed": 42,
    "aspect_ratio": "16:9",
    "extra_params": {
        "task": "t2va",
        "duration": 7.5,
        "audio_flow_shift": 3.0,
        "prompt": "A cute cat playing with a ball of yarn in a sunny living room, 4K quality, cinematic lighting"
    }
}

print(f"Payload: {json.dumps(payload, indent=2)}")
try:
    response = requests.post(url, json=payload, timeout=300)
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    if response.status_code == 200:
        result = response.json()
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