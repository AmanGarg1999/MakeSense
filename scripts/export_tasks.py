#!/usr/bin/env python3
import json
import subprocess

# Export tasks from SQLite to JSON
result = subprocess.run([
    'sqlite3', 
    '/home/huntingvision/.hermes/kanban/boards/makense/kanban.db', 
    "SELECT id, title, status, assignee FROM tasks;"
], capture_output=True, text=True)

tasks = []
for line in result.stdout.strip().split('\n'):
    line = line.strip()
    if not line:
        continue
    parts = line.split('|')
    if len(parts) >= 4:
        tasks.append({
            'id': parts[0],
            'title': parts[1],
            'status': parts[2],
            'assignee': parts[3]
        })

with open('/run/media/huntingvision/1c514555-9d09-44e0-8fcc-e90fcada2549/workspaces/MakeSense/scripts/kanban_tasks.json', 'w') as f:
    json.dump(tasks, f, indent=2)

print(f'Saved {len(tasks)} tasks to cache')