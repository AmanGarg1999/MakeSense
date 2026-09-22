# MAKENSE 3-Hour Monitoring Protocol

## Overview

This document defines the automated 3-hour monitoring cadence for the MakeSense MVP delivery pipeline. The protocol ensures continuous progress tracking, blocker detection, and automated resolution across all active kanban tasks.

## Cadence Configuration

- **Frequency**: Every 3 hours (0, 3, 6, 9, 12, 15, 18, 21 UTC)
- **Trigger**: Cron job `kanban-monitor-3hr` (see cron config below)
- **Scope**: All tasks on `makense` board with status `running`, `ready`, `review`, `blocked`
- **Delivery**: Telegram summary to home channel (chat_id: 8500700729)

## Cycle Execution Steps

### 1. Pull Task Status
Query all tasks from the `makense` board with statuses:
- `running` — actively being worked on
- `ready` — waiting for worker pickup
- `review` — awaiting human/reviewer approval
- `blocked` — stalled and needs intervention

Collect for each task:
- Task ID, title, assignee, status, priority
- Started timestamp, last heartbeat, run count
- Parent/child dependencies
- Recent comments and events

### 2. Identify Blockers

A task is **blocked** if ANY of the following conditions are met:

| Condition | Threshold | Detection Method |
|-----------|-----------|------------------|
| Stalled execution | > 3 hours (1 cycle) without heartbeat | `last_heartbeat < now - 3h` |
| Excessive retries | > 3 failed runs | `run_count > 3 AND outcome != success` |
| Failed CI / checks | Any run with `outcome: failed` + CI error markers | Check run metadata for CI failure patterns |
| Missing review | In `review` status > 24 hours | `status == review AND started_at < now - 24h` |
| Dependency deadlock | Parent stuck in `running` > 2 cycles | Check parent task status recursively |
| Worker unreachable | Assignee profile has no active runs > 6h | Cross-reference profile activity |

### 3. Auto-Resolution Actions

For each identified blocker, apply the first matching resolution:

| Blocker Type | Resolution |
|--------------|------------|
| Stalled task (no heartbeat) | Reassign to same profile (new run) OR split into subtasks if > 2 days old |
| Failed CI | Attach error logs, create child task "Fix CI: <original title>" assigned to same profile |
| Missing review | Ping reviewer via Telegram, escalate to `dwight` after 24h |
| Dependency deadlock | Unblock parent first (recursive), then re-promote child |
| Worker unreachable | Reassign to alternate profile per routing rules (bruce↔gemini↔spark) |
| Irrecoverable failure | Archive task with error logs, create replacement task with root cause in body |

**Routing rules for reassignment:**
- Code/DevOps/infra/debugging → `bruce`
- Research/web/content/OCR/browser → `gemini`
- Quick/private/offline/experiments → `spark`

### 4. Archive Irrecoverable Tasks

A task is **irrecoverable** if:
- 5+ failed runs with distinct error patterns
- No progress for > 7 days (168 hours)
- Explicitly marked `capability` blocker (no agent can resolve)
- Superseded by newer task covering same scope

Archive action:
1. Attach all error logs and run metadata as artifacts
2. Set status `archived` (or `done` with `result: "archived: <reason>"`)
3. Create replacement task if scope still needed, referencing archived task

### 5. Telegram Summary

Post to home channel with format:

```
🔄 MAKENSE 3hr Monitor — <timestamp IST>

📊 Board Snapshot:
  • Running: <count>  • Ready: <count>  • Review: <count>  • Blocked: <count>

⚠️ Blockers Detected: <count>
  <task_id> <title> — <blocker reason> → <action taken>

✅ Resolved This Cycle: <count>
  <task_id> <title> — <resolution>

🗑️ Archived: <count>
  <task_id> <title> — <reason>

📈 Velocity: <tasks completed this cycle> / <tasks started this cycle>

Next check: <next cycle time IST>
```

## Cron Job Configuration

```yaml
name: "kanban-monitor-3hr"
schedule: "0 */3 * * *"  # Every 3 hours at minute 0
deliver: "telegram"
skills: ["chief-of-staff-kanban"]
prompt: |
  Execute the 3-hour monitoring cycle per MONITORING_PROTOCOL.md:
  1. Pull all running/ready/review/blocked tasks from makense board
  2. Identify blockers using thresholds defined in protocol
  3. Apply auto-resolution actions (reassign, split, escalate, archive)
  4. Post summary to Telegram home channel
  5. Log cycle results to kanban comment on this monitor task
```

## Manual Trigger

To run immediately outside schedule:
```bash
hermes cron run kanban-monitor-3hr --prompt "Manual trigger: run full monitoring cycle now"
```

## Monitoring Task Self-Management

The monitor itself is a kanban task (`t_b11c0321` → creates recurring child). Each cycle:
1. Creates a child task `monitor-cycle-<timestamp>` with assignee `dwight`
2. Child runs the protocol, posts summary, completes
3. Parent task remains `running` as the living protocol owner

## Escalation Matrix

| Severity | Condition | Escalation |
|----------|-----------|------------|
| P0 | > 3 tasks blocked simultaneously | Immediate Telegram alert + create triage task for `dwight` |
| P1 | Single task blocked > 2 cycles | Auto-reassign + Telegram notification |
| P2 | Task in review > 48h | Ping reviewer, create reminder task |
| P3 | Velocity < 1 task/cycle for 3 cycles | Create analysis task for `dwight` |

## Metrics Tracked

- Cycle duration (target: < 2 minutes)
- Blockers detected/resolved per cycle
- Tasks completed per cycle (velocity)
- Reassignment rate
- Archive rate
- False positive blocker rate

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-19 | dwight | Initial protocol from task t_b11c0321 |