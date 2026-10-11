"""LL-07 tests: stores contract, batching math, side-quest engine, demo track."""

import math
import time

import pytest

from ll07.stores import Stores, STORE_NAMES, StoreError
from ll07.batches import plan_batches, record_batch_completion, WEEK_MINUTES
from ll07 import quests as Q


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def stores():
    s = Stores(":memory:")
    yield s
    s.close()


LADDER = [
    {"run": 1, "skill": "g:grip",       "level": 0, "minutes": 40, "can_do": "hold the pick without tension",
     "adjacent": [{"title": "Pick material experiment", "kind": "micro_project", "minutes": 45,
                   "skills": ["g:grip", "g:tone"], "credit": 1.0}]},
    {"run": 2, "skill": "g:strum",      "level": 0, "minutes": 50, "can_do": "strum a 4-chord loop in time"},
    {"run": 3, "skill": "g:chords",     "level": 1, "minutes": 60, "can_do": "switch C-G-Em-D at 80bpm",
     "adjacent": [{"title": "Capo tooling & transposition", "kind": "tool", "minutes": 30,
                   "skills": ["g:chords"], "credit": 0.5},
                  {"title": "Fretboard geometry tangent", "kind": "tangent", "minutes": 40,
                   "skills": ["g:theory"], "credit": 1.0}]},
    {"run": 4, "skill": "g:barre",      "level": 1, "minutes": 70, "can_do": "clean F barre chord"},
    {"run": 5, "skill": "g:fingerstyle","level": 2, "minutes": 80, "can_do": "play travis picking at 90bpm"},
    {"run": 6, "skill": "g:improv",     "level": 2, "minutes": 90, "can_do": "solo over a 12-bar blues"},
    {"run": 7, "skill": "g:repertoire", "level": 3, "minutes": 60, "can_do": "perform 3 songs start-to-finish"},
]


def seed_snapshot(s):
    s.append("snapshots", {"skill_tag": "guitar", "goal_type": "hobby",
                           "ladder_version": "v1", "rungs": LADDER},
             provenance="engine:ladder")


# ---------------------------------------------------------------------------
# stores: six registries, append-only + provenance
# ---------------------------------------------------------------------------

def test_all_six_stores_exist_and_summarize(stores):
    assert STORE_NAMES == ("items", "snapshots", "mastery", "verifications", "recaps", "quests")
    assert stores.summary() == {n: 0 for n in STORE_NAMES}


def test_append_requires_provenance(stores):
    with pytest.raises(StoreError):
        stores.append("mastery", {"user_id": "u1", "skill_tag": "x", "delta": 1})
    with pytest.raises(StoreError):
        stores.append("mastery", {"user_id": "u1"}, provenance="")


def test_unknown_store_rejected(stores):
    with pytest.raises(StoreError):
        stores.append("vault", {}, provenance="user")
    with pytest.raises(StoreError):
        stores.count("vault")


def test_append_only_no_update(stores):
    stores.append("mastery", {"user_id": "u1", "track_id": "t1", "skill_tag": "g:chords",
                              "delta": 2, "cause": "batch_completed"},
                  provenance="engine:batcher", record_id="m1")
    with pytest.raises(StoreError):
        stores.append("mastery", {"delta": 99}, provenance="engine:batcher", record_id="m1")
    # state change = new event; history keeps both, latest folds forward
    stores.append("mastery", {"user_id": "u1", "track_id": "t1", "skill_tag": "g:chords",
                              "delta": 1, "cause": "recap"}, provenance="engine:recap", record_id="m2")
    h = stores.history("mastery", user_id="u1")
    assert [e["cause"] for e in h] == ["batch_completed", "recap"]  # append order
    assert stores.latest("mastery", user_id="u1")["cause"] == "recap"


