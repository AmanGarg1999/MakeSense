import requests
import json

# Test with the correct schema parameters
url = "http://100.72.85.102:8000/v1/videos/sync"

prompt = "A simple red ball rolling on a table, 4K quality"

# Use the correct parameters from the schema
files = {
    'prompt': (None, prompt),
    'seconds': (None, '3'),
    'size': (None, '256x144'),
    'num_inference_steps': (None, '5'),
    'flow_shift': (None, '12'),
    'seed': (None, '42'),
    'generate_sound': (None, 'true'),
    'sound_duration': (None, '3.0'),
    'extra_params': (None, '{"task": "t2va", "audio_flow_shift": 3.0}'),
}

print("Sending test request with correct schema...")
try:
    response = requests.post(url, files=files, timeout=300)
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        # Check if video data is returned
        content_type = response.headers.get('content-type', '')
        print(f"Content-Type: {content_type}")
        if 'video' in content_type or 'octet-stream' in content_type:
            output_path = "/home/huntingvision/test_output_video.mp4"
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"Video saved to {output_path} ({len(response.content)} bytes)")
        else:
            print(f"Response: {response.text[:500]}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Request failed: {e}")
    import traceback
    traceback.print_exc()