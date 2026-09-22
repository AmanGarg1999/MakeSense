import json, sys
from collections import Counter

with open('/home/huntingvision/.hermes/profiles/dwight/cache/terminal-output/out-1790059885-128679-c090.log', 'r') as f:
    content = f.read()

# Find the end of the JSON array
json_end = content.rfind(']')
if json_end == -1:
    print("No JSON array found")
    sys.exit(1)

json_content = content[:json_end + 1]
data = json.loads(json_content)

mk_tasks = [t for t in data if t['title'].startswith('mk-') and not t['title'].startswith('mk-03')]
for t in sorted(mk_tasks, key=lambda x: x['title']):
    print(f"{t['title']}: {t['status']}")

# Also check mk-029
mk29 = [t for t in data if t['title'].startswith('mk-029')]
for t in mk29:
    print(f"{t['title']}: {t['status']}")

# Count by status
status_counts = Counter(t['status'] for t in mk_tasks)
print("\nStatus counts:")
for status, count in sorted(status_counts.items()):
    print(f"  {status}: {count}")

print(f"\nTotal mk-001 through mk-028 tasks: {len(mk_tasks)}")
all_done = all(t['status'] == 'done' for t in mk_tasks)
print(f"All done: {all_done}")