"""LL-06 §1: spaced recap scheduler (Leitner buckets + tuned SM-2 growth).

Vision §3: recap is interval-driven off the mastery ledger, Leitner/SM-2 style
buckets, tuned per skill decay rate from verification results. LL-05's handoff
note: ``expiry`` math + the registry's due-events view are the feed.

Bucket model
------------
Five Leitner boxes. Base spacing = ``BASE_INTERVAL_DAYS`` (days). A *success*
moves the item up one box and multiplies its interval by the box's growth
factor (never below the next box's base floor); a *lapse* (quality < 3) resets
it to box 1 with the base interval — SM-2 lapse semantics, history never
deleted (append-only, LL-01 §4).

Per-skill tuning: the growth factor is ``GROWTH_BASE + GROWTH_SPAN *
success_rate`` clamped to [1.5, 3.5], where ``success_rate`` is the observed
recall success (recap outcomes) for the item's decay family (LL-05
``expiry.family_for``), smoothed with a Beta(2,2) prior so the first couple of
outcomes don't swing it. Families with generous first re-checks in the LL-01
table (finance, crafts) get their initial placement pushed one box up —
already-demonstrated skill shouldn't start in the "tomorrow" box.

Seeding: every (user, track, skill) pair with mastery-ledger events or a
verification event gets a scheduled item. If an LL-05
``VerificationRegistry`` is wired in, its ``due_events`` feed overrides the
due time with the expiry clock (verification currency IS the recap clock for
verified rungs).

Storage: all state lives in the LL-07 stores ``recaps`` stream as append-only
events (``scheduled`` / ``due`` / ``completed`` / ``lapsed``). The in-memory
dict is a fold cache — on a warm start the schedule is rebuilt from events, so
the client can be a WatermelonDB mirror of the same stream.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ll07.stores import Stores, StoreError
from packages.assessment import expiry

DAY = 86400.0

# ---------------------------------------------------------------------------
# Leitner config
# ---------------------------------------------------------------------------

N_BUCKETS = 5
BASE_INTERVAL_DAYS = [1, 3, 7, 21, 60]
FAMILY_FIRST_BOX = {          # seeded box for a first-time recap schedule
    "finance": 3, "crafts": 3,          # long-horizon families (LL-01 §9)
    "language": 1, "math": 1,           # tight micro-check cadence
    "coding": 2, "guitar": 2, "photo_video": 2, "default": 2,
}
PASS_QUALITY = 3              # SM-2: quality >= 3 is a success
GROWTH_BASE, GROWTH_MIN, GROWTH_MAX = 2.0, 1.5, 3.5
GROWTH_SPAN = GROWTH_MAX - GROWTH_BASE
_PRIOR_A, _PRIOR_B = 2.0, 2.0   # Beta prior on family success rate


def _epoch(value: Any) -> Optional[float]:
    """Coerce an epoch float or ISO string to epoch seconds."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        try:
            return expiry.parse_dt(str(value)).timestamp()
        except Exception:
            return None


def clamp_growth(x: float) -> float:
    return max(GROWTH_MIN, min(GROWTH_MAX, x))


def family_growth(successes: int, failures: int) -> float:
    """Growth factor tuned by observed recall success for a decay family."""
    rate = (successes + _PRIOR_A) / (successes + failures + _PRIOR_A + _PRIOR_B)
    return clamp_growth(GROWTH_BASE + GROWTH_SPAN * rate)


def interval_for_success(bucket: int, growth: float) -> tuple[int, float]:
    """Advance one box on success. Returns (new_bucket, days_until_due).

    A top-box item stays in the box and grows by the tuned factor (capped by
    the family ceiling); lower boxes grow by the factor but never below the
    next box's base spacing floor.
    """
    new_bucket = min(bucket + 1, N_BUCKETS)
    base_days = BASE_INTERVAL_DAYS[bucket - 1]
    days = base_days * growth
    if new_bucket < N_BUCKETS:
        days = max(days, BASE_INTERVAL_DAYS[new_bucket - 1])
    return new_bucket, days


def interval_for_lapse() -> tuple[int, float]:
    """Lapse → reset to box 1 at base spacing (SM-2)."""
    return 1, float(BASE_INTERVAL_DAYS[0])


# ---------------------------------------------------------------------------
# schedule item
# ---------------------------------------------------------------------------

