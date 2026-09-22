import requests
import json

video_id = "video_gen_6e1131af0f3b42af881fd7115bc20439"

print(f"Checking status of job {video_id}...")
try:
    response = requests.get(f"http://100.72.85.102:8000/v1/videos/{video_id}", timeout=10)
    if response.status_code == 200:
        status_data = response.json()
        print(f"Status: {json.dumps(status_data, indent=2)}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Error: {e}")