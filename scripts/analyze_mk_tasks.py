import json, re
with open('/home/huntingvision/.hermes/profiles/dwight/cache/terminal-output/out-1790057828-2442872-8e50.log', 'r') as f:
    tasks = json.load(f)

mk_tasks = []
for t in tasks:
    title = t.get('title', '')
    match = re.match(r'mk-(\d{3})', title)
    if match:
        num = int(match.group(1))
        if 1 <= num <= 29:
            mk_tasks.append(t)

print(f"Total mk-001 through mk-029 tasks: {len(mk_tasks)}")

from collections import Counter
status_counts = Counter(t.get('status') for t in mk_tasks)
print("Status counts:")
for status, count in sorted(status_counts.items()):
    print(f"  {status}: {count}")

print("\nAll mk-001 through mk-029 tasks:")
for t in sorted(mk_tasks, key=lambda x: int(re.match(r'mk-(\d{3})', x.get('title', '')).group(1))):
    title = t.get('title', '')
    status = t.get('status', '')
    assignee = t.get('assignee', '')
    completed = t.get('completed_at', 0)
    print(f"  [{status}] {title} (assignee: {assignee}, completed: {completed})")