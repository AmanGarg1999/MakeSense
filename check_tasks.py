import json
with open('scripts/kanban_tasks.json') as f:
    tasks = json.load(f)

statuses = ['running', 'ready', 'review', 'blocked']
for s in statuses:
    filtered = [t for t in tasks if t.get('status') == s]
    print(f'{s}: {len(filtered)}')
    for t in filtered:
        print(f'  {t["id"]} - {t["title"][:60]} (assignee: {t.get("assignee", "none")})')