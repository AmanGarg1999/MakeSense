import json, sys

with open('/home/huntingvision/executions.json', 'r') as f:
    data = json.load(f)

for exec in reversed(data):
    if 'news-site' in str(exec.get('taskName', '')).lower() or 'news-site' in str(exec.get('taskId', '')).lower():
        print(f"ID: {exec.get('id')}")
        print(f"Task: {exec.get('taskName')}")
        print(f"Status: {exec.get('status')}")
        print(f"Duration: {exec.get('durationMs')}ms")
        print(f"Result keys: {list(exec.get('result', {}).keys())}")
        if 'screenshot_url' in exec.get('result', {}):
            print(f"Screenshot: {exec['result']['screenshot_url']}")
        print('---')