"""Skill batches: chunk ladder rungs into coherent weekly-ish batches.

Vision §3: "topics chunked into coherent weekly-ish batches (existing pack
format)". A ladder rung is a named sub-skill with an effort estimate; the
batcher groups *consecutive prerequisite-respecting rungs* into batches sized
by the track's weekly pacing, and binds each batch to a content pack
sequence (pack refs from the knowledge DB item registry).

Batch completion is an event, not a mutation: it appends to the `quests`
store (batch state) and feeds a mastery delta into the `mastery` ledger, per
the loop's append-only rule.

Goal-relative pacing (per-track):
  hobby      -> ~120 min/week   (small batches, more variety)
  job-ready  -> ~300 min/week   (project-anchored batches)
  expert     -> ~480 min/week   (deep consolidation blocks)
"""

from __future__ import annotations

from typing import Any, Optional

from ll07.stores import Stores

WEEK_MINUTES = {"hobby": 120, "job_ready": 300, "expert": 480}
RUNGS_PER_BATCH_CAP = 5  # coherence cap: keep a batch small enough to finish in a week

# A batch is "coherent" when its rungs sit within one ladder level. If a level
# is left with a thin tail (< 60% of the weekly budget), the tail merges
# forward into the next level's first batch instead of a stub week.
COHERENCE_MERGE_RATIO = 0.6


def plan_batches(
    stores: Stores,
    *,
    track_id: str,
    skill_tag: str,
    goal_type: str,
    ladder: Optional[list[dict[str, Any]]] = None,
    week_minutes: Optional[int] = None,
    provenance: str = "engine:batcher",
) -> list[dict[str, Any]]:
    """Chunk ladder rungs into batches for a track and record them.

    `ladder` is the LL-02 skill ladder: list of rungs
    {run: int, skill: str, level: int, minutes: int, can_do: str}.
    When omitted, the latest snapshot in the stores is used.
    Returns the batch plans (also appended to the quests store).
    """
    if ladder is None:
        snap = stores.latest("snapshots", skill_tag=skill_tag, goal_type=goal_type)
        if snap is None:
            raise ValueError(f"no ladder snapshot for {skill_tag}/{goal_type} and none passed")
        ladder = snap["rungs"]

    budget = week_minutes or WEEK_MINUTES.get(goal_type, WEEK_MINUTES["job_ready"])

    # group by level, keeping rung order (prerequisites first)
    by_level: dict[int, list[dict]] = {}
    for rung in sorted(ladder, key=lambda r: r["run"]):
        by_level.setdefault(int(rung["level"]), []).append(rung)

    batches: list[dict[str, Any]] = []
    week_no = 1
    carry: list[dict] = []  # thin tail merged forward from the previous level
    for level in sorted(by_level):
        pool = carry + by_level[level]
        carry = []
        while pool:
            batch: list[dict] = []
            total = 0
            while pool and total < budget and len(batch) < RUNGS_PER_BATCH_CAP:
                r = pool.pop(0)
                batch.append(r)
                total += int(r.get("minutes", 30))
            if pool and sum(int(r.get("minutes", 30)) for r in pool) < budget * COHERENCE_MERGE_RATIO:
                carry = pool  # thin tail: merge into the next level's first week
                pool = []
            batches.append(_make_batch(track_id, skill_tag, goal_type, batch, week_no, total))
            week_no += 1
    while carry:  # last level's tail still needs a week of its own
        pool, carry = carry, []
        batch: list[dict] = []
        total = 0
        while pool and total < budget and len(batch) < RUNGS_PER_BATCH_CAP:
            r = pool.pop(0)
            batch.append(r)
            total += int(r.get("minutes", 30))
        if pool:
            carry = pool
        batches.append(_make_batch(track_id, skill_tag, goal_type, batch, week_no, total))
        week_no += 1

    # append-only: batch plan events into quest/batch state
    for b in batches:
        stores.append("quests", {
            "quest_id": b["batch_id"], "kind": "batch", "status": "planned",
            "track_id": track_id, "user_id": None,
            "batch_id": b["batch_id"], "label": b["label"],
            "rungs": [r["skill"] for r in b["rungs"]], "week": b["week"],
        }, provenance=provenance, record_id=b["batch_id"])
    return batches


def _make_batch(track_id: str, skill_tag: str, goal_type: str,
                rungs: list[dict], week: int, minutes: int) -> dict[str, Any]:
    return {
        "batch_id": f"batch:{track_id}:{skill_tag}:{goal_type}:w{week}",
        "track_id": track_id,
        "skill_tag": skill_tag,
        "goal_type": goal_type,
        "week": week,
        "label": rungs[0]["skill"] if len(rungs) == 1 else f"{rungs[0]['skill']} → {rungs[-1]['skill']}",
        "rungs": rungs,
        "est_minutes": minutes,
        "pack_refs": sorted({r["pack"] for r in rungs if r.get("pack")}),
        "completed": False,
    }


def record_batch_completion(
    stores: Stores,
    *,
    batch_id: str,
    user_id: str,
    rungs_verified: list[str],
    provenance: str = "engine:batcher",
    mastery_delta: float = 2.0,
) -> dict[str, Any]:
    """Batch done -> two appends: a batch-state event + a mastery-ledger event
    per completed rung. Batch completion events feed mastery (vision §3)."""
    plan = stores.latest("quests", batch_id=batch_id)
    if plan is None:
        raise ValueError(f"unknown batch {batch_id}")
    ev = stores.append("quests", {
        "quest_id": f"{batch_id}:done:{user_id}", "kind": "batch", "status": "completed",
        "track_id": plan["track_id"], "user_id": user_id, "batch_id": batch_id,
        "rungs": rungs_verified,
    }, provenance=provenance)
    for rung in rungs_verified:
        stores.append("mastery", {
            "user_id": user_id, "track_id": plan["track_id"], "skill_tag": rung,
            "delta": mastery_delta, "cause": "batch_completed", "batch_id": batch_id,
        }, provenance=provenance)
    return ev