def test_current_state_folds_vector(stores):
    for skill, d in (("a", 1.0), ("b", 2.0), ("a", 0.5)):
        stores.append("mastery", {"user_id": "u1", "track_id": "t1", "skill_tag": skill,
                                  "delta": d, "cause": "test"}, provenance="test")
    state = stores.current_state("mastery", key_fields=["user_id", "skill_tag"], user_id="u1")
    assert state["u1|a"]["delta"] == 0.5 and state["u1|b"]["delta"] == 2.0


def test_history_filters_on_indexed_and_payload_fields(stores):
    stores.append("items", {"item_id": "i1", "source_url": "https://ncert.example",
                            "license": "CC-BY", "skill_tag": "g:chords", "topic": "guitar",
                            "capture_date": "2026-10-01", "bloom": "apply"},
                  provenance="scraper:ncert")
    assert stores.count("items", skill_tag="g:chords") == 1
    assert stores.count("items", skill_tag="nope") == 0
    # payload (non-indexed) filter
    assert stores.count("items", bloom="apply") == 1


def test_summary_after_seeding_all_six(stores):
    stores.append("items", {"item_id": "i1", "skill_tag": "s"}, provenance="scraper:x")
    stores.append("snapshots", {"skill_tag": "s", "goal_type": "hobby", "rungs": []}, provenance="engine:ladder")
    stores.append("mastery", {"user_id": "u", "skill_tag": "s", "delta": 1}, provenance="test")
    stores.append("verifications", {"user_id": "u", "skill_tag": "s", "outcome": "pass",
                                    "expires_at": time.time() + 86400}, provenance="engine:verify")
    stores.append("recaps", {"user_id": "u", "skill_tag": "s", "due_at": time.time() + 86400,
                             "bucket": 1, "status": "scheduled"}, provenance="engine:recap")
    stores.append("quests", {"quest_id": "q1", "kind": "side", "status": "offered",
                             "track_id": "t", "expires_at": time.time() + 86400}, provenance="engine:quest")
    summary = stores.summary()
    assert set(summary) == set(STORE_NAMES)
    assert all(summary[n] == 1 for n in STORE_NAMES)


# ---------------------------------------------------------------------------
# batches
# ---------------------------------------------------------------------------

def test_batches_from_snapshot_respect_weekly_pacing(stores):
    seed_snapshot(stores)
    batches = plan_batches(stores, track_id="tr1", skill_tag="guitar", goal_type="hobby")
    budget = WEEK_MINUTES["hobby"]
    assert batches, "ladder must chunk into >=1 batch"
    for b in batches:
        assert b["est_minutes"] <= budget + max(r["minutes"] for r in b["rungs"])  # one rung can tip over
    # every rung appears exactly once across batches, run order preserved
    flat = [r["skill"] for b in batches for r in b["rungs"]]
    assert flat == [r["skill"] for r in LADDER]
    assert len(flat) == len(set(flat))
    # batches recorded in the quest/batch store
    assert stores.count("quests", kind="batch", status="planned") == len(batches)


def test_batch_completion_feeds_mastery(stores):
    seed_snapshot(stores)
    batches = plan_batches(stores, track_id="tr1", skill_tag="guitar", goal_type="hobby")
    b0 = batches[0]
    record_batch_completion(stores, batch_id=b0["batch_id"], user_id="u1",
                            rungs_verified=[r["skill"] for r in b0["rungs"]])
    assert stores.count("quests", kind="batch", status="completed") == 1
    ledger = stores.history("mastery", user_id="u1", cause="batch_completed")
    assert {e["skill_tag"] for e in ledger} == {r["skill"] for r in b0["rungs"]}
    assert all(e["delta"] > 0 for e in ledger)


