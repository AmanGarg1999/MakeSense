import json
with open('scripts/kanban_tasks.json') as f:
    tasks = json.load(f)

all_statuses = {}
for t in tasks:
    s = t.get('status', 'unknown')
    all_statuses[s] = all_statuses.get(s, 0) + 1

print('All statuses:')
for s, c in sorted(all_statuses.items()):
    print(f'  {s}: {c}')