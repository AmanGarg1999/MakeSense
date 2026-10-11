#!/usr/bin/env python3
"""LL-07 demo: one track through batches + side quests + the stores layer.

Run:  python3 scripts/demo_ll07.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ll07.stores import Stores
from ll07.batches import plan_batches, record_batch_completion
from ll07.quests import generate_quests, accept_quest, complete_quest

LADDER = [
    {"run": 1, "skill": "g:grip", "level": 0, "minutes": 40, "can_do": "hold the pick without tension",
     "adjacent": [{"title": "Pick material experiment", "kind": "micro_project", "minutes": 45,
                   "skills": ["g:grip", "g:tone"], "credit": 1.0}]},
    {"run": 2, "skill": "g:strum", "level": 0, "minutes": 50, "can_do": "strum a 4-chord loop in time"},
    {"run": 3, "skill": "g:chords", "level": 1, "minutes": 60, "can_do": "switch C-G-Em-D at 80bpm",
     "adjacent": [{"title": "Capo tooling & transposition", "kind": "tool", "minutes": 30,
                   "skills": ["g:chords"], "credit": 0.5},
                  {"title": "Fretboard geometry tangent", "kind": "tangent", "minutes": 40,
                   "skills": ["g:theory"], "credit": 1.0}]},
    {"run": 4, "skill": "g:barre", "level": 1, "minutes": 70, "can_do": "clean F barre chord"},
    {"run": 5, "skill": "g:fingerstyle", "level": 2, "minutes": 80, "can_do": "travis picking at 90bpm"},
    {"run": 6, "skill": "g:improv", "level": 2, "minutes": 90, "can_do": "solo over a 12-bar blues"},
    {"run": 7, "skill": "g:repertoire", "level": 3, "minutes": 60, "can_do": "perform 3 songs start-to-finish"},
]


def main() -> None:
    stores = Stores(":memory:")
    now = time.time()

    # knowledge DB registry (items store) — provenance per scraper
    for i, (url, tag) in enumerate((("https://ncert.example/ch1", "g:grip"),
                                    ("https://khan.example/chords", "g:chords"))):
        stores.append("items", {"item_id": f"kb{i}", "source_url": url, "license": "CC-BY-NC",
                                "skill_tag": tag, "topic": "guitar", "capture_date": "2026-10-01",
                                "quote": "verbatim span"}, provenance="scraper:demo")
    # ladder snapshot (goal-relative), then batched weekly path
    stores.append("snapshots", {"skill_tag": "guitar", "goal_type": "hobby",
                               "ladder_version": "v1", "rungs": LADDER}, provenance="engine:ladder")
    batches = plan_batches(stores, track_id="demo", skill_tag="guitar", goal_type="hobby")
    print("Week-by-week batches (hobby pacing, 120 min/wk):")
    for b in batches:
        print(f"  w{b['week']}: {b['label']}  (~{b['est_minutes']} min, {len(b['rungs'])} rungs)")

    # side quests: from ladder adjacency + one seeded interest signal
    offered = generate_quests(stores, user_id="demo-user", track_id="demo",
                              ladder=LADDER, current_run=2,
                              interests=[{"topic": "songwriting", "signal": 0.7,
                                          "last_seen_ts": now, "kind": "micro_project",
                                          "skills": ["g:theory"]}])
    print("\nDetours welcome:")
    for q in offered:
        print(f"  [{q['trigger']['source']}] {q['deliverable']['kind']}: {q['deliverable']['title']}"
              f"  (+{q['mastery']['credit']} mastery, never gates the path)")

    # finish week 1 + accept/complete a quest -> mastery ledger moves
    record_batch_completion(stores, batch_id=batches[0]["batch_id"], user_id="demo-user",
                            rungs_verified=[r["skill"] for r in batches[0]["rungs"]])
    quest = offered[0]
    accept_quest(stores, quest_id=quest["quest_id"], user_id="demo-user")
    complete_quest(stores, quest_id=quest["quest_id"], user_id="demo-user",
                   evidence_ref="artifact:pick-samples")

    print("\nMastery ledger (current per skill):")
    state = stores.current_state("mastery", key_fields=["skill_tag"], user_id="demo-user")
    for k, ev in sorted(state.items()):
        print(f"  {k}: +{ev['delta']} ({ev['cause']})")

    # verification + recap entries land for the batch-completed skill (LL-05/06 feeds)
    stores.append("verifications", {"user_id": "demo-user", "track_id": "demo",
                                    "skill_tag": "g:grip", "outcome": "pass",
                                    "evidence": "video:take1", "expires_at": now + 30 * 86400},
                  provenance="engine:verify")
    stores.append("recaps", {"user_id": "demo-user", "track_id": "demo", "skill_tag": "g:grip",
                             "due_at": now + 3 * 86400, "bucket": 2, "status": "scheduled"},
                  provenance="engine:recap")

    print("\nStore counts:", {name: n for name, n in stores.summary().items()})
    stores.close()


if __name__ == "__main__":
    main()