def test_per_track_pacing_differs_by_goal(stores):
    # a level with 4x45min rungs: hobby (120/wk) must split it into 2 batches,
    # job_ready (300/wk) absorbs it in one
    long_ladder = [{"run": 1, "skill": "warm", "level": 0, "minutes": 90, "can_do": "x"}] + [
        {"run": i + 2, "skill": f"p{i}", "level": 1, "minutes": 45, "can_do": "x"} for i in range(4)]
    for gt in ("hobby", "job_ready"):
        stores.append("snapshots", {"skill_tag": "guitar", "goal_type": gt,
                                    "ladder_version": "v1", "rungs": long_ladder},
                      provenance="engine:ladder")
    hobby = plan_batches(stores, track_id="th", skill_tag="guitar", goal_type="hobby")
    job = plan_batches(stores, track_id="tj", skill_tag="guitar", goal_type="job_ready")
    assert len(hobby) > len(job)  # tighter weekly budget -> more, smaller batches
    assert max(b["est_minutes"] for b in job) > max(b["est_minutes"] for b in hobby)


def test_unknown_batch_raises(stores):
    with pytest.raises(ValueError):
        record_batch_completion(stores, batch_id="batch:nope", user_id="u1", rungs_verified=["x"])


# ---------------------------------------------------------------------------
# side quests
# ---------------------------------------------------------------------------

def test_quests_from_ladder_adjacency(stores):
    offered = Q.generate_quests(stores, user_id="u1", track_id="tr1",
                                ladder=LADDER, current_run=2)
    side = [q for q in offered if q["trigger"]["source"] == "ladder_adjacency"]
    assert len(side) >= 2, "acceptance: 2+ side quests from ladder adjacency"
    for q in side:
        assert q["deliverable"]["kind"] in Q.KINDS
        assert q["mastery"]["credit"] > 0
        assert q["expires_at"] > time.time()
        assert q["surface"] == "detours_welcome"


def test_quests_from_seeded_interest(stores):
    interests = [{"topic": "vinyl records", "signal": 0.8, "last_seen_ts": time.time(),
                  "kind": "tangent", "skills": ["g:tone"]}]
    offered = Q.generate_quests(stores, user_id="u1", track_id="tr1",
                                ladder=LADDER, current_run=1, interests=interests)
    iq = [q for q in offered if q["trigger"]["source"] == "interest"]
    assert len(iq) == 1 and iq[0]["deliverable"]["kind"] == "tangent"
    # decayed / zero-strength signals produce nothing
    stale = [{"topic": "old thing", "signal": 0.0, "last_seen_ts": time.time()}]
    assert [q for q in Q.generate_quests(stores, user_id="u1", track_id="tr2",
            ladder=LADDER, current_run=1, interests=stale) if q["trigger"]["source"] == "interest"] == []


def test_side_quest_credits_mastery_never_gates_main_path(stores):
    seed_snapshot(stores)
    batches = plan_batches(stores, track_id="tr1", skill_tag="guitar", goal_type="hobby")
    offered = Q.generate_quests(stores, user_id="u1", track_id="tr1",
                                ladder=LADDER, current_run=3)
    q = offered[0]
    Q.accept_quest(stores, quest_id=q["quest_id"], user_id="u1")
    Q.complete_quest(stores, quest_id=q["quest_id"], user_id="u1", evidence_ref="artifact:capo-chart")
    # mastery credit landed
    assert stores.count("mastery", user_id="u1", cause="side_quest_completed") >= 1
    # batch state untouched: no batch event references the quest, and every
    # planned batch is still just 'planned' — quest completion cannot gate it
    batch_events = stores.history("quests", kind="batch")
    assert all(e["status"] == "planned" for e in batch_events)
    assert not any("quest:" in str(e.get("batch_id", "")) for e in batch_events)


