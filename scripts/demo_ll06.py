#!/usr/bin/env python3
"""LL-06 acceptance demo: seeded user -> recap schedule + rewind digest.

Seeds one demo user with knowledge-DB items, mastery events, a verification
with an expiry clock, and a lapse history; then:

  1. builds the Leitner/SM-2 schedule and shows due vs upcoming items
     (the home/coach surfacing shape);
  2. clears one due recap (quality 4) and shows the mastery + verification
     currency update;
  3. generates the "take me back through guitar" rewind digest with
     citations into the knowledge DB.

Writes docs/acceptance/LL-06/{recap_digest.json,schedule.json}.

Run:  python3 scripts/demo_ll06.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ll07.stores import Stores
from ll06 import scheduler as S
from ll06.digest import rewind
from ll06.outcomes import record_recap

DAY = 86400.0
NOW = time.time()
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "docs", "acceptance", "LL-06")

LADDER = [
    {"run": 2, "skill": "g:strum", "can_do": "strum a 4-chord loop in time"},
    {"run": 3, "skill": "g:chords", "can_do": "switch C-G-Em-D at 80bpm"},
    {"run": 4, "skill": "g:barre", "can_do": "clean F barre chord"},
]


def seed(stores: Stores) -> None:
    # knowledge DB items the digest can cite
    for i, (url, tag, quote) in enumerate((
        ("https://ncert.example/music-ch1", "g:strum",
         "downstrokes land on beats 1 and 3; keep the wrist loose"),
        ("https://justinguitar.example/chords", "g:chords",
         "anchor finger: keep one finger down during the C->G change"),
        ("https://ultimateguitar.example/barre", "g:barre",
         "thumb behind the neck, index edge not flat"),
    )):
        stores.append("items", {"item_id": f"kb-g{i}", "source_url": url,
                                "license": "CC-BY-NC", "skill_tag": tag,
                                "topic": "guitar", "capture_date": "2026-09-14",
                                "quote": quote},
                      provenance="scraper:demo", ts=NOW - 40 * DAY)
    # mastery history (what the user actually did)
    stores.append("mastery", {"user_id": "demo", "track_id": "guitar-hobby",
                              "skill_tag": "g:strum", "delta": 3.0,
                              "cause": "batch_completed"},
                  provenance="engine:batcher", ts=NOW - 30 * DAY)
    stores.append("mastery", {"user_id": "demo", "track_id": "guitar-hobby",
                              "skill_tag": "g:chords", "delta": 2.0,
                              "cause": "batch_completed"},
                  provenance="engine:batcher", ts=NOW - 12 * DAY)
    stores.append("mastery", {"user_id": "demo", "track_id": "guitar-hobby",
                              "skill_tag": "g:barre", "delta": 1.0,
                              "cause": "quest_completed"},
                  provenance="engine:quest", ts=NOW - 20 * DAY)
    # a passed verification whose expiry clock drives the recap schedule
    stores.append("verifications", {"user_id": "demo", "track_id": "guitar-hobby",
                                    "skill_tag": "g:chords", "outcome": "pass",
                                    "evidence": "video:practice-log-w3",
                                    "expires_at": NOW + 1 * DAY},
                  provenance="engine:verify", ts=NOW - 25 * DAY)
    # a past lapse: the digest must re-question it, not repeat the card
    stores.append("recaps", {"user_id": "demo", "track_id": "guitar-hobby",
                             "skill_tag": "g:barre", "due_at": NOW - 5 * DAY,
                             "bucket": 1, "status": "scheduled",
                             "outcome": "lapsed", "quality": 2},
                  provenance="user", ts=NOW - 5 * DAY)


def iso(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ts)) + "Z"


def main() -> None:
    stores = Stores(":memory:")
    seed(stores)
    sched = S.RecapScheduler(stores, now=NOW)

    due = sched.due("demo", now=NOW)
    upcoming = sched.upcoming("demo", now=NOW)
    print("== due now (home/coach feed) ==")
    for i in due:
        print(f"  {i.skill_tag:12s} box {i.bucket}  seeded_from={i.seeded_from}")
    print("== upcoming ==")
    for i in upcoming:
        print(f"  {i.skill_tag:12s} box {i.bucket}  due {iso(i.due_at)}")

    # clear one due recap: outcome updates mastery + verification currency
    if due:
        target = due[0]
        res = record_recap(stores, sched, user_id="demo",
                           skill_tag=target.skill_tag, quality=4,
                           track_id=target.track_id, now=NOW)
        print(f"\n== recap cleared: {target.skill_tag} (quality 4) ==")
        print(f"  bucket -> {res['bucket']}, next due {iso(res['next_due_at'])}")
        print(f"  mastery delta {res['mastery_delta']:+.1f}; "
              f"verification currency: {res['verification_currency']['action']}")

    # on-demand rewind with citations
    digest = rewind(stores, user_id="demo",
                    topic="take me back through guitar",
                    track_id="guitar-hobby", ladder=LADDER)
    print(f"\n== rewind digest ==\n  {digest['summary']}")
    for sec in digest["sections"]:
        print(f"  [{sec['skill_tag']}] Q: {sec['prompt']['question']}")
        for g in sec.get("gaps", []):
            print(f"    gap re-ask ({g['was']}) -> {g['route']}")

    os.makedirs(OUT_DIR, exist_ok=True)
    schedule_doc = {
        "generated_at": iso(NOW),
        "due": [{**i.as_row(), "due_at": iso(i.due_at)} for i in due],
        "upcoming": [{**i.as_row(), "due_at": iso(i.due_at)} for i in upcoming],
    }
    with open(os.path.join(OUT_DIR, "schedule.json"), "w") as f:
        json.dump(schedule_doc, f, indent=2)
    with open(os.path.join(OUT_DIR, "recap_digest.json"), "w") as f:
        json.dump(digest, f, indent=2, default=str)
    print(f"\nwrote {OUT_DIR}/recap_digest.json + schedule.json")
    assert digest["sections"], "digest must have sections for a seeded user"
    assert digest["citations"], "digest must cite the knowledge DB"
    urls = {c["source_url"] for c in digest["citations"]}
    assert all(urls), "every citation must carry a source URL"


if __name__ == "__main__":
    main()
