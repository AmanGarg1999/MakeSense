"""LL-06 §3+§4: recap session outcomes — mastery, verification currency, and
the stuck/gap route back into LL-04 delivery.

Each completed recap:
  * updates the mastery ledger (small positive delta on recall, negative on
    lapse — a lapse is evidence the skill is NOT consolidated);
  * extends or resets verification currency: a clean recap of a verified rung
    pushes the LL-05 expiry clock forward with the same SM-2 family math
    (``expiry.next_due``), a lapse marks the verification lapsed (the next
    clearance must be a performance re-check, per LL-05's re-verify payload);
  * routes lapses into LL-04 delivery (``route`` payload: flip to active mode /
    re-teach the weakest prerequisite) — NEVER "show the same card again".
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

from ll07.stores import Stores
from ll06 import scheduler as S
from packages.assessment import expiry

PASS_QUALITY = S.PASS_QUALITY
DAY = S.DAY

# quality (SM-2 style 0-5) -> mastery delta: recall effort rewarded,
# forgetting penalised (verification-ladder evidence, LL-01 §3)
_MASTERY_BY_QUALITY = {5: 1.0, 4: 0.7, 3: 0.3, 2: -0.5, 1: -1.0, 0: -1.5}

# recap failure -> LL-04 delivery strategy (vision §2.8: change strategy)
_STUCK_ROUTES = {
    1: {"route": "reteach_prerequisite",
       "detail": "total blank — re-teach from the nearest consolidated rung, "
                 "different modality (video/build, not text)"},
    2: {"route": "flip_active_mode",
       "detail": "partial recall — flip the next segment to active mode "
                 "(predict-before-reveal / mini-task), do not re-show the card"},
}


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def record_recap(stores: Stores, sched: S.RecapScheduler, *,
                 user_id: str, skill_tag: str, quality: int,
                 track_id: Optional[str] = None,
                 mastery_deltas: Optional[dict] = None,
                 now: Optional[float] = None,
                 provenance: str = "user") -> dict[str, Any]:
    """Close out one recap item with an outcome. See module docstring.

    ``mastery_deltas`` is injectable for tests; production callers leave it
    None and we read the current mastery vector from the ledger.
    """
    now = now if now is not None else time.time()
    fam = expiry.family_for(skill_tag)

    # 1. find (or seed) the scheduler item
    item = next((i for i in sched.all_items()
                 if i.user_id == user_id and i.skill_tag == skill_tag
                 and (track_id is None or i.track_id == track_id)), None)
    if item is None:
        raise ValueError(f"no recap item for {user_id}/{skill_tag} — seed via RecapScheduler first")
    sched._now = now
    item = sched.record(item, quality=quality, provenance=provenance)
    passed = quality >= PASS_QUALITY

    # 2. mastery ledger event
    delta = _MASTERY_BY_QUALITY.get(int(quality), 0.5 if passed else -0.5)
    stores.append("mastery", {
        "user_id": user_id, "track_id": item.track_id, "skill_tag": skill_tag,
        "delta": delta,
        "cause": "recap_pass" if passed else "recap_lapse",
        "bucket": item.bucket, "quality": int(quality),
    }, provenance=provenance, ts=now)

    # 3. verification currency: extend (clean spaced recall) or lapse
    ver = stores.latest("verifications", user_id=user_id, skill_tag=skill_tag)
    currency: dict[str, Any] = {"action": "none", "reason": "no verification on record"}
    if ver is not None:
        hist = [h for h in stores.history("verifications", user_id=user_id,
                                          skill_tag=skill_tag, limit=10**5)]
        clean = expiry.count_clean_rechecks(
            [{"verified_at": _iso(h["ts"]), "verdict": h.get("outcome"),
              "recheck_of": h.get("evidence") is not None} for h in hist])
        if passed:
            # spaced recall with evidence of use counts as a clean re-check:
            # push the expiry clock out with the same family SM-2 math
            base_iso = ver.get("expires_at") and _iso(float(ver["expires_at"])) or _iso(now)
            new_due = expiry.next_due(base_iso, fam, max(clean, 1))
            new_ts = expiry.parse_dt(new_due).timestamp()
            stores.append("verifications", {
                "user_id": user_id, "track_id": item.track_id, "skill_tag": skill_tag,
                "outcome": "pass", "evidence": f"recap:quality{quality}",
                "expires_at": new_ts, "recap_extend": True,
            }, provenance="engine:recap", ts=now)
            currency = {"action": "extended", "new_due_at": new_due,
                        "clean_rechecks": max(clean, 1)}
        else:
            stores.append("verifications", {
                "user_id": user_id, "track_id": item.track_id, "skill_tag": skill_tag,
                "outcome": "provisional", "evidence": f"recap:lapse",
                "expires_at": now, "recap_lapse": True,
            }, provenance="engine:recap", ts=now)
            currency = {"action": "lapsed", "downgrade_to": "provisional",
                        "next_clearance": "performance"}

    # 4. stuck/gap routing into LL-04 (lapses only — never repeat-the-card)
    route: Optional[dict[str, Any]] = None
    if not passed:
        route = dict(_STUCK_ROUTES.get(int(quality), _STUCK_ROUTES[2]))
        route.update({"user_id": user_id, "track_id": item.track_id,
                      "skill_tag": skill_tag, "quality": int(quality),
                      "do_not": "repeat the same card"})
        if route["route"] == "reteach_prerequisite":
            deltas = mastery_deltas if mastery_deltas is not None else _current_mastery(
                stores, user_id=user_id, track_id=item.track_id)
            deltas.pop(skill_tag, None)   # the gap itself isn't its own prerequisite
            prereq = min(deltas.items(), key=lambda kv: kv[1])[0] if deltas else None
            route["prerequisite"] = prereq
            route["detail"] += f" — start from '{prereq}'" if prereq else ""

    return {"user_id": user_id, "skill_tag": skill_tag, "track_id": item.track_id,
            "quality": int(quality), "passed": passed,
            "bucket": item.bucket, "interval_days": item.interval_days,
            "next_due_at": item.due_at, "mastery_delta": delta,
            "verification_currency": currency, "delivery_route": route}


def _current_mastery(stores: Stores, *, user_id: str,
                     track_id: Optional[str]) -> dict[str, float]:
    """Fold the ledger to a current delta-total vector per skill."""
    vec: dict[str, float] = {}
    for ev in stores.history("mastery", user_id=user_id, limit=10**6):
        if track_id and ev.get("track_id") not in (track_id, None):
            continue
        tag = ev.get("skill_tag")
        if tag:
            vec[tag] = vec.get(tag, 0.0) + float(ev.get("delta") or 0.0)
    return vec