def test_quests_expire_when_interests_shift(stores):
    interests = [{"topic": "synths", "signal": 0.9, "last_seen_ts": time.time(),
                  "kind": "micro_project", "skills": ["g:theory"]}]
    offered = Q.generate_quests(stores, user_id="u1", track_id="tr1",
                                ladder=LADDER, current_run=1, interests=interests)
    q = next(x for x in offered if x["trigger"]["source"] == "interest")
    future = q["expires_at"] + 60
    expired = Q.expire_stale_quests(stores, now=future)
    assert q["quest_id"] in expired
    assert stores.latest("quests", quest_id=q["quest_id"], kind="side")["status"] == "expired"
    with pytest.raises(ValueError):
        Q.accept_quest(stores, quest_id=q["quest_id"], user_id="u1")
    # idempotent: expiring twice does not double-append
    assert Q.expire_stale_quests(stores, now=future) == []
    # adjacency quests are long-lived: only expired once past TTL
    aq = next(x for x in offered if x["trigger"]["source"] == "ladder_adjacency")
    assert aq["quest_id"] not in Q.expire_stale_quests(stores, now=aq["expires_at"] - 1)
    assert aq["quest_id"] in Q.expire_stale_quests(stores, now=aq["expires_at"] + 1)


def test_bad_quest_schema_rejected(stores):
    with pytest.raises(ValueError):
        Q._quest("u", "t", trigger={"source": "vibes", "evidence": "x"},
                 deliverable={"kind": "tool", "title": "y"}, mastery={}, expires_at=time.time())
    with pytest.raises(ValueError):
        Q._quest("u", "t", trigger={"source": "interest", "evidence": "x"},
                 deliverable={"kind": "ritual", "title": "y"}, mastery={}, expires_at=time.time())


# ---------------------------------------------------------------------------
# acceptance demo: batched path + 2 adjacency quests + seeded interest, end-to-end
# ---------------------------------------------------------------------------

def test_demo_track_end_to_end(stores):
    now = time.time()
    # 1. knowledge DB registry exposed (LL-02 items exist upstream)
    for i, (url, tag) in enumerate((("https://ncert.example/ch1", "g:grip"),
                                    ("https://khan.example/chords", "g:chords"))):
        stores.append("items", {"item_id": f"kb{i}", "source_url": url, "license": "CC-BY-NC",
                                "skill_tag": tag, "topic": "guitar", "capture_date": "2026-10-01",
                                "quote": "verbatim span evidence"}, provenance="scraper:demo")
    # 2. ladder snapshot (goal-relative) + batched weekly path
    seed_snapshot(stores)
    batches = plan_batches(stores, track_id="demo", skill_tag="guitar", goal_type="hobby")
    assert len(batches) >= 2
    # 3. side quests: >=2 from ladder adjacency + 1 from a seeded interest
    offered = Q.generate_quests(stores, user_id="demo-user", track_id="demo",
                                ladder=LADDER, current_run=2,
                                interests=[{"topic": "songwriting", "signal": 0.7,
                                            "last_seen_ts": now, "kind": "micro_project",
                                            "skills": ["g:theory"]}])
    adj = [q for q in offered if q["trigger"]["source"] == "ladder_adjacency"]
    ints = [q for q in offered if q["trigger"]["source"] == "interest"]
    assert len(adj) >= 2 and len(ints) == 1
    # 4. user completes a batch + one quest; verification + recap scheduled
    record_batch_completion(stores, batch_id=batches[0]["batch_id"], user_id="demo-user",
                            rungs_verified=[r["skill"] for r in batches[0]["rungs"]])
    Q.complete_quest(stores, quest_id=ints[0]["quest_id"], user_id="demo-user",
                     evidence_ref="artifact:song-draft")
    stores.append("verifications", {"user_id": "demo-user", "track_id": "demo",
                                    "skill_tag": "g:grip", "outcome": "pass",
                                    "evidence": "video:take1", "expires_at": now + 30 * 86400},
                  provenance="engine:verify")
    stores.append("recaps", {"user_id": "demo-user", "track_id": "demo", "skill_tag": "g:grip",
                             "due_at": now + 3 * 86400, "bucket": 2, "status": "scheduled"},
                  provenance="engine:recap")
    # 5. every store has counts + queryable history for the dashboard
    summary = stores.summary()
    assert all(summary[n] > 0 for n in STORE_NAMES), summary
    hist = stores.history("mastery", user_id="demo-user")
    assert sum(e["delta"] for e in hist) > 0 and len(hist) == stores.count("mastery", user_id="demo-user")
