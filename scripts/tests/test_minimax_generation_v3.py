import requests
import json
import base64

# Test minimax-H3 video generation via vLLM server - use multipart/form-data as per OpenAPI spec
url = "http://100.72.85.102:8000/v1/videos/sync"

prompt = "A cute cat playing with a ball of yarn in a sunny living room, 4K quality, cinematic lighting"

# Use multipart/form-data as required by the API
files = {
    'prompt': (None, prompt),
    'width': (None, '1024'),
    'height': (None, '576'),
    'fps': (None, '24'),
    'num_inference_steps': (None, '15'),
    'flow_shift': (None, '12'),
    'seed': (None, '42'),
    'aspect_ratio': (None, '16:9'),
    'extra_params': (None, '{"task": "t2va", "duration": 7.5, "audio_flow_shift": 3.0}'),
}

print(f"Sending request to {url}...")
print(f"Prompt: {prompt}")

try:
    response = requests.post(url, files=files, timeout=300)
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response keys: {list(result.keys())}")
        
        if 'video' in result:
            video_b64 = result['video']
            video_data = base64.b64decode(video_b64)
            output_path = "/home/huntingvision/test_output_video.mp4"
            with open(output_path, "wb") as f:
                f.write(video_data)
            print(f"Video saved to {output_path} ({len(video_data)} bytes)")
        elif 'file_path' in result:
            print(f"Video file path: {result['file_path']}")
        else:
            print(f"Full response: {json.dumps(result, indent=2)}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Request failed: {e}")
    import traceback
    traceback.print_exc()