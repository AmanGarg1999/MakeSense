"""Side quest engine: optional enrichments branching off the main line.

Vision §3: side quests are "where constantly-changing interests get absorbed:
interests are captured from behavior and offered as side quests rather than
derailing the goal." Two trigger sources:

  * ladder_adjacency — sub-skills adjacent to the current ladder position
    (a tool used by the next rung, a tangent topic one hop off a prereq)
  * interest         — a signal captured from behavior (dwell, searches,
    other active tracks)

Schema (one quest):
  trigger      : {source: ladder_adjacency|interest, evidence: str}
  deliverable  : {kind: tool|tangent|micro_project, title, desc, minutes}
  mastery      : {skills: [tags], credit: float}   — CONTRIBUTES to the ledger,
                 NEVER gates a batch/rung on the main path (asserted below)
  expires_at   : interest-driven quests carry an expiry so they evaporate
                 when the signal decays; adjacency quests are long-lived

Surface form: 'detours welcome' affordances on the track view.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from ll07.stores import Stores

KINDS = ("tool", "tangent", "micro_project")
TRIGGER_SOURCES = ("ladder_adjacency", "interest")

# interest signals decay; a quest seeded from one expires with the signal
INTEREST_HALF_LIFE_DAYS = 14.0
INTEREST_EXPIRY_FLOOR_DAYS = 3.0
ADJACENCY_TTL_DAYS = 60.0


def _now() -> float:
    return time.time()


def generate_quests(
    stores: Stores,
    *,
    user_id: str,
    track_id: str,
    ladder: list[dict[str, Any]],
    current_run: int,
    interests: Optional[list[dict[str, Any]]] = None,
    max_adjacency: int = 2,
    provenance: str = "engine:quest",
) -> list[dict[str, Any]]:
    """Generate + record offered quests for a track position.

    ladder: LL-02 rungs, each {run, skill, level, tags?, adjacent?}.
    interests: [{topic, signal, last_seen_ts}] inferred (never asked) signals.
    Returns the quest dicts (appended to the quests store as offered events).
    """
    by_run = {int(r["run"]): r for r in ladder}
    quests: list[dict[str, Any]] = []

    # 1. ladder adjacency: one hop ahead/behind/sideways from current position
    for target_run, relation in ((current_run + 1, "next_rung"), (current_run, "current_rung")):
        rung = by_run.get(target_run)
        if not rung:
            continue
        for adj in (rung.get("adjacent") or [])[:max_adjacency]:
            quests.append(_quest(
                user_id, track_id,
                trigger={"source": "ladder_adjacency",
                         "evidence": f"{relation} ({rung['skill']}) lists {adj['title']}"},
                deliverable={"kind": adj.get("kind", "tool"),
                             "title": adj["title"], "desc": adj.get("desc", ""),
                             "minutes": adj.get("minutes", 45)},
                mastery={"skills": adj.get("skills", [rung["skill"]]),
                         "credit": adj.get("credit", 1.0)},
                expires_at=_now() + ADJACENCY_TTL_DAYS * 86400,
            ))

    # 2. seeded interest signals (captured from behavior elsewhere)
    for sig in (interests or []):
        strength = float(sig.get("signal", 0.5))
        if strength <= 0.0:
            continue
        age_days = max(0.0, (_now() - float(sig.get("last_seen_ts", _now()))) / 86400.0)
        ttl_days = max(INTEREST_EXPIRY_FLOOR_DAYS,
                       INTEREST_HALF_LIFE_DAYS * (2 ** -age_days) * max(strength, 0.1) * 2)
        quests.append(_quest(
            user_id, track_id,
            trigger={"source": "interest",
                     "evidence": f"behavioral signal on '{sig['topic']}' (strength {strength:.2f}, seen {age_days:.0f}d ago)"},
            deliverable={"kind": sig.get("kind", "tangent"),
                         "title": sig.get("title", f"Detour: {sig['topic']}"),
                         "desc": sig.get("desc", f"A short detour into {sig['topic']} — connect it back to {track_id}."),
                         "minutes": sig.get("minutes", 30)},
            mastery={"skills": sig.get("skills", []), "credit": round(strength, 2)},
            expires_at=_now() + ttl_days * 86400,
        ))

    for q in quests:
        stores.append("quests", {
            "quest_id": q["quest_id"], "kind": "side", "status": "offered",
            "user_id": user_id, "track_id": track_id,
            **q,
        }, provenance=provenance, record_id=q["quest_id"])
    return quests


def _quest(user_id: str, track_id: str, *, trigger: dict, deliverable: dict,
           mastery: dict, expires_at: float) -> dict[str, Any]:
    if trigger["source"] not in TRIGGER_SOURCES:
        raise ValueError(f"bad trigger source {trigger['source']}")
    if deliverable["kind"] not in KINDS:
        raise ValueError(f"bad deliverable kind {deliverable['kind']}")
    qid = f"quest:{track_id}:{deliverable['kind']}:{deliverable['title']}"
    return {
        "quest_id": qid,
        "trigger": trigger,
        "deliverable": deliverable,
        "mastery": mastery,
        "expires_at": expires_at,
        "surface": "detours_welcome",
    }


def quest_state(stores: Stores, quest_id: str) -> Optional[dict[str, Any]]:
    return stores.latest("quests", quest_id=quest_id, kind="side")


def accept_quest(stores: Stores, *, quest_id: str, user_id: str,
                 provenance: str = "user") -> dict[str, Any]:
    q = quest_state(stores, quest_id)
    if q is None or q["status"] != "offered":
        raise ValueError(f"quest {quest_id} not open for acceptance (status={q and q['status']})")
    if q["expires_at"] < _now():
        raise ValueError(f"quest {quest_id} has expired")
    return stores.append("quests", {
        "quest_id": quest_id, "kind": "side", "status": "accepted",
        "user_id": user_id, "track_id": q["track_id"],
        "trigger": q["trigger"], "deliverable": q["deliverable"],
        "mastery": q["mastery"], "expires_at": q["expires_at"],
    }, provenance=provenance, record_id=f"{quest_id}:accepted:{user_id}")


def complete_quest(stores: Stores, *, quest_id: str, user_id: str,
                   evidence_ref: Optional[str] = None,
                   provenance: str = "user") -> dict[str, Any]:
    """Finish a side quest: appends a state event + mastery credit events.

    Side quests CONTRIBUTE to mastery — one ledger event per mapped skill.
    They never touch batch state, so they cannot gate the main path.
    """
    q = quest_state(stores, quest_id)
    if q is None or q["status"] not in ("offered", "accepted"):
        raise ValueError(f"quest {quest_id} not completable (status={q and q['status']})")
    ev = stores.append("quests", {
        "quest_id": quest_id, "kind": "side", "status": "completed",
        "user_id": user_id, "track_id": q["track_id"],
        "evidence_ref": evidence_ref, "delivered": q["deliverable"],
    }, provenance=provenance, record_id=f"{quest_id}:completed:{user_id}")
    credit = float(q["mastery"].get("credit", 1.0))
    for skill in q["mastery"].get("skills", []):
        stores.append("mastery", {
            "user_id": user_id, "track_id": q["track_id"], "skill_tag": skill,
            "delta": credit, "cause": "side_quest_completed", "quest_id": quest_id,
        }, provenance=provenance)
    return ev


def expire_stale_quests(stores: Stores, *, now: Optional[float] = None,
                        provenance: str = "engine:quest") -> list[str]:
    """Mark still-open quests whose interest signal has expired as 'expired'
    (append-only: a new state event, never an update). Returns quest ids."""
    now = now if now is not None else _now()
    stale: list[str] = []
    events_by_quest: dict[str, list[dict[str, Any]]] = {}
    for q in stores.history("quests", kind="side", limit=10**7):
        events_by_quest.setdefault(q["quest_id"], []).append(q)
    for qid, events in events_by_quest.items():
        latest = max(events, key=lambda e: e["seq"])
        if latest["status"] in ("offered", "accepted") and latest["expires_at"] < now:
            stores.append("quests", {
                "quest_id": qid, "kind": "side", "status": "expired",
                "user_id": latest.get("user_id"), "track_id": latest["track_id"],
                "trigger": latest["trigger"], "deliverable": latest["deliverable"],
                "mastery": latest["mastery"], "expires_at": latest["expires_at"],
            }, provenance=provenance, record_id=f"{qid}:expired")
            stale.append(qid)
    return stale
