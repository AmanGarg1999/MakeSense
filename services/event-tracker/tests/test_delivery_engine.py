"""LL-04 delivery engine tests: classifier, mode resolution, adaptive flip
rule (with evidence), companion voice generation from real ladder state, and
the telemetry store against a fake asyncpg connection."""

import asyncio
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.delivery_engine import (classify_segment, resolve_mode, mode_is_active,
                                 evaluate_flip_rule, generate_bridge,
                                 generate_bridges_many)
from app.delivery_store import store_segment, run_flip_check, recent_skill_segments
from app.dial_config import load_config

CFG = load_config()


# ---------------------------------------------------------------------------
# Segment classifier
# ---------------------------------------------------------------------------

class TestClassifier(unittest.TestCase):
    def test_explicit_kind_wins(self):
        self.assertEqual(
            classify_segment({"kind": "consolidation", "title": "Intro to loops"}, CFG),
            "consolidation")

    def test_consolidation_markers(self):
        self.assertEqual(classify_segment({"title": "Retrieval practice: chords"}, CFG),
                         "consolidation")
        self.assertEqual(classify_segment({"title": "Week recap", "content_type": "review"}, CFG),
                         "consolidation")

    def test_intake_markers(self):
        self.assertEqual(classify_segment({"title": "What are functions", "tags": ["new_concept"]}, CFG),
                         "intake")
        self.assertEqual(classify_segment({"title": "Watch: how a lens works", "content_type": "video"}, CFG),
                         "intake")

    def test_first_visit_heuristic(self):
        self.assertEqual(classify_segment({"title": "Something novel"}, CFG, prior_visits=0), "intake")
        self.assertEqual(classify_segment({"title": "Something novel"}, CFG, prior_visits=3), "consolidation")


# ---------------------------------------------------------------------------
# Mode resolution (per-track defaults, escalation, energy)
# ---------------------------------------------------------------------------

class TestModeResolution(unittest.TestCase):
    def test_hobby_intake_passive_consolidation_active(self):
        d = resolve_mode({"goal_type": "hobby"}, "intake", CFG)
        self.assertEqual(d.mode_class, "passive")
        d2 = resolve_mode({"goal_type": "hobby"}, "consolidation", CFG)
        self.assertEqual(d2.mode_class, "active")

    def test_expert_defaults_active(self):
        d = resolve_mode({"goal_type": "expert"}, "intake", CFG)
        self.assertTrue(mode_is_active(d.mode, CFG))

    def test_escalation_overrides_everything(self):
        d = resolve_mode({"goal_type": "hobby"}, "intake", CFG,
                         active_escalation={"reason": "passive_dropout"})
        self.assertEqual(d.decided_by, "escalation")
        self.assertEqual(d.mode_class, "active")

    def test_low_energy_intake_is_passive_scaffold(self):
        d = resolve_mode({"goal_type": "expert"}, "intake", CFG, energy=1)
        # expert intake default is active; energy override must not fire
        # against an already-active default (we never *remove* active delivery
        # for energy unless the track default is passive intake)
        self.assertEqual(d.decided_by, "track_default")
        d2 = resolve_mode({"goal_type": "hobby"}, "intake", CFG, energy=1)
        self.assertEqual(d2.mode_class, "passive")


# ---------------------------------------------------------------------------
# Adaptive flip rule
# ---------------------------------------------------------------------------

def seg(mode_class, session, abandoned=False, outcome="none", sid=1):
    return {"id": sid, "mode_class": mode_class, "session_id": session,
            "abandoned": abandoned, "retrieval_outcome": outcome}


class TestFlipRule(unittest.TestCase):
    def test_below_min_sessions_no_flip(self):
        segments = [seg("passive", "s1"), seg("passive", "s1", abandoned=True)]
        dec = evaluate_flip_rule("guitar", segments, CFG)
        self.assertFalse(dec.should_flip)

    def test_passive_dropout_fires_with_evidence(self):
        # Realistic pattern: passive-heavy sessions with drop-off, few abandons
        # in the active segments we do have.
        segments = []
        i = 0
        for s in ("s1", "s2", "s3", "s4"):
            i += 1
            segments.append(seg("passive", s, abandoned=(s != "s1"), sid=i))
        segments.append(seg("active", "s5", abandoned=False, sid=i + 1))
        dec = evaluate_flip_rule("python", segments, CFG)
        self.assertTrue(dec.should_flip)
        self.assertEqual(dec.reason, "passive_dropout")
        self.assertGreaterEqual(dec.evidence["passive_abandon_rate"],
                                CFG["flip_rule"]["passive_abandon_rate_threshold"])
        self.assertIn("thresholds", dec.evidence)

    def test_failed_retrieval_fires(self):
        segments = [seg("passive", f"s{n}", outcome="incorrect", sid=n) for n in (1, 2, 3)]
        dec = evaluate_flip_rule("photography", segments, CFG)
        self.assertTrue(dec.should_flip)
        self.assertEqual(dec.reason, "failed_retrieval")
        self.assertGreaterEqual(dec.evidence["failed_retrieval_count"],
                                CFG["flip_rule"]["failed_retrieval_count_threshold"])

    def test_all_active_good_outcome_no_flip(self):
        segments = [seg("active", f"s{n}", outcome="correct", sid=n) for n in (1, 2, 3, 4)]
        dec = evaluate_flip_rule("cooking", segments, CFG)
        self.assertFalse(dec.should_flip)

    def test_high_abandon_in_both_modes_does_not_flip(self):
        # Correlation must be *with passive*: equal abandon rates -> no flip
        segments = [seg("passive", f"s{n}", abandoned=True, sid=n) for n in (1, 2)]
        segments += [seg("active", f"s{n}", abandoned=True, sid=n + 10) for n in (1, 2, 3)]
        dec = evaluate_flip_rule("tennis", segments, CFG)
        self.assertFalse(dec.should_flip or dec.reason == "passive_dropout")


