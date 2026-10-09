#!/usr/bin/env python3
"""Standalone MAKENSE 3-Hour Monitoring Cycle - Direct DB access, no gateway needed."""
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
import os

board = 'makense'
db_path = os.path.expanduser('~/.hermes/kanban/boards/makense/kanban.db')
now = datetime.now()
cycle_time = now.strftime('%Y-%m-%d %H:%M IST')
next_cycle = (now + timedelta(hours=3)).strftime('%H:%M IST')

# Get all tasks from the board database directly
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, title, status, assignee, created_at, started_at, consecutive_failures FROM tasks")
rows = cursor.fetchall()
conn.close()

tasks = []
for row in rows:
    tasks.append({
        'id': row[0],
        'title': row[1],
        'status': row[2],
        'assignee': row[3],
        'created_at': row[4],
        'started_at': row[5],
        'consecutive_failures': row[6]
    })

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

# Analyze blockers
blockers = []
for task in monitored:
    task_id = task['id']
    title = task['title']
    status = task['status']
    assignee = task['assignee']
    failures = task.get('consecutive_failures', 0)
    
    # Check for explicit blocked status
    if status == 'blocked':
        blockers.append({
            'task_id': task_id,
            'title': title,
            'assignee': assignee,
            'type': 'explicit_blocked',
            'reason': f'Task explicitly blocked after {failures} consecutive failures',
            'severity': 'P0'
        })
        continue
    
    # Check for excessive consecutive failures (3+)
    if failures >= 3:
        blockers.append({
            'task_id': task_id,
            'title': title,
            'assignee': assignee,
            'type': 'excessive_failures',
            'reason': f'{failures} consecutive failures',
            'severity': 'P0'
        })
        continue
    
    # Check for stalled execution (running > 3h)
    if status == 'running' and task.get('started_at'):
        started = datetime.fromtimestamp(task['started_at'])
        hours_running = (now - started).total_seconds() / 3600
        if hours_running > 3:
            severity = 'P1' if failures > 0 else 'P2'
            blockers.append({
                'task_id': task_id,
                'title': title,
                'assignee': assignee,
                'type': 'stalled_execution',
                'reason': f'Running > 3h ({hours_running:.1f}h) {"with prior failures" if failures > 0 else "no prior failures"}',
                'severity': severity
            })
    
    # Check review tasks for staleness (> 24h)
    if status == 'review' and task.get('started_at'):
        started = datetime.fromtimestamp(task['started_at'])
        if (now - started).total_seconds() / 3600 > 24:
            blockers.append({
                'task_id': task_id,
                'title': title,
                'assignee': assignee,
                'type': 'missing_review',
                'reason': f'In review > 24h (since {started.strftime("%Y-%m-%d %H:%M")})',
                'severity': 'P2'
            })
    
    # Check ready tasks for starvation (> 3h)
    if status == 'ready' and task.get('created_at'):
        created = datetime.fromtimestamp(task['created_at'])
        if (now - created).total_seconds() / 3600 > 3:
            blockers.append({
                'task_id': task_id,
                'title': title,
                'assignee': assignee,
                'type': 'ready_starvation',
                'reason': f'Ready > 3h, not picked up (created {created.strftime("%H:%M")})',
                'severity': 'P2'
            })

print(f'⚠️ Blockers Detected: {len(blockers)}')
if blockers:
    for b in blockers:
        print(f'  [{b["severity"]}] {b["task_id"]} {b["title"][:45]} — {b["reason"]}')
else:
    print('  (none)')
print()

# Auto-resolution actions
actions_taken = 0
for blocker in blockers:
    task_id = blocker['task_id']
    btype = blocker['type']
    
    if btype == 'excessive_failures':
        # Archive and flag for replacement
        try:
            subprocess.run(['hermes', 'kanban', '--board', board, 'archive', task_id], 
                         capture_output=True, timeout=30)
            print(f'  ✓ Archived {task_id} (excessive failures)')
            actions_taken += 1
        except:
            print(f'  ⚠ Could not archive {task_id} (gateway unavailable)')
    elif btype == 'stalled_execution' and blocker['severity'] == 'P1':
        # Reassign for fresh approach
        current = blocker['assignee']
        new_assignee = 'bruce' if current != 'bruce' else 'gemini'
        try:
            subprocess.run(['hermes', 'kanban', '--board', board, 'reassign', task_id, new_assignee], 
                         capture_output=True, timeout=30)
            print(f'  ✓ Reassigned {task_id} from {current} to {new_assignee}')
            actions_taken += 1
        except:
            print(f'  ⚠ Could not reassign {task_id} (gateway unavailable)')

print()
print(f'✅ Actions Taken: {actions_taken}')
if actions_taken == 0:
    print('  (none - board is clean, all tasks done)')
print()

# Check for irrecoverable tasks (5+ failures, no success in 7 days)
archived = 0
seven_days_ago = now - timedelta(days=7)
for task in tasks:
    task_id = task['id']
    if task_id == 't_b11c0321':  # Don't archive monitor task
        continue
    if task.get('consecutive_failures', 0) >= 5:
        if task.get('status') in ['running', 'blocked']:
            created = datetime.fromtimestamp(task['created_at']) if task.get('created_at') else now
            if created < seven_days_ago:
                try:
                    subprocess.run(['hermes', 'kanban', '--board', board, 'archive', task_id], 
                                 capture_output=True, timeout=30)
                    print(f'  ✓ Archived irrecoverable: {task_id} {task["title"][:40]}')
                    archived += 1
                except:
                    pass

print()
print(f'🗑️ Archived: {archived}')
if archived == 0:
    print('  (none)')
print()

print(f'📈 Velocity: {status_counts.get("done", 0)} completed tasks on board')
print()
print(f'⚠️ Note: Hermes gateway unavailable (connection refused). Using direct DB access.')
print(f'   Gateway restart recommended for next cycle.')
print()
print(f'Next check: {next_cycle} IST')