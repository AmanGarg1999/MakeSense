import json

with open('/home/huntingvision/executions.json', 'r') as f:
    data = json.load(f)

for exec in reversed(data):
    if 'news-site' in str(exec.get('taskName', '')).lower() or 'news-site' in str(exec.get('taskId', '')).lower():
        if exec.get('status') == 500:
            print(f"ID: {exec.get('id')}")
            print(f"Task: {exec.get('taskName')}")
            print(f"Error: {exec.get('result', {}).get('error')}")
            print(f"Details: {exec.get('result', {}).get('details')}")
            print('---')