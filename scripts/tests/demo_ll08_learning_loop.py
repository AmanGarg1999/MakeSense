#!/usr/bin/env python3
"""LL-08 acceptance demo.

Runs the full interest-drift -> offer / goal-protection path on a synthetic
telemetry stream, the future-path engine on a seeded 2-track user, and the
project-together reverse-derivation on a real topic from the shipped NCERT pack
— printing the grounded evidence at each step.

Run: python3 scripts/tests/demo_ll08_learning_loop.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "services", "event-tracker"))

from app.interest_config import load_config, load_kg            # noqa: E402
from app import interest_drift as drift                         # noqa: E402
from app import learning_modes as modes                         # noqa: E402
from app import future_paths as fp                              # noqa: E402
from app.content_citations import load_pack_index               # noqa: E402

CFG = load_config()
KG = load_kg()
DAY = 86400
NOW = 1_700_000_000.0  # fixed clock -> reproducible decay


def sig(domain, kind, age_days):
    return {"ts": NOW - age_days * DAY, "kind": kind, "domain": domain}


def guitar_ladder():
    return {"rungs": [
        {"level_index": 0, "level_name": "novice",
         "sub_skills": [{"name": "chords"}, {"name": "strumming"}]},
        {"level_index": 1, "level_name": "competent",
         "sub_skills": [{"name": "barre chords"}, {"name": "repertoire"}]},
        {"level_index": 2, "level_name": "proficient",
         "sub_skills": [{"name": "improvisation"}]},
    ]}


def python_ladder():
    return {"rungs": [
        {"level_index": 0, "level_name": "novice",
         "sub_skills": [{"name": "syntax"}, {"name": "functions"}, {"name": "files"}]},
    ]}


# ---------------------------------------------------------------------------

def demo_drift():
    print("=" * 74)
    print("1. INTEREST-DRIFT DEMO — telemetry pattern -> quest offer, goal intact")
    print("=" * 74)
    signals = [
        sig("python", "session", 6), sig("python", "session", 5),
        sig("python", "content", 4), sig("python", "session", 3),   # baseline: goal
        sig("guitar", "search", 2), sig("guitar", "content", 1),
        sig("guitar", "track_start", 1), sig("guitar", "content", 0),
        sig("guitar", "search", 0),                                # recent: drift
    ]
    goals = [{"track_id": "t-python", "domain": "python"}]
    report = drift.route_interests(signals, goals, CFG, NOW)

    print("\nRolling interest profile (time-decayed, confidence-gated):")
    for dom, i in sorted(report.profile.items(), key=lambda kv: -kv[1].weight):
        print(f"  {dom:10s} weight={i.weight:5.2f}  share={i.share*100:4.0f}%  "
              f"conf={i.confidence:.2f}  signals={i.signal_count}  sources={i.sources}")

    print("\nChange points (windowed share shift):")
    for e in report.drift_events:
        flag = "  <- STATED GOAL" if e.is_goal_track else ""
        print(f"  {e.domain:10s} {e.direction:8s} "
              f"{e.baseline_share*100:4.0f}% -> {e.recent_share*100:4.0f}%  "
              f"delta={e.delta:+.2f}  conf={e.confidence:.2f}{flag}")

    assert report.quest_offers, "expected a side-quest offer"
    print("\nSide-quest offer (LL-07 will surface this; the goal is NOT touched):")
    for o in report.quest_offers:
        print(f"  [{o.domain}] {o.offer_text}")

    gp = report.goal_protection
    print(f"\nGoal protection: goal_intact={gp.goal_intact}  "
          f"requires_explicit_ask={gp.requires_explicit_ask} ({gp.reason})")
    if gp.question:
        print(f"  ask (the ONE place we ask): {gp.question}")

    assert gp.goal_intact is True
    assert goals == [{"track_id": "t-python", "domain": "python"}], "goal mutated!"
    assert report.quest_offers[0].domain == "guitar"
    assert gp.requires_explicit_ask is True
    print("\nOK: drift -> quest offer; stated goal intact; goal change only via explicit ask.")


def demo_future_paths():
    print("\n" + "=" * 74)
    print("2. FUTURE PATHS — 3 grounded next-path suggestions (seeded 2-track user)")
    print("=" * 74)
    tracks = [
        {"track_id": "t-guitar", "skill_tag": "guitar", "goal_type": "hobby",
         "level_index": 1, "ladder": guitar_ladder(), "sessions": 9,
         "mastery_vector": {"barre chords": {"score": 0.8}, "repertoire": {"score": 0.75}}},
        {"track_id": "t-python", "skill_tag": "python", "goal_type": "job-ready",
         "level_index": 0, "ladder": python_ladder(), "sessions": 6,
         "mastery_vector": {"syntax": {"score": 0.6}, "functions": {"score": 0.2},
                            "files": {"score": 0.55}}},
    ]
    sugs = fp.propose_future_paths(tracks, KG, CFG, limit=3)
    for i, s in enumerate(sugs, 1):
        print(f"\n  {i}. [{s.kind}] {s.title}")
        print(f"     why this, why now: {s.why_now}")
        print(f"     evidence: {s.evidence}")
    assert len(sugs) == 3, f"expected 3 suggestions, got {len(sugs)}"
    assert any(s.kind == "adjacent" for s in sugs), "KG adjacent suggestion missing"
    assert all(s.why_now and s.evidence for s in sugs)
    print("\nOK: 3 suggestions, each grounded in the user's own mastery data + KG edges.")


def demo_project_curriculum():
    print("\n" + "=" * 74)
    print("3. PROJECT-TOGETHER — reverse-derived plan with cited content")
    print("=" * 74)
    pack = load_pack_index()
    artifact = {
        "title": "Route-plotting map",
        "skill_tag": "coordinate_geometry",
        "capabilities": [
            {"sub_skill": "cartesian plane", "can_do": "place the origin and axes"},
            {"sub_skill": "plotting", "can_do": "plot points from coordinates"},
            {"sub_skill": "distance formula", "can_do": "compute a distance between points"},
        ],
        "end_state": "a map with plotted landmarks and measured distances",
    }
    plan = modes.derive_project_curriculum(artifact, KG, pack, CFG)
    print(f"\n  mode={plan['mode']}  direction={plan['direction']}")
    print(f"  target artifact: {artifact['title']}")
    for s in plan["steps"]:
        cite = s["cites"][0] if s["cites"] else None
        cite_str = (f"{cite['content_id']} | {cite['chapter']} | "
                    f"{cite['source']} {cite['license']} | {cite['locator']}") if cite else "NONE"
        print(f"\n  step {s['index']} [{s['kind']}] {s['title']}")
        print(f"     why: {s['why']}")
        print(f"     cited: {cite_str}")
    endpoint = plan["verification_endpoint"]
    print(f"\n  all modes terminate at: {endpoint}")
    assert plan["mode"] == "project_together"
    assert plan["steps"][-1]["kind"] == "assemble"
    assert plan["cited"] is True, "plan must be fully cited"
    assert plan["uncited_steps"] == []
    assert plan["verification_endpoint"] == CFG["mode_routing"]["verification_endpoint"]
    print("\nOK: reverse-derived plan, every step cited (NCERT pack), same LL-05 endpoint.")


def demo_modes():
    print("\n" + "=" * 74)
    print("BONUS — learning-mode routing: one skill, four doors, one endpoint")
    print("=" * 74)
    for m in modes.modes_for_skill("python", CFG):
        ep = modes.verification_endpoint(m["mode"], "python", CFG)["endpoint"]
        print(f"  {m['mode']:16s} {m['description']:70s} -> {ep}")
    assert len(modes.modes_for_skill("python", CFG)) == 4


if __name__ == "__main__":
    demo_drift()
    demo_future_paths()
    demo_project_curriculum()
    demo_modes()
    print("\n" + "=" * 74)
    print("LL-08 DEMO OK — drift routed to a quest without derailing the goal,")
    print("3 grounded future paths, project mode reverse-derived & cited.")
    print("=" * 74)
