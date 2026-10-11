"""Mastery-decay / expiry engine (LL-05 §5).

Per LL-01 §4 + §9: intervals are SM-2-style — a first re-check after `first_days`,
then a steady-state interval that expands by GROWTH (~×2.5, within the literature
band ×2.3–2.7) per clean spaced re-verification, clamped to the family ceiling and
floored at the family minimum. Lapses never delete history: the rung downgrades to
provisional and a re-verify task is re-queued into the loop.

Statuses of a *verification* (derived, never stored by UPDATE — the registry is
append-only; each event carries its own expires_at):

    current   now < due
    stale     due <= now < due + stale_grace  (re-check overdue; do next session)
    expired   now >= due + stale_grace        (rung drops to provisional,
                                               re-verify task queued)

Family table transcribed from docs/research/skill-verification.md §9.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

GROWTH = 2.5            # ×2.3–2.7 per clean spaced re-verification (LL-01 §9)
STALE_GRACE_FRACTION = 0.25   # stale band = 25% of the interval, min 7 days
MIN_STALE_GRACE_DAYS = 7

# family -> (first re-check days, steady interval days, ceiling days)
# ceiling = upper end of the family steady-state band (concepts for coding = 180).
FAMILY_INTERVALS: dict[str, tuple[int, int, int]] = {
    "coding":        (30, 60, 180),    # 45-75d stack fluency, 6mo concepts
    "guitar":        (30, 75, 180),    # repertoire 60-90d, transfer probe 180d
    "finance":       (60, 270, 365),   # 6-12mo + event-driven
    "language":      (21, 45, 180),    # micro-checks 21d, spot 30-60d, full 4-6mo
    "photo_video":   (45, 105, 240),   # 90-120d
    "crafts":        (60, 270, 365),   # 6-12mo; immediate on tool change
    "math":          (21, 38, 90),     # 30-45d interleaved
    "default":       (30, 60, 180),
}

STATUSES = {"current", "stale", "expired"}

# Map skill_tag fragments onto decay families so callers can pass a raw tag.
_FAMILY_ALIASES = {
    "python": "coding", "javascript": "coding", "web": "coding", "sql": "coding",
    "guitar": "guitar", "music": "guitar",
    "finance": "finance", "invest": "finance", "budget": "finance",
    "language": "language", "spanish": "language", "english": "language", "french": "language",
    "photo": "photo_video", "video": "photo_video", "film": "photo_video",
    "craft": "crafts", "wood": "crafts", "sewing": "crafts",
    "math": "math", "algebra": "math", "calculus": "math",
}


def family_for(skill_tag: str, family: Optional[str] = None) -> str:
    if family and family in FAMILY_INTERVALS:
        return family
    tag = skill_tag.lower()
    for frag, fam in _FAMILY_ALIASES.items():
        if frag in tag:
            return fam
    return "default"


def next_interval_days(family: str, clean_rechecks: int) -> int:
    """Interval (days) until the NEXT re-verification, given how many clean spaced
    re-checks have already followed the original verification (0 = first pass)."""
    first, steady, ceiling = FAMILY_INTERVALS.get(family, FAMILY_INTERVALS["default"])
    if clean_rechecks <= 0:
        return first
    return int(min(ceiling, steady * (GROWTH ** min(clean_rechecks - 1, 6))))


def next_due(verified_at: str, family: str, clean_rechecks: int) -> str:
    return (parse_dt(verified_at) + timedelta(days=next_interval_days(family, clean_rechecks))).isoformat()


def stale_grace_days(family: str, clean_rechecks: int) -> int:
    return max(MIN_STALE_GRACE_DAYS,
               int(next_interval_days(family, clean_rechecks) * STALE_GRACE_FRACTION))


def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class ExpiryStatus:
    status: str                    # current | stale | expired
    due_at: str
    hard_expired_at: str
    days_remaining: int            # negative once past due
    recheck_task: Optional[dict] = None   # populated when 'expired'


def compute_status(*, user_id: Any, skill_tag: str, level_index: int,
                   latest_verdict: str, verified_at: str, expires_at: str,
                   clean_rechecks: int, track_id: Optional[str] = None,
                   family: Optional[str] = None,
                   now: Optional[str] = None) -> ExpiryStatus:
    """Pure clock math over the registry's latest event for a rung."""
    fam = family_for(skill_tag, family)
    now_dt = parse_dt(now) if now else datetime.now(timezone.utc)
    due_dt = parse_dt(expires_at)
    grace = stale_grace_days(fam, clean_rechecks)
    hard_dt = due_dt + timedelta(days=grace)

    if now_dt < due_dt:
        status = "current"
    elif now_dt < hard_dt:
        status = "stale"
    else:
        status = "expired"

    task = build_recheck_task(user_id=user_id, skill_tag=skill_tag,
                              level_index=level_index, track_id=track_id,
                              family=fam, clean_rechecks=clean_rechecks) \
        if status == "expired" else None
    return ExpiryStatus(
        status=status, due_at=due_dt.isoformat(), hard_expired_at=hard_dt.isoformat(),
        days_remaining=(due_dt - now_dt).days, recheck_task=task,
    )


def build_recheck_task(*, user_id: Any, skill_tag: str, level_index: int,
                       track_id: Optional[str], family: str,
                       clean_rechecks: int) -> dict:
    """Re-verify task payload for the learning loop (LL-05 §5 → dispatcher / LL-06).

    A lapse downgrades to provisional — never deletes (append-only history, LL-01 §4).
    The re-check must be a PERFORMANCE evidence submission, and per LL-01 §4 the
    environment should rotate (context-dependency finding)."""
    return {
        "type": "reverify",
        "user_id": str(user_id),
        "skill_tag": skill_tag,
        "level_index": level_index,
        "track_id": track_id,
        "reason": "verification_expired",
        "required_evidence": "performance",     # explain-only cannot clear it
        "suggested_action": (
            "Schedule a performance re-check in a rotated context "
            "(different project/venue/problem set) — do not repeat the original artifact."
        ),
        "downgrade_to": "provisional",
        "next_interval_days": next_interval_days(family, clean_rechecks),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def count_clean_rechecks(history: list[dict]) -> int:
    """How many spaced re-verifications (recheck_of set) passed cleanly so far —
    drives interval expansion. A rejected/provisional re-check resets the count
    (SM-2 lapse semantics)."""
    count = 0
    for ev in sorted(history, key=lambda e: e.get("verified_at", "")):
        verdict = ev.get("verdict")
        if verdict in ("verified", "reinforced") and ev.get("recheck_of"):
            count += 1
        elif verdict in ("rejected", "provisional"):
            count = 0
    return count
