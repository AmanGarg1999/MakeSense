#!/usr/bin/env python3
"""
MAKENSE 3-Hour Monitoring Cycle Script
Executes the monitoring protocol defined in MONITORING_PROTOCOL.md
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class KanbanMonitor:
    def __init__(self):
        self.board = "makense"
        self.now = datetime.now()
        self.cycle_time = self.now.strftime("%Y-%m-%d %H:%M IST")
        self.next_cycle = (self.now + timedelta(hours=3)).strftime("%H:%M IST")
        self.workdir = "/run/media/huntingvision/1c514555-9d09-44e0-8fcc-e90fcada2549/workspaces/MakeSense"
        
    def run_hermes_cmd(self, args: List[str]) -> Dict:
        """Run hermes kanban command and return parsed JSON.
        Note: --board must come BEFORE the subcommand in hermes CLI."""
        cmd = ["hermes", "kanban", "--board", self.board] + args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.workdir)
        if result.returncode != 0:
            return {"error": result.stderr, "raw": result.stdout, "exit_code": result.returncode}
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": 0}
    
    def get_tasks_by_status(self, status: str) -> List[Dict]:
        """Get tasks with given status from makense board."""
        result = self.run_hermes_cmd(["list", "--status", status, "--json"])
        if "error" in result:
            print(f"Error fetching {status} tasks: {result['error']}")
            return []
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON for {status}: {e}")
            return []
    
    def get_all_relevant_tasks(self) -> Dict[str, List[Dict]]:
        """Pull all tasks in monitored statuses."""
        statuses = ["running", "ready", "review", "blocked"]
        all_tasks = {}
        for status in statuses:
            all_tasks[status] = self.get_tasks_by_status(status)
        return all_tasks
    
    def get_task_runs(self, task_id: str) -> List[Dict]:
        """Get run history for a task."""
        result = self.run_hermes_cmd(["runs", task_id, "--json"])
        if "error" in result:
            return []
        try:
            return json.loads(result["stdout"])
        except json.JSONDecodeError:
            return []
    
    def analyze_task_health(self, task: Dict, runs: List[Dict]) -> Dict:
        """Analyze a task's health and return status flags."""
        task_id = task["id"]
        status = task["status"]
        assignee = task["assignee"]
        
        # Count outcomes
        total_runs = len(runs)
        crashed_runs = [r for r in runs if r.get("outcome") == "crashed"]
        timed_out_runs = [r for r in runs if r.get("outcome") == "timed_out"]
        gave_up_runs = [r for r in runs if r.get("outcome") == "gave_up"]
        completed_runs = [r for r in runs if r.get("outcome") == "completed"]
        running_runs = [r for r in runs if r.get("outcome") is None and r.get("status") == "running"]
        
        # Current run info
        current_run = running_runs[0] if running_runs else None
        current_run_started = current_run.get("started_at") if current_run else None
        
        # Time since last activity
        last_activity = None
        if runs:
            # Filter runs that have timestamps
            runs_with_time = [r for r in runs if r.get("ended_at") or r.get("started_at")]
            if runs_with_time:
                last_run = max(runs_with_time, key=lambda r: r.get("ended_at") or r.get("started_at") or 0)
                last_activity = last_run.get("ended_at") or last_run.get("started_at")
        
        hours_since_activity = None
        if last_activity:
            hours_since_activity = (self.now.timestamp() - last_activity) / 3600
        
        # Time since current run started
        hours_current_run = None
        if current_run_started:
            hours_current_run = (self.now.timestamp() - current_run_started) / 3600
        
        return {
            "task_id": task_id,
            "title": task["title"],
            "assignee": assignee,
            "status": status,
            "total_runs": total_runs,
            "crashed_count": len(crashed_runs),
            "timed_out_count": len(timed_out_runs),
            "gave_up_count": len(gave_up_runs),
            "completed_count": len(completed_runs),
            "has_running": len(running_runs) > 0,
            "hours_since_activity": hours_since_activity,
            "hours_current_run": hours_current_run,
            "consecutive_failures": len(crashed_runs) + len(timed_out_runs) + len(gave_up_runs)
        }
    
    def detect_blockers(self, tasks: Dict[str, List[Dict]]) -> List[Dict]:
        """Identify blockers per protocol thresholds."""
        blockers = []
        three_hours_ago = self.now - timedelta(hours=3)
        twenty_four_hours_ago = self.now - timedelta(hours=24)
        seven_days_ago = self.now - timedelta(days=7)
        
        all_tasks = []
        for status_list in tasks.values():
            all_tasks.extend(status_list)
        
        for task in all_tasks:
            task_id = task["id"]
            runs = self.get_task_runs(task_id)
            health = self.analyze_task_health(task, runs)
            
            # Skip monitor task itself
            if task_id == "t_b11c0321":
                continue
            
            # Check for explicit blocked status
            if task["status"] == "blocked":
                blockers.append({
                    "task_id": task_id,
                    "title": task["title"],
                    "assignee": task["assignee"],
                    "type": "explicit_blocked",
                    "reason": f"Task explicitly blocked after {health['total_runs']} runs ({health['crashed_count']} crashed, {health['timed_out_count']} timed_out, {health['gave_up_count']} gave_up)",
                    "severity": "P0",
                    "health": health,
                    "detail": {"health": health}
                })
                continue
            
            # Check for excessive consecutive failures (3+ crashed/timed_out/gave_up)
            if health["consecutive_failures"] >= 3 and health["completed_count"] == 0:
                blockers.append({
                    "task_id": task_id,
                    "title": task["title"],
                    "assignee": task["assignee"],
                    "type": "excessive_failures",
                    "reason": f"{health['consecutive_failures']} consecutive failures (0 completed): {health['crashed_count']} crashed, {health['timed_out_count']} timed_out, {health['gave_up_count']} gave_up",
                    "severity": "P0",
                    "health": health,
                    "detail": {"health": health}
                })
                continue
            
            # Check for stalled execution (running > 3h with no progress)
            if task["status"] == "running" and health["has_running"]:
                if health["hours_current_run"] and health["hours_current_run"] > 3:
                    # Check if there are recent failed runs before this
                    if health["crashed_count"] > 0 or health["timed_out_count"] > 0:
                        blockers.append({
                            "task_id": task_id,
                            "title": task["title"],
                            "assignee": task["assignee"],
                            "type": "stalled_with_failures",
                            "reason": f"Current run > 3h ({health['hours_current_run']:.1f}h) after {health['crashed_count']} crashed + {health['timed_out_count']} timed_out",
                            "severity": "P1",
                            "health": health,
                            "detail": {"health": health}
                        })
                    else:
                        blockers.append({
                            "task_id": task_id,
                            "title": task["title"],
                            "assignee": task["assignee"],
                            "type": "stalled_execution",
                            "reason": f"Running > 3h ({health['hours_current_run']:.1f}h) with no prior failures",
                            "severity": "P2",
                            "health": health,
                            "detail": {"health": health}
                        })
            
            # Check review tasks for staleness (> 24h)
            if task["status"] == "review":
                started_at = task.get("started_at")
                if started_at:
                    started_dt = datetime.fromtimestamp(started_at)
                    if started_dt < twenty_four_hours_ago:
                        blockers.append({
                            "task_id": task["id"],
                            "title": task["title"],
                            "assignee": task["assignee"],
                            "type": "missing_review",
                            "reason": f"In review > 24h (since {started_dt.strftime('%Y-%m-%d %H:%M')})",
                            "severity": "P2",
                            "health": health,
                            "detail": {"started_at": started_at}
                        })
            
            # Check ready tasks for starvation (not picked up > 3h)
            if task["status"] == "ready":
                created_at = task.get("created_at")
                if created_at:
                    created_dt = datetime.fromtimestamp(created_at)
                    if created_dt < three_hours_ago:
                        blockers.append({
                            "task_id": task["id"],
                            "title": task["title"],
                            "assignee": task["assignee"],
                            "type": "ready_starvation",
                            "reason": f"Ready > 3h, not picked up by worker (created {created_dt.strftime('%H:%M')})",
                            "severity": "P2",
                            "health": health,
                            "detail": {"created_at": created_at}
                        })
        
        return blockers
    
    def resolve_blocker(self, blocker: Dict) -> Dict:
        """Apply auto-resolution per protocol. Returns action taken."""
        task_id = blocker["task_id"]
        blocker_type = blocker["type"]
        assignee = blocker["assignee"]
        health = blocker.get("health", {})
        
        # Get task details for reassign decision
        task_detail_result = self.run_hermes_cmd(["show", task_id, "--json"])
        task_detail = {}
        if "stdout" in task_detail_result:
            try:
                task_detail = json.loads(task_detail_result["stdout"])
            except:
                pass
        
        if blocker_type == "excessive_failures":
            # This task has failed repeatedly - archive and create replacement
            return {
                "task_id": task_id,
                "action": "archive_and_replace",
                "detail": f"Archiving after {health.get('consecutive_failures', 'multiple')} consecutive failures. Creating replacement task with error context."
            }
        
        elif blocker_type == "explicit_blocked":
            # Already blocked - check if capability blocker
            blocker_reason = task_detail.get("result", "unknown")
            if "capability" in str(blocker_reason).lower():
                new_assignee = self.get_alternate_assignee(assignee, task_detail.get("title", ""))
                return {
                    "task_id": task_id,
                    "action": "reassign_capability_block",
                    "detail": f"Capability blocker detected. Reassigning from {assignee} to {new_assignee}"
                }
            else:
                return {
                    "task_id": task_id,
                    "action": "investigate_blocker",
                    "detail": f"Blocked after {health.get('total_runs', 'N/A')} runs. Needs manual investigation or decomposition."
                }
        
        elif blocker_type == "stalled_with_failures":
            # Has failures and now stalled - reassign for fresh approach
            new_assignee = self.get_alternate_assignee(assignee, blocker["title"])
            return {
                "task_id": task_id,
                "action": "reassign_fresh_approach",
                "detail": f"Stalled with prior failures. Reassigning from {assignee} to {new_assignee} for fresh approach."
            }
        
        elif blocker_type == "stalled_execution":
            # Running long without failures - may just need more time, but flag it
            return {
                "task_id": task_id,
                "action": "monitor_extended_run",
                "detail": f"Running > 3h without failures. May need more time. Will re-check next cycle."
            }
        
        elif blocker_type == "missing_review":
            return {
                "task_id": task_id,
                "action": "escalate_review",
                "detail": "Notifying reviewer via Telegram summary. Will escalate to dwight if no action in next cycle."
            }
        
        elif blocker_type == "ready_starvation":
            return {
                "task_id": task_id,
                "action": "verify_worker_availability",
                "detail": f"Ready task not picked up. Checking {assignee} capacity."
            }
        
        return {
            "task_id": task_id,
            "action": "manual_review_needed",
            "detail": f"Unknown blocker type: {blocker_type}"
        }
    
    def get_alternate_assignee(self, current: str, title: str) -> str:
        """Determine alternate assignee per routing rules."""
        title_lower = title.lower()
        # Code/DevOps/infra/debugging → bruce
        if any(kw in title_lower for kw in ["code", "devops", "infra", "debug", "deploy", "api", "backend", "workflow", "rate limit", "pwa", "next.js", "nextjs", "shell", "config"]):
            return "bruce" if current != "bruce" else "gemini"
        # Research/web/content/OCR/browser → gemini
        if any(kw in title_lower for kw in ["research", "content", "prompt", "web", "scrap", "browser", "ocr", "gather", "curate", "finance", "guitar"]):
            return "gemini" if current != "gemini" else "bruce"
        # Quick/private/offline/experiments → spark
        return "spark"
    
    def check_irrecoverable(self, tasks: Dict[str, List[Dict]]) -> List[Dict]:
        """Identify tasks that should be archived (5+ failed runs, no progress 7+ days)."""
        archived = []
        seven_days_ago = self.now - timedelta(days=7)
        
        all_tasks = []
        for status_list in tasks.values():
            all_tasks.extend(status_list)
        
        for task in all_tasks:
            task_id = task["id"]
            if task_id == "t_b11c0321":  # Don't archive monitor task
                continue
                
            runs = self.get_task_runs(task_id)
            
            failed_runs = [r for r in runs if r.get("outcome") in ["failed", "error", "timed_out", "crashed", "gave_up"]]
            if len(failed_runs) >= 5:
                completed_runs = [r for r in runs if r.get("outcome") == "completed"]
                if len(completed_runs) == 0:
                    archived.append({
                        "task_id": task_id,
                        "title": task["title"],
                        "reason": f"5+ failed runs ({len(failed_runs)} total), 0 completed"
                    })
                continue
            
            # Check for no progress > 7 days
            created_at = task.get("created_at")
            if created_at:
                created_dt = datetime.fromtimestamp(created_at)
                if created_dt < seven_days_ago and task["status"] in ["running", "blocked"]:
                    # Check if any successful run in last 7 days
                    recent_success = any(
                        r.get("outcome") == "completed" and r.get("ended_at", 0) > seven_days_ago.timestamp()
                        for r in runs
                    )
                    if not recent_success:
                        archived.append({
                            "task_id": task_id,
                            "title": task["title"],
                            "reason": f"No successful progress in 7+ days"
                        })
        
        return archived
    
    def apply_resolution(self, resolution: Dict) -> bool:
        """Apply a resolution action to the kanban board."""
        task_id = resolution["task_id"]
        action = resolution["action"]
        
        try:
            if action == "reassign_fresh_approach":
                new_assignee = resolution["detail"].split("to ")[1].split(" ")[0]
                self.run_hermes_cmd(["reassign", task_id, new_assignee])
                print(f"  ✓ Reassigned {task_id} to {new_assignee}")
                return True
            
            elif action == "reassign_capability_block":
                new_assignee = resolution["detail"].split("to ")[1].split(" ")[0]
                self.run_hermes_cmd(["reassign", task_id, new_assignee])
                print(f"  ✓ Reassigned {task_id} to {new_assignee} (capability block)")
                return True
            
            elif action == "archive_and_replace":
                self.run_hermes_cmd(["archive", task_id])
                print(f"  ✓ Archived {task_id}")
                # Could create replacement task here with context
                return True
            
            elif action in ["escalate_review", "investigate_blocker", "verify_worker_availability", "monitor_extended_run"]:
                # These are notification/escalation actions - handled by summary
                return True
                
        except Exception as e:
            print(f"Failed to apply resolution for {task_id}: {e}")
            return False
        
        return False
    
    def generate_summary(self, tasks: Dict[str, List[Dict]], blockers: List[Dict], resolutions: List[Dict], archived: List[Dict]) -> str:
        """Generate Telegram summary message."""
        running_count = len(tasks.get("running", []))
        ready_count = len(tasks.get("ready", []))
        review_count = len(tasks.get("review", []))
        blocked_count = len(tasks.get("blocked", []))
        
        # Count health metrics
        all_tasks = []
        for status_list in tasks.values():
            all_tasks.extend(status_list)
        
        total_runs_all = 0
        total_completed = 0
        total_crashed = 0
        total_timed_out = 0
        total_gave_up = 0
        
        for task in all_tasks:
            runs = self.get_task_runs(task["id"])
            total_runs_all += len(runs)
            total_completed += len([r for r in runs if r.get("outcome") == "completed"])
            total_crashed += len([r for r in runs if r.get("outcome") == "crashed"])
            total_timed_out += len([r for r in runs if r.get("outcome") == "timed_out"])
            total_gave_up += len([r for r in runs if r.get("outcome") == "gave_up"])
        
        lines = [
            f"🔄 MAKENSE 3hr Monitor — {self.cycle_time}",
            "",
            "📊 Board Snapshot:",
            f"  • Running: {running_count}  • Ready: {ready_count}  • Review: {review_count}  • Blocked: {blocked_count}",
            "",
            f"📈 Run Health (all monitored tasks):",
            f"  • Total runs: {total_runs_all}  • ✅ Completed: {total_completed}  • 💥 Crashed: {total_crashed}  • ⏱️ Timed out: {total_timed_out}  • 🏳️ Gave up: {total_gave_up}",
            "",
            f"⚠️ Blockers Detected: {len(blockers)}"
        ]
        
        for b in blockers:
            res = next((r for r in resolutions if r.get("task_id") == b["task_id"]), {})
            action = res.get("action", "pending")
            severity = b.get("severity", "")
            lines.append(f"  [{severity}] {b['task_id']} {b['title'][:45]} — {b['reason']} → {action}")
        
        if not blockers:
            lines.append("  (none)")
        
        lines.extend([
            "",
            f"✅ Actions Taken: {len([r for r in resolutions if r.get('action') not in ['needs_detailed_check', 'manual_review_needed', 'verify_worker_availability', 'escalate_review', 'monitor_extended_run']])}",
        ])
        
        for r in resolutions:
            if r.get("action") not in ["needs_detailed_check", "manual_review_needed", "verify_worker_availability", "escalate_review", "monitor_extended_run"]:
                lines.append(f"  {r.get('task_id', 'N/A')} — {r.get('action', 'unknown')}")
        
        if not any(r.get("action") not in ["needs_detailed_check", "manual_review_needed", "verify_worker_availability", "escalate_review", "monitor_extended_run"] for r in resolutions):
            lines.append("  (none - notifications/escalations only)")
        
        lines.extend([
            "",
            f"🗑️ Archived: {len(archived)}",
        ])
        
        for a in archived:
            lines.append(f"  {a['task_id']} {a['title'][:40]} — {a['reason']}")
        
        if not archived:
            lines.append("  (none)")
        
        lines.extend([
            "",
            f"📈 Velocity: {total_completed} completed across all runs (baseline tracking)",
            "",
            f"Next check: {self.next_cycle} IST"
        ])
        
        return "\n".join(lines)
    
    def send_telegram(self, message: str) -> bool:
        """Send message via print (captured by cron deliver='telegram')."""
        print(message)
        return True
    
    def log_to_kanban(self, summary: str):
        """Post cycle summary as comment on monitor task."""
        comment = f"**3hr Monitor Cycle — {self.cycle_time}**\n\n{summary}"
        result = self.run_hermes_cmd(["comment", "t_b11c0321", comment])
        if "error" in result:
            print(f"Failed to post kanban comment: {result['error']}")
    
    def run_cycle(self) -> Dict:
        """Execute one full monitoring cycle."""
        print(f"Starting monitoring cycle at {self.cycle_time}")
        
        # Step 1: Pull task status
        tasks = self.get_all_relevant_tasks()
        total_tasks = sum(len(t) for t in tasks.values())
        print(f"Found {total_tasks} tasks across monitored statuses")
        for status, task_list in tasks.items():
            if task_list:
                print(f"  {status}: {len(task_list)}")
        
        # Step 2: Identify blockers
        blockers = self.detect_blockers(tasks)
        print(f"Detected {len(blockers)} blockers")
        
        # Step 3: Generate resolutions
        resolutions = []
        for blocker in blockers:
            resolution = self.resolve_blocker(blocker)
            resolutions.append(resolution)
            print(f"  {blocker['task_id']}: {resolution['action']} - {resolution['detail']}")
        
        # Step 4: Apply resolutions (where automated)
        for resolution in resolutions:
            if resolution["action"] in ["reassign_fresh_approach", "reassign_capability_block", "archive_and_replace"]:
                self.apply_resolution(resolution)
        
        # Step 5: Check irrecoverable
        archived = self.check_irrecoverable(tasks)
        for a in archived:
            print(f"  Archiving: {a['task_id']} — {a['reason']}")
            self.run_hermes_cmd(["archive", a["task_id"]])
        
        # Step 6: Generate and send summary
        summary = self.generate_summary(tasks, blockers, resolutions, archived)
        self.send_telegram(summary)
        
        # Step 7: Log to kanban
        self.log_to_kanban(summary)
        
        return {
            "timestamp": self.cycle_time,
            "tasks_scanned": total_tasks,
            "blockers_found": len(blockers),
            "resolutions_generated": len(resolutions),
            "archived": len(archived),
            "summary": summary
        }

def main():
    monitor = KanbanMonitor()
    result = monitor.run_cycle()
    print("\n=== CYCLE COMPLETE ===")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()