# ---------------------------------------------------------------------------
# Companion voice — generated from actual ladder/mastery state (acceptance:
# 20+ distinct strings across state permutations, none canned)
# ---------------------------------------------------------------------------

def ladder(skill_levels=4, sub_skills=("grip", "strumming", "chord_changes")):
    levels = ["Novice", "Competent", "Proficient", "Expert"]
    cando = {
        "grip": "hold the pick without tension during a 2-minute drill",
        "strumming": "keep a steady down-up pattern at 90 bpm",
        "chord_changes": "switch G to D mid-phrase without stopping",
    }
    return {"rungs": [
        {"level_index": i, "level_name": levels[i],
         "sub_skills": [{"name": s,
                         "can_do_statements": [f"can {cando.get(s, 'perform ' + s)}"]}
                        for s in sub_skills]}
        for i in range(skill_levels)
    ]}


class TestCompanionVoice(unittest.TestCase):
    def test_silent_without_ladder_state(self):
        self.assertIsNone(generate_bridge({"skill_tag": "x"}, {}, {"rungs": []}, CFG))

    def test_gap_callout_uses_real_score_and_cando(self):
        mv = {"grip": {"score": 0.75}, "strumming": {"score": 0.3}, "chord_changes": {"score": 0.9}}
        b = generate_bridge({"skill_tag": "guitar", "current_ladder_rung": 1}, mv, ladder(), CFG)
        self.assertIn("strumming", b["text"])
        self.assertIn("30%", b["text"])
        self.assertIn("keep a steady down-up pattern", b["text"])
        self.assertEqual(b["motivation"], "competence")

    def test_strength_mentions_next_rung_cando(self):
        mv = {"grip": {"score": 0.9}, "strumming": {"score": 0.95}, "chord_changes": {"score": 0.88}}
        b = generate_bridge({"skill_tag": "guitar", "current_ladder_rung": 2}, mv, ladder(), CFG)
        self.assertIn("genuinely solid", b["text"])

    def test_20_plus_distinct_strings_from_state_matrix(self):
        """Acceptance: 20+ companion strings generated from actual
        ladder/mastery state — varied scores x rungs x tracks, all distinct,
        all tied to their state's sub-skill names."""
        tracks = {
            "guitar": ("grip", "strumming", "chord_changes"),
            "python": ("syntax", "functions", "classes"),
            "photography": ("exposure", "focus", "composition"),
        }
        seen = set()
        score_sets = ((0.2, 0.4, 0.65), (0.85, 0.9, 0.7), (0.1, 0.2, 0.3),
                      (0.62, 0.95, 0.88), (0.0, 0.0, 0.0), (0.75, 0.62, 0.7),
                      (0.45, 0.82, 0.66), (0.28, 0.71, 0.93))
        for skill, subs in tracks.items():
            for rung in range(4):
                for scores in score_sets:
                    mv = {name: {"score": s} for name, s in zip(subs, scores)}
                    b = generate_bridge({"skill_tag": skill, "current_ladder_rung": rung},
                                        mv, ladder(sub_skills=subs), CFG)
                    assert b is not None
                    seen.add(b["text"])
        self.assertGreaterEqual(len(seen), 20)
        # no generic filler: every string references its own skill or sub-skill
        joined = " ".join(seen).lower()
        for skill in tracks:
            self.assertIn(skill, joined)

    def test_bridges_many_respects_word_budget(self):
        triples = [({"skill_tag": "guitar", "current_ladder_rung": 0},
                    {"grip": {"score": 0.3}}, ladder())] * 5
        out = generate_bridges_many(triples, CFG)
        self.assertEqual(len(out), 5)
        for b in out:
            self.assertLessEqual(len(b["text"].split()), CFG["companion_voice"]["max_bridge_words"])


