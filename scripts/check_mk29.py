import json, sys

with open('/home/huntingvision/.hermes/profiles/dwight/cache/terminal-output/out-1790059885-128679-c090.log', 'r') as f:
    content = f.read()

json_end = content.rfind(']')
json_content = content[:json_end + 1]
data = json.loads(json_content)

for t in data:
    if t['title'].startswith('mk-029'):
        print(f"ID: {t['id']}")
        print(f"Title: {t['title']}")
        print(f"Status: {t['status']}")
        print(f"Assignee: {t['assignee']}")
        print(f"Created: {t['created_at']}")
        print(f"Started: {t['started_at']}")
        print(f"Completed: {t['completed_at']}")
        print()