import json
import subprocess
from datetime import datetime

board = 'makense'
workdir = '/run/media/huntingvision/1c514555-9d09-44e0-8fcc-e90fcada2549/workspaces/MakeSense'

def run_hermes_cmd(args):
    cmd = ['hermes', 'kanban', '--board', board] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=workdir, timeout=30)
    if result.returncode != 0:
        return {'error': result.stderr, 'raw': result.stdout, 'exit_code': result.returncode}
    return {'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': 0}

# Get tasks by status
for status in ['running', 'ready', 'review', 'blocked']:
    result = run_hermes_cmd(['list', '--status', status, '--json'])
    if 'error' in result:
        print(f'Error fetching {status}: {result["error"]}')
    else:
        try:
            tasks = json.loads(result['stdout'])
            print(f'{status}: {len(tasks)} tasks')
            for t in tasks:
                print(f'  {t["id"]} | {t["title"][:60]} | {t.get("assignee", "")}')
        except:
            print(f'{status}: parse error')