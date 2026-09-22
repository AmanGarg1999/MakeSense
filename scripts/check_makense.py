import json, sys, subprocess

result = subprocess.run(['hermes', 'kanban', 'list', '--json'], capture_output=True, text=True)
tasks = json.loads(result.stdout)
mk_tasks = [t for t in tasks if t['id'].startswith('mk-') or t.get('title', '').startswith('mk-')]
print(f"Found {len(mk_tasks)} mk-* tasks:")
for t in mk_tasks:
    print(f"{t['id']}: {t.get('title', '')[:80]} | status={t['status']} | assignee={t.get('assignee', 'N/A')}")

# Count by status
from collections import Counter
status_counts = Counter(t['status'] for t in mk_tasks)
print("\nStatus counts:")
for status, count in status_counts.most_common():
    print(f"  {status}: {count}")

# Check specifically mk-001 through mk-028 and mk-029
expected_ids = [f"mk-{i:03d}" for i in range(1, 30)]
print("\nChecking expected mk-001 through mk-029:")
for eid in expected_ids:
    found = [t for t in mk_tasks if t['id'] == eid]
    if found:
        t = found[0]
        print(f"  {eid}: {t.get('title', '')[:60]} | status={t['status']}")
    else:
        # Also check by title prefix
        found2 = [t for t in tasks if t.get('title', '').startswith(eid)]
        if found2:
            t = found2[0]
            print(f"  {eid} (by title): {t.get('title', '')[:60]} | status={t['status']} | id={t['id']}")
        else:
            print(f"  {eid}: NOT FOUND")