@dataclass
class RecapItem:
    item_id: str
    user_id: str
    track_id: str
    skill_tag: str
    bucket: int
    interval_days: float
    due_at: float
    status: str = "scheduled"          # scheduled | completed | lapsed
    successes: int = 0
    failures: int = 0
    seeded_from: Optional[str] = None  # 'mastery' | 'verification' | 'expiry'
    events: list = field(default_factory=list, repr=False)

    def as_row(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id, "track_id": self.track_id,
            "skill_tag": self.skill_tag, "bucket": self.bucket,
            "due_at": self.due_at, "status": self.status,
            "interval_days": self.interval_days,
            "successes": self.successes, "failures": self.failures,
            "seeded_from": self.seeded_from,
        }


class RecapScheduler:
    """Fold store streams into a per-user/per-track recap schedule."""

    def __init__(self, stores: Stores, *, registry: Any = None,
                 now: Optional[float] = None):
        self._stores = stores
        self._registry = registry
        self._now = now if now is not None else time.time()
        self._items: dict[tuple, RecapItem] = {}
        self._growth: dict[str, float] = {}
        self._build()

    def _bump(self, fam: str, kind: str) -> None:
        """Track one recap outcome toward the family's tuned growth factor."""
        succ = self._growth.setdefault(fam + ":succ", 0.0)
        fail = self._growth.setdefault(fam + ":fail", 0.0)
        if kind == "successes":
            self._growth[fam + ":succ"] = succ + 1
        else:
            self._growth[fam + ":fail"] = fail + 1
        self._growth[fam] = family_growth(int(self._growth[fam + ":succ"]),
                                          int(self._growth[fam + ":fail"]))

    # -- public ---------------------------------------------------------

    def due(self, user_id: str, *, track_id: Optional[str] = None,
            now: Optional[float] = None) -> list[RecapItem]:
        """Items whose due time has passed, oldest first — the home/coach feed."""
        now = now if now is not None else self._now
        out = [i for i in self._items.values()
               if i.user_id == user_id and i.status == "scheduled"
               and i.due_at <= now
               and (track_id is None or i.track_id == track_id)]
        return sorted(out, key=lambda i: (i.due_at, i.skill_tag))

    def upcoming(self, user_id: str, *, now: Optional[float] = None) -> list[RecapItem]:
        now = now if now is not None else self._now
        out = [i for i in self._items.values()
               if i.user_id == user_id and i.status == "scheduled" and i.due_at > now]
        return sorted(out, key=lambda i: i.due_at)

    def all_items(self) -> list[RecapItem]:
        return list(self._items.values())

    def growth_for(self, skill_tag: str) -> float:
        fam = expiry.family_for(skill_tag)
        return self._growth.get(fam, self._growth.get("default",
                             family_growth(0, 0)))

    def record(self, item: RecapItem, *, quality: int,
               provenance: str = "user") -> RecapItem:
        """Apply one recap outcome: tune family growth, advance or reset the
        bucket, append the event. Returns the updated item."""
        fam = expiry.family_for(item.skill_tag)
        if quality >= PASS_QUALITY:
            item.successes += 1
            self._bump(fam, "successes")
            item.bucket, item.interval_days = interval_for_success(
                item.bucket, self.growth_for(item.skill_tag))
            status = "completed"
        else:
            item.failures += 1
            self._bump(fam, "failures")
            item.bucket, item.interval_days = interval_for_lapse()
            status = "lapsed"
        item.due_at = self._now + item.interval_days * DAY
        item.status = "scheduled"
        self._stores.append("recaps", {
            **item.as_row(),
            "id": f"recap:{item.track_id}:{item.skill_tag}:{item.user_id}:evt{len(item.events)}",
            "outcome": status, "quality": int(quality),
            "growth_factor": round(self.growth_for(item.skill_tag), 3),
        }, provenance=provenance, ts=self._now)
        item.events.append(status)
        return item

    # -- build ----------------------------------------------------------

    def _build(self) -> None:
        # 1. family growth, tuned by every recorded recap outcome so far
        succ: dict[str, int] = {}
        fail: dict[str, int] = {}
        for ev in self._stores.history("recaps", limit=10**7):
            if ev.get("outcome") not in ("completed", "lapsed"):
                continue
            fam = expiry.family_for(ev.get("skill_tag") or "")
            if ev["outcome"] == "completed":
                succ[fam] = succ.get(fam, 0) + 1
            else:
                fail[fam] = fail.get(fam, 0) + 1
        for fam in set(succ) | set(fail):
            self._growth[fam] = family_growth(succ.get(fam, 0), fail.get(fam, 0))
            self._growth[fam + ":succ"] = float(succ.get(fam, 0))
            self._growth[fam + ":fail"] = float(fail.get(fam, 0))
        if not self._growth:
            self._growth["default"] = family_growth(0, 0)

        # 2. seed from mastery ledger + verification events. NOTE: ``seq`` is
        # per-store-table, so it can never be compared across streams — the
        # verified-rung rule ("verification currency IS the recap clock") is
        # source-based: any verification event on the key drives the seed.
        keyed: dict[tuple, dict[str, Any]] = {}

        def _key_slot(k):
            return keyed.setdefault(k, {"verified": False, "ver_ts": None,
                                        "expires_at": None})

        for ev in self._stores.history("mastery", limit=10**7):
            _key_slot((ev["user_id"], ev["track_id"], ev["skill_tag"]))
        for ev in self._stores.history("verifications", limit=10**7):
            slot = _key_slot((ev["user_id"], ev["track_id"], ev["skill_tag"]))
            slot["verified"] = True
            # the LATEST verification event carries the live expiry clock
            # (LL-05 re-verify/recap-extend append a newer row); mastery
            # recency says nothing about verification currency
            if slot["ver_ts"] is None or ev["ts"] >= slot["ver_ts"]:
                slot["ver_ts"] = ev["ts"]
                slot["expires_at"] = ev.get("expires_at")

        # 3. fold the recaps stream (append-only state machine)
        for ev in self._stores.history("recaps", limit=10**7):
            if ev.get("outcome") not in ("completed", "lapsed"):
                continue  # seed marker rows carry no outcome
            k = (ev["user_id"], ev["track_id"], ev["skill_tag"])
            item = self._items.get(k)
            if item is None:
                item = RecapItem(item_id=f"recap:{k[2]}:{k[0]}", user_id=k[0],
                                 track_id=k[1], skill_tag=k[2],
                                 bucket=ev.get("bucket", 1),
                                 interval_days=ev.get("interval_days", BASE_INTERVAL_DAYS[0]),
                                 due_at=ev.get("due_at", self._now),
                                 successes=0, failures=0)
                self._items[k] = item
            item.bucket = ev.get("bucket", item.bucket)
            item.interval_days = ev.get("interval_days", item.interval_days)
            item.due_at = ev["due_at"]
            item.successes = ev.get("successes", item.successes + (ev["outcome"] == "completed"))
            item.failures = ev.get("failures", item.failures + (ev["outcome"] == "lapsed"))
            item.status = "scheduled"
            item.events.append(ev["outcome"])

        # 4. seed what has no recap history yet
        for k, src in keyed.items():
            if k in self._items:
                continue
            user_id, track_id, skill_tag = k
            fam = expiry.family_for(skill_tag)
            bucket = FAMILY_FIRST_BOX.get(fam, FAMILY_FIRST_BOX["default"])
            due_at = self._now + BASE_INTERVAL_DAYS[bucket - 1] * DAY
            seeded_from = "verification" if src["verified"] else "mastery"
            if src["verified"] and src.get("expires_at"):
                # verification currency IS the recap clock for verified rungs
                exp = _epoch(src["expires_at"])
                if exp is not None:
                    due_at = min(due_at, exp)
            item = RecapItem(item_id=f"recap:{skill_tag}:{user_id}",
                             user_id=user_id, track_id=track_id, skill_tag=skill_tag,
                             bucket=bucket,
                             interval_days=float(BASE_INTERVAL_DAYS[bucket - 1]),
                             due_at=due_at, seeded_from=seeded_from)
            self._items[k] = item
            try:
                self._stores.append("recaps", {
                    **item.as_row(),
                    "id": f"recap:{track_id}:{skill_tag}:{user_id}:seed",
                }, provenance="engine:recap", ts=self._now)
            except StoreError:
                pass  # seeded on an earlier warm start; stream already has it

        # 5. LL-05 registry due-events feed overrides due time for verified rungs
        if self._registry is not None:
            import datetime as _dt
            as_of = _dt.datetime.fromtimestamp(self._now, _dt.timezone.utc).isoformat()
            for ev in self._registry.due_events(as_of):
                k = (str(ev.user_id), ev.track_id or "", ev.skill_tag)
                item = self._items.get(k)
                if item is not None and ev.expires_at:
                    item.due_at = min(item.due_at, expiry.parse_dt(ev.expires_at).timestamp())
                    item.seeded_from = "expiry"
