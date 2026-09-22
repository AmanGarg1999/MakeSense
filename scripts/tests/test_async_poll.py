import requests
import json

# Test async endpoint - create job then poll
url = "http://100.72.85.102:8000/v1/videos"

prompt = "A simple red ball rolling on a table"

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

print("Creating async video generation job...")
try:
    response = requests.post(url, files=files, timeout=30)
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        video_id = result.get('id') or result.get('video_id')
        if video_id:
            print(f"Job created with ID: {video_id}")
            # Poll for completion
            import time
            for i in range(60):  # Poll for up to 5 minutes
                time.sleep(5)
                status_resp = requests.get(f"http://100.72.85.102:8000/v1/videos/{video_id}", timeout=10)
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    print(f"Poll {i+1}: Status = {status_data.get('status', 'unknown')}")
                    if status_data.get('status') == 'completed':
                        # Download the video
                        download_resp = requests.get(f"http://100.72.85.102:8000/v1/videos/{video_id}/content", timeout=30)
                        if download_resp.status_code == 200:
                            output_path = "/home/huntingvision/test_output_video.mp4"
                            with open(output_path, "wb") as f:
                                f.write(download_resp.content)
                            print(f"Video saved to {output_path} ({len(download_resp.content)} bytes)")
                        break
                    elif status_data.get('status') == 'failed':
                        print(f"Job failed: {status_data}")
                        break
                else:
                    print(f"Poll {i+1}: Error checking status: {status_resp.text}")
        else:
            print("No video_id in response")
except Exception as e:
    print(f"Request failed: {e}")
    import traceback
    traceback.print_exc()