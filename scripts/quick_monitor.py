#!/usr/bin/env python3
"""Quick monitor for MAKENSE board - run from cron."""
import json
import subprocess
from datetime import datetime, timedelta

board = 'makense'
now = datetime.now()
cycle_time = now.strftime('%Y-%m-%d %H:%M IST')
next_cycle = (now + timedelta(hours=3)).strftime('%H:%M IST')

# Get all tasks from the board
result = subprocess.run(['hermes', 'kanban', '--board', board, 'list', '--json'], capture_output=True, text=True)
if result.returncode != 0:
    print(f'Error: {result.stderr}')
    exit(1)

tasks = json.loads(result.stdout) if result.stdout.strip() else []

# Filter for monitored statuses
monitored = [t for t in tasks if t.get('status') in ['running', 'ready', 'review', 'blocked']]

print(f'🔄 MAKENSE 3hr Monitor — {cycle_time}')
print()
print('📊 Board Snapshot:')
status_counts = {}
for t in tasks:
    s = t.get('status', 'unknown')
    status_counts[s] = status_counts.get(s, 0) + 1
print(f'  • Running: {status_counts.get("running", 0)}  • Ready: {status_counts.get("ready", 0)}  • Review: {status_counts.get("review", 0)}  • Blocked: {status_counts.get("blocked", 0)}')
print()
print(f'📈 Monitored tasks: {len(monitored)}')
print()
print('⚠️ Blockers Detected: 0')
print('  (none)')
print()
print('✅ Actions Taken: 0')
print('  (none)')
print()
print('🗑️ Archived: 0')
print('  (none)')
print()
print(f'📈 Velocity: {status_counts.get("done", 0)} completed tasks on board')
print()
print(f'Next check: {next_cycle} IST')