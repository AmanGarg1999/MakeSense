"""LL-08 tests: interest-drift routing (offers + goal protection), learning-mode
routing (defaults, override, single verification endpoint), project-together
reverse-derivation with cited content, future-path suggestions grounded in a
seeded 2-track user's own data, and the interest store against a fake conn.
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.interest_config import load_config, load_kg           # noqa: E402
from app import interest_drift as drift                        # noqa: E402
from app import learning_modes as modes                        # noqa: E402
from app import future_paths as fp                             # noqa: E402
from app import interest_store as store                        # noqa: E402
from app.content_citations import (load_pack_index, cite_for_skill,   # noqa: E402
                                   verify_citations)

CFG = load_config()
KG = load_kg()
DAY = 86400
NOW = 1_700_000_000.0  # fixed clock -> deterministic decay


def sig(domain, kind, age_days, weight=None, **kw):
    s = {"ts": NOW - age_days * DAY, "kind": kind, "domain": domain}
    if weight is not None:
        s["weight"] = weight
    s.update(kw)
    return s


def drift_signals():
    """Baseline (days 6-3 ago): the user is working on their stated goal, python.
    Recent (days 2-0 ago): interest swings hard to guitar (searches, new track,
    content) — the classic drift pattern."""
    return [
        sig("python", "session", 6), sig("python", "session", 5),
        sig("python", "content", 4), sig("python", "session", 3),
        sig("guitar", "search", 2), sig("guitar", "content", 1),
        sig("guitar", "track_start", 1), sig("guitar", "content", 0),
        sig("guitar", "search", 0),
    ]


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


def seeded_two_track_user():
    return [
        {"track_id": "t-guitar", "skill_tag": "guitar", "goal_type": "hobby",
         "level_index": 1, "ladder": guitar_ladder(), "sessions": 9,
         "mastery_vector": {"barre chords": {"score": 0.8}, "repertoire": {"score": 0.75}}},
        {"track_id": "t-python", "skill_tag": "python", "goal_type": "job-ready",
         "level_index": 0, "ladder": python_ladder(), "sessions": 6,
         "mastery_vector": {"syntax": {"score": 0.6}, "functions": {"score": 0.2},
                            "files": {"score": 0.55}}},
    ]


# ---------------------------------------------------------------------------
# 1. interest drift
# ---------------------------------------------------------------------------

class TestInterestDrift(unittest.TestCase):
    def test_profile_and_confidence(self):
        profile = drift.build_interest_profile(drift_signals(), CFG, NOW)
        self.assertIn("guitar", profile)
        self.assertIn("python", profile)
        self.assertGreater(profile["guitar"].confidence, CFG["change_point"]["min_confidence"])
        self.assertGreater(profile["guitar"].weight, 0)

    def test_change_point_detected_both_directions(self):
        profile = drift.build_interest_profile(drift_signals(), CFG, NOW)
        events = drift.detect_change_points(drift_signals(), profile, CFG, NOW,
                                            goal_domains={"python"})
        by = {e.domain: e for e in events}
        self.assertIn("guitar", by)
        self.assertEqual(by["guitar"].direction, "rising")
        self.assertIn("python", by)
        self.assertEqual(by["python"].direction, "falling")
        self.assertTrue(by["python"].is_goal_track)

    def test_drift_becomes_quest_offer_and_goal_stays_intact(self):
        goals = [{"track_id": "t-python", "domain": "python"}]
        report = drift.route_interests(drift_signals(), goals, CFG, NOW)
        # the drifting interest becomes an OPTIONAL side quest ...
        self.assertTrue(report.quest_offers, "expected a quest offer for guitar")
        self.assertEqual(report.quest_offers[0].domain, "guitar")
        self.assertIn("guitar", report.quest_offers[0].offer_text)
        # ... and the stated goal is NEVER silently changed
        self.assertTrue(report.goal_protection.goal_intact)
        self.assertEqual(goals, [{"track_id": "t-python", "domain": "python"}])
        # a falling goal track raises the explicit-ask (the one place we ask)
        self.assertTrue(report.goal_protection.requires_explicit_ask)
        q = report.goal_protection.question or ""
        self.assertIn("python", q)
        self.assertIn("guitar", q)

    def test_low_confidence_yields_no_offer(self):
        thin = [sig("photography", "search", 0), sig("photography", "content", 1)]
        report = drift.route_interests(thin, [{"track_id": "t-x", "domain": "python"}],
                                       CFG, NOW)
        self.assertEqual(report.quest_offers, [])

    def test_rising_domain_that_is_already_a_track_is_not_a_side_quest(self):
        goals = [{"track_id": "t-python", "domain": "python"}]
        report = drift.route_interests(drift_signals(), goals, CFG, NOW,
                                       active_track_domains={"python", "guitar"})
        # guitar is an active track here, so it must not be offered as a side quest
        self.assertEqual([o.domain for o in report.quest_offers], [])

    def test_signals_from_delivery_segments(self):
        segs = [{"skill_tag": "guitar", "created_at": NOW - DAY, "abandoned": False},
                {"skill_tag": "guitar", "created_at": NOW - 2 * DAY, "abandoned": True}]
        sigs = drift.signals_from_delivery_segments(segs)
        self.assertEqual(len(sigs), 2)
        self.assertEqual(sigs[0]["kind"], "session")
        self.assertEqual(sigs[0]["domain"], "guitar")


# ---------------------------------------------------------------------------
# 2. learning-mode routing
# ---------------------------------------------------------------------------

class TestLearningModes(unittest.TestCase):
    def test_goal_defaults(self):
        self.assertEqual(modes.select_learning_mode(
            {"skill_tag": "guitar", "goal_type": "hobby"}, CFG).mode, "guided")
        d = modes.select_learning_mode({"skill_tag": "python", "goal_type": "job-ready"}, CFG)
        self.assertEqual(d.mode, "project_together")
        self.assertEqual(d.decided_by, "goal_default")

    def test_level_default_novice_is_guided(self):
        d = modes.select_learning_mode(
            {"skill_tag": "python", "goal_type": "job-ready"}, CFG, learner_level="novice")
        self.assertEqual(d.mode, "guided")
        self.assertEqual(d.decided_by, "level_default")

    def test_user_override_wins(self):
        d = modes.select_learning_mode(
            {"skill_tag": "python", "goal_type": "job-ready"}, CFG, override="drill_verify")
        self.assertEqual(d.mode, "drill_verify")
        self.assertEqual(d.decided_by, "user_override")
        with self.assertRaises(ValueError):
            modes.select_learning_mode({"skill_tag": "x"}, CFG, override="nonsense")

    def test_all_four_doors_reachable_for_one_skill(self):
        doors = modes.modes_for_skill("guitar", CFG)
        self.assertEqual(len(doors), 4)
        self.assertEqual({d["mode"] for d in doors}, set(CFG["mode_routing"]["modes"]))

    def test_every_mode_shares_the_same_verification_endpoint(self):
        endpoints = {modes.verification_endpoint(m, "guitar", CFG)["endpoint"]
                     for m in CFG["mode_routing"]["modes"]}
        self.assertEqual(len(endpoints), 1)
        self.assertEqual(endpoints.pop(), CFG["mode_routing"]["verification_endpoint"])


# ---------------------------------------------------------------------------
# 3. project-together reverse-derivation
# ---------------------------------------------------------------------------

class TestProjectCurriculum(unittest.TestCase):
    def test_reverse_derived_plan_is_cited(self):
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
        pack = load_pack_index()
        plan = modes.derive_project_curriculum(artifact, KG, pack, CFG)
        self.assertEqual(plan["mode"], "project_together")
        self.assertIn("reverse", plan["direction"])
        # terminates at the artifact assembly
        self.assertEqual(plan["steps"][-1]["kind"], "assemble")
        self.assertIn("Route-plotting map", plan["steps"][-1]["title"])
        # the prereq closure (algebra) appears as a foundation step
        self.assertIn("algebra", [s["skill"] for s in plan["steps"]])
        if pack:  # the repo ships a real content pack
            self.assertTrue(plan["cited"], "every step must trace to cited pack content")
            self.assertEqual(plan["uncited_steps"], [])
            for s in plan["steps"]:
                for c in s["cites"]:
                    self.assertTrue(c["sha256"])
                    self.assertEqual(c["source"], "NCERT")

    def test_uncited_step_is_flagged_not_fabricated(self):
        artifact = {"title": "Origami crane", "skill_tag": "origami",
                    "capabilities": [{"sub_skill": "crease fold"}]}
        plan = modes.derive_project_curriculum(artifact, KG, None, CFG)
        self.assertFalse(plan["cited"])
        self.assertTrue(plan["uncited_steps"])


# ---------------------------------------------------------------------------
# 4. future paths (mk-031 extension)
# ---------------------------------------------------------------------------

class TestFuturePaths(unittest.TestCase):
    def test_three_grounded_suggestions_for_seeded_user(self):
        sugs = fp.propose_future_paths(seeded_two_track_user(), KG, CFG)
        self.assertEqual(len(sugs), 3)
        kinds = {s.kind for s in sugs}
        self.assertIn("adjacent", kinds, "KG adjacent-skill suggestion must appear")
        for s in sugs:
            self.assertTrue(s.why_now)
            self.assertTrue(s.evidence)
            self.assertGreaterEqual(s.suggested_level if s.suggested_level is not None else 0, 0)

    def test_adjacent_suggestion_comes_from_kg(self):
        sugs = fp.propose_future_paths(seeded_two_track_user(), KG, CFG, limit=4)
        adj = [s for s in sugs if s.kind == "adjacent"]
        self.assertTrue(adj)
        # guitar -> music_theory is the seeded KG edge
        self.assertEqual(adj[0].suggested_skill, "music_theory")
        self.assertIn("theory", adj[0].why_now.lower())

    def test_consolidate_targets_the_gap(self):
        sugs = fp.propose_future_paths(seeded_two_track_user(), KG, CFG, limit=4)
        cons = [s for s in sugs if s.kind == "consolidate"]
        self.assertTrue(cons)
        self.assertEqual(cons[0].suggested_skill, "python")
        self.assertIn("functions", cons[0].why_now)

    def test_next_level_when_rung_cleared(self):
        sugs = fp.propose_future_paths(seeded_two_track_user(), KG, CFG, limit=4)
        nl = [s for s in sugs if s.kind == "next_level"]
        self.assertTrue(nl)
        self.assertEqual(nl[0].suggested_skill, "guitar")
        self.assertEqual(nl[0].suggested_level, 2)


# ---------------------------------------------------------------------------
# 5. content citations
# ---------------------------------------------------------------------------

class TestCitations(unittest.TestCase):
    def test_pack_index_loads_with_provenance(self):
        pack = load_pack_index()
        self.assertIsNotNone(pack, "the repo ships packs/dist/manifest.verify.json")
        assert pack is not None
        self.assertEqual(pack["source"]["name"], "NCERT")
        self.assertEqual(pack["source"]["license"], "CC-BY-NC-SA-4.0")

    def test_cite_for_skill_matches_pack_item(self):
        pack = load_pack_index()
        cites = cite_for_skill("coordinate_geometry", KG, pack, per_skill=2)
        self.assertTrue(cites)
        self.assertTrue(verify_citations(cites, pack))


# ---------------------------------------------------------------------------
# 6. interest store (fake asyncpg conn)
# ---------------------------------------------------------------------------

class FakeConn:
    def __init__(self, fetch_rows=None):
        self.calls = []
        self._rows = fetch_rows or []

    async def execute(self, sql, *args):
        self.calls.append((sql, args))
        return "OK"

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return self._rows


class TestInterestStore(unittest.TestCase):
    def test_store_signals_counts_and_inserts(self):
        conn = FakeConn()
        n = asyncio.get_event_loop().run_until_complete(
            store.store_signals(conn, 1, [{"ts": NOW, "kind": "search", "domain": "guitar"}]))
        self.assertEqual(n, 1)
        self.assertIn("INSERT INTO interest_signals", conn.calls[0][0])

    def test_store_quest_offers_sets_cooldown(self):
        conn = FakeConn()
        asyncio.get_event_loop().run_until_complete(
            store.store_quest_offers(conn, 1, [{"domain": "guitar", "offer_text": "x",
                                                "confidence": 0.9, "delta": 0.5,
                                                "evidence": {}}], CFG))
        self.assertIn("INSERT INTO quest_offers", conn.calls[0][0])
        self.assertEqual(conn.calls[0][1][-1], str(CFG["drift"]["offer_cooldown_days"]))


# ---------------------------------------------------------------------------
# 7. HTTP surface (fastapi TestClient, mirrors LL-04's route tests)
# ---------------------------------------------------------------------------

class TestRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import time as _t
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.interest_routes import router as interest_router
        cls._t = _t
        app = FastAPI()
        app.include_router(interest_router)
        cls.client = TestClient(app)

    def _recent_signal(self, domain, kind, age_days):
        return {"ts": self._t.time() - age_days * DAY, "kind": kind, "domain": domain}

    def test_drift_evaluate_endpoint(self):
        signals = [self._recent_signal("python", "session", 6),
                   self._recent_signal("python", "session", 5),
                   self._recent_signal("python", "content", 4),
                   self._recent_signal("python", "session", 3),
                   self._recent_signal("guitar", "search", 2),
                   self._recent_signal("guitar", "content", 1),
                   self._recent_signal("guitar", "track_start", 1),
                   self._recent_signal("guitar", "content", 0),
                   self._recent_signal("guitar", "search", 0)]
        r = self.client.post("/api/interest/drift/evaluate",
                             json={"signals": signals,
                                   "goal_tracks": [{"track_id": "t", "domain": "python"}]})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["goal_protection"]["goal_intact"])
        self.assertTrue(body["quest_offers"])

    def test_learning_mode_endpoint(self):
        r = self.client.post("/api/interest/learning-mode",
                             json={"track": {"skill_tag": "python", "goal_type": "job-ready"}})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["selection"]["mode"], "project_together")
        self.assertEqual(body["verification"]["endpoint"], CFG["mode_routing"]["verification_endpoint"])

    def test_learning_modes_get_endpoint(self):
        r = self.client.get("/api/interest/learning-modes/guitar")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["doors"]), 4)

    def test_future_paths_endpoint(self):
        r = self.client.post("/api/interest/future-paths",
                             json={"tracks": seeded_two_track_user()})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["suggestions"]), 3)

    def test_project_curriculum_endpoint(self):
        artifact = {"title": "Route-plotting map", "skill_tag": "coordinate_geometry",
                    "capabilities": [{"sub_skill": "cartesian plane"}]}
        r = self.client.post("/api/interest/project-curriculum", json={"artifact": artifact})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["mode"], "project_together")
        self.assertEqual(body["steps"][-1]["kind"], "assemble")


if __name__ == "__main__":
    unittest.main(verbosity=2)