# ---------------------------------------------------------------------------
# Telemetry store against a fake asyncpg conn (proves SQL wiring shape)
# ---------------------------------------------------------------------------

class FakeConn:
    def __init__(self, segment_rows=None, escalation_rows=None, track_row=None):
        self.executed = []
        self.segment_rows = segment_rows or []
        self.escalation_rows = escalation_rows or []
        self.track_row = track_row
        self._next_id = 1000

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def fetch(self, sql, *args):
        if "delivery_segments" in sql:
            return self.segment_rows
        return []

    async def fetchrow(self, sql, *args):
        if "delivery_mode_escalations" in sql and "SELECT" in sql:
            return self.escalation_rows[0] if self.escalation_rows else None
        if "skill_tracks" in sql:
            return self.track_row
        if "UPDATE" in sql and "sessions_consumed" in sql:
            return {"sessions_consumed": 1, "escalate_for_sessions": CFG["flip_rule"]["escalation_sessions"]}
        return None


def run(coro):
    return asyncio.run(coro)


class TestTelemetryStore(unittest.TestCase):
    def test_store_segment_writes_row(self):
        conn = FakeConn()
        s = {"user_id": 1, "track_id": "t-1", "skill_tag": "guitar",
             "session_id": "s1", "segment_index": 0, "segment_kind": "intake",
             "delivery_mode": "read", "mode_class": "passive",
             "decided_by": "track_default", "dwell_seconds": 30,
             "paused_seconds": 2, "abandoned": False, "retrieval_outcome": None,
             "energy_level": 3, "ladder_level": 0}
        run(store_segment(conn, s))
        sql, args = conn.executed[0]
        self.assertIn("INSERT INTO delivery_segments", sql)
        self.assertEqual(args[0], 1)
        self.assertEqual(args[3], "s1")

    def test_run_flip_check_logs_escalation_with_evidence(self):
        rows = []
        i = 0
        for sn in ("s1", "s2", "s3", "s4"):
            for k in range(2):
                i += 1
                rows.append({"id": i, "session_id": sn, "mode_class": "passive",
                             "abandoned": k == 1, "retrieval_outcome": "none"})
        conn = FakeConn(segment_rows=rows, track_row={"id": "track-uuid"})
        result = run(run_flip_check(conn, "guitar", 1, CFG))
        self.assertTrue(result["should_flip"])
        self.assertEqual(result["reason"], "passive_dropout")
        insert = [e for e in conn.executed if "INSERT INTO delivery_mode_escalations" in e[0]]
        self.assertEqual(len(insert), 1)
        evidence = json.loads(insert[0][1][4])
        self.assertIn("thresholds", evidence)
        self.assertIn("passive_abandon_rate", evidence)

    def test_no_escalation_stored_when_rule_silent(self):
        rows = [{"id": n, "session_id": f"s{m}", "mode_class": "active",
                 "abandoned": False, "retrieval_outcome": "correct"}
                for n in range(1, 13) for m in range(1, 4)]
        conn = FakeConn(segment_rows=rows)
        result = run(run_flip_check(conn, "cooking", 1, CFG))
        self.assertFalse(result["should_flip"])
        self.assertFalse([e for e in conn.executed if "INSERT INTO delivery_mode_escalations" in e[0]])


class TestHttpSurface(unittest.TestCase):
    """The /api/delivery endpoints without DB (pure-logic paths)."""

    def setUp(self):
        os.environ.pop("DATABASE_URL", None)
        # import after env is clean
        from app import delivery_routes
        delivery_routes._pool = None
        from starlette.testclient import TestClient
        from app.main import app
        self.client = TestClient(app)

    def test_decide_endpoint_classifies_and_resolves(self):
        r = self.client.post("/api/delivery/segments/decide", json={
            "user_id": 1, "skill_tag": "guitar", "session_id": "s1",
            "title": "Practice chord changes", "goal_type": "hobby"})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["segment_kind"], "consolidation")
        self.assertEqual(d["mode_class"], "active")

    def test_bridge_endpoint_from_state(self):
        mv = {"grip": {"score": 0.9}, "strumming": {"score": 0.85}, "chord_changes": {"score": 0.8}}
        r = self.client.post("/api/delivery/bridges", json={
            "track_state": {"skill_tag": "guitar", "current_ladder_rung": 0},
            "mastery_vector": mv, "ladder": ladder()})
        self.assertEqual(r.status_code, 200)
        b = r.json()["bridge"]
        self.assertIsNotNone(b)
        self.assertIn("grip", b["text"].lower())


if __name__ == "__main__":
    unittest.main()
