#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timedelta

board = 'makense'
workdir = '/run/media/huntingvision/1c514555-9d09-44e0-8fcc-e90fcada2549/workspaces/MakeSense'
now = datetime.now()
cycle_time = now.strftime('%Y-%m-%d %H:%M IST')
next_cycle = (now + timedelta(hours=3)).strftime('%H:%M IST')

def run_hermes_cmd(args):
    cmd = ['hermes', 'kanban', '--board', board] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=workdir, timeout=30)
    if result.returncode != 0:
        return {'error': result.stderr, 'raw': result.stdout, 'exit_code': result.returncode}
    return {'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': 0}

# Check board status
statuses = ['running', 'ready', 'review', 'blocked']
all_tasks = {}
for status in statuses:
    result = run_hermes_cmd(['list', '--status', status, '--json'])
    if 'error' in result:
        print(f'Error fetching {status}: {result["error"]}')
        all_tasks[status] = []
    else:
        try:
            all_tasks[status] = json.loads(result['stdout'])
        except:
            all_tasks[status] = []

total = sum(len(t) for t in all_tasks.values())
print(f'Monitor Cycle: {cycle_time}')
print(f'Total tasks in monitored statuses: {total}')
for s, t in all_tasks.items():
    if t:
        print(f'  {s}: {len(t)}')
    else:
        print(f'  {s}: 0')

if total == 0:
    print('\nAll tasks done or archived - board is clean.')
    print(f'Next check: {next_cycle} IST')
else:
    print('\nBlockers found - see details above.')