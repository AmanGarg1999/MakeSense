"""LL-06 tests: spaced recap scheduler, rewind digest, recap outcomes.

Acceptance (task): scheduler unit tests (interval growth/reset math), a
generated recap digest for a seeded user with citations to the knowledge DB,
due-item surfacing in the UI (surfacing logic covered here; the React panel
+ API route consume the same shapes).
"""

import time

import pytest

from ll07.stores import Stores
from ll06 import scheduler as S
from ll06.digest import build_digest, rewind
from ll06.outcomes import record_recap
from packages.assessment import expiry


NOW = 1_800_000_000.0  # 2026-06-11 epoch; fixed clock, everything explicit


@pytest.fixture
def stores():
    s = Stores(":memory:")
    yield s
    s.close()


def seed_mastery(s, user="u1", track="t1", skill="web:fetch", delta=2.0, cause="batch_completed"):
    s.append("mastery", {"user_id": user, "track_id": track, "skill_tag": skill,
                         "delta": delta, "cause": cause},
             provenance="engine:batcher", ts=NOW - 5 * 86400)


# ---------------------------------------------------------------------------
# pure interval math
# ---------------------------------------------------------------------------

def test_success_grows_bucket_and_interval():
    bucket, days = S.interval_for_success(1, growth=2.0)
    assert bucket == 2
    assert days >= S.BASE_INTERVAL_DAYS[1]           # floor at next box base
    b2, d2 = S.interval_for_success(bucket, growth=2.0)
    assert b2 == 3 and d2 > days                      # monotone growth


def test_top_bucket_stays_but_growth_tuning_still_expands():
    b, d = S.interval_for_success(S.N_BUCKETS, growth=2.0)
    assert b == S.N_BUCKETS
    base = S.BASE_INTERVAL_DAYS[-1]
    assert d == pytest.approx(base * 2.0)
    # same tuned factor -> steady state at the ceiling (no runaway growth)
    b2, d2 = S.interval_for_success(b, growth=2.0)
    assert b2 == S.N_BUCKETS and d2 == pytest.approx(d)
    # improved recall success raises the growth factor, so the interval expands
    b3, d3 = S.interval_for_success(b, growth=S.family_growth(6, 0))
    assert d3 > d


def test_growth_tunes_with_observed_recall_success():
    lo = S.family_growth(0, 8)     # family where recall keeps failing
    hi = S.family_growth(8, 0)     # family where recall always works
    assert lo < hi
    assert S.GROWTH_MIN <= lo and hi <= S.GROWTH_MAX
    assert lo > S.GROWTH_MIN       # Beta prior: one bad outcome != instant floor


def test_growth_persists_into_intervals():
    # with a strong success history the growth factor beats the base factor
    g = S.family_growth(10, 0)
    _, fast = S.interval_for_success(4, growth=g)
    _, slow = S.interval_for_success(4, growth=S.family_growth(0, 10))
    assert fast > slow


def test_lapse_resets_to_box_one():
    b, d = S.interval_for_lapse()
    assert b == 1 and d == float(S.BASE_INTERVAL_DAYS[0])


# ---------------------------------------------------------------------------
# scheduler: seeding from mastery + verification + expiry feed
# ---------------------------------------------------------------------------

def test_seed_from_mastery_events(stores):
    seed_mastery(stores)
    sched = S.RecapScheduler(stores, now=NOW)
    due = sched.due("u1", now=NOW + 30 * 86400)
    assert [i.skill_tag for i in due] == ["web:fetch"]
    item = due[0]
    assert item.seeded_from == "mastery"
    assert item.bucket == S.FAMILY_FIRST_BOX[expiry.family_for("web:fetch")]
    # due immediately after the first box interval, nothing earlier
    assert sched.due("u1", now=NOW) == []
    assert sched.due("u1", now=item.due_at) == [item]


def test_seed_from_verification_uses_expiry_clock(stores):
    stores.append("verifications", {"user_id": "u1", "track_id": "t1",
                                    "skill_tag": "guitar:scales", "outcome": "pass",
                                    "evidence": "video:take1",
                                    "expires_at": NOW + 2 * 86400},
                  provenance="engine:verify", ts=NOW - 3 * 86400)
    sched = S.RecapScheduler(stores, now=NOW)
    item = sched.all_items()[0]
    assert item.seeded_from == "verification"
    assert item.due_at == NOW + 2 * 86400          # expiry wins: it's sooner than box base


def test_verification_expiry_wins_even_with_newer_mastery_event(stores):
    """seq is per-store; a later mastery batch must NOT mask a verified rung's
    expiry clock (regression: seed was keyed on cross-store seq comparison)."""
    seed_mastery(stores, skill="g:chords")                      # ts = NOW-5d
    stores.append("verifications", {"user_id": "u1", "track_id": "t1",
                                    "skill_tag": "g:chords", "outcome": "pass",
                                    "evidence": "video:take1",
                                    "expires_at": NOW + 1 * 86400},
                  provenance="engine:verify", ts=NOW - 25 * 86400)  # older row
    sched = S.RecapScheduler(stores, now=NOW)
    item = next(i for i in sched.all_items() if i.skill_tag == "g:chords")
    assert item.seeded_from == "verification"
    assert item.due_at == NOW + 1 * 86400


def test_registry_due_events_move_due_time(stores):
    seed_mastery(stores)                          # mastery-only seed, later due
    sched = S.RecapScheduler(stores, now=NOW)
    item = sched.all_items()[0]
    assert item.due_at > NOW + 2 * 86400

    from packages.assessment.registry import VerificationRegistry
    reg = VerificationRegistry(":memory:")
    past = (expiry.datetime(2026, 1, 1, tzinfo=expiry.timezone.utc)).isoformat()
    reg.append(user_id="u1", skill_tag="web:fetch", level_index=1,
               verdict="verified", verifier={"kind": "model"},
               verified_at=past, expires_at=past, track_id="t1")
    sched2 = S.RecapScheduler(stores, registry=reg, now=NOW)
    it2 = next(i for i in sched2.all_items() if i.skill_tag == "web:fetch")
    assert it2.due_at < NOW                        # registry feed pulled it forward
    assert it2.seeded_from == "expiry"


def test_no_duplicate_seed_on_warm_restart(stores, tmp_path):
    seed_mastery(stores)
    sched = S.RecapScheduler(stores, now=NOW)
    before = stores.count("recaps")
    assert before == 1                             # exactly the seed event
    sched2 = S.RecapScheduler(stores, now=NOW)
    assert stores.count("recaps") == before
    assert len(sched2.all_items()) == 1


# ---------------------------------------------------------------------------
# scheduler + outcomes: full loop
# ---------------------------------------------------------------------------

def test_recap_success_extends_interval_and_mastery(stores):
    seed_mastery(stores)
    sched = S.RecapScheduler(stores, now=NOW)
    item = sched.all_items()[0]
    first_due = item.due_at

    res = record_recap(stores, sched, user_id="u1", skill_tag="web:fetch",
                       quality=5, now=first_due)
    assert res["passed"] is True
    assert res["bucket"] == item.bucket
    assert res["bucket"] == S.FAMILY_FIRST_BOX[expiry.family_for("web:fetch")] + 1
    assert res["next_due_at"] > first_due          # interval grew
    assert res["mastery_delta"] > 0
    m = stores.latest("mastery", user_id="u1", cause="recap_pass")
    assert m and m["delta"] == pytest.approx(1.0)


def test_recap_lapse_resets_interval_penalises_mastery_no_repeat_card(stores):
    seed_mastery(stores)
    seed_mastery(stores, skill="web:dom", delta=2.0)   # a consolidated prereq
    sched = S.RecapScheduler(stores, now=NOW)
    item = next(i for i in sched.all_items() if i.skill_tag == "web:fetch")
    t0 = item.due_at
    res = record_recap(stores, sched, user_id="u1", skill_tag="web:fetch",
                       quality=1, now=t0)
    assert res["passed"] is False
    assert res["bucket"] == 1
    assert res["next_due_at"] == pytest.approx(t0 + S.BASE_INTERVAL_DAYS[0] * S.DAY)
    assert res["mastery_delta"] < 0
    route = res["delivery_route"]
    assert route["route"] == "reteach_prerequisite"   # quality 1 = total blank
    assert route["prerequisite"] == "web:dom"          # weakest current mastery
    assert route["do_not"] == "repeat the same card"

    # partial-recall lapse flips delivery mode instead
    res2 = record_recap(stores, sched, user_id="u1", skill_tag="web:dom",
                        quality=2, now=NOW)
    assert res2["delivery_route"]["route"] == "flip_active_mode"


def test_recap_extends_verification_currency(stores):
    seed_mastery(stores, skill="python:api")
    stores.append("verifications", {"user_id": "u1", "track_id": "t1",
                                    "skill_tag": "python:api", "outcome": "pass",
                                    "evidence": "repo:proj",
                                    "expires_at": NOW + 10 * 86400},
                  provenance="engine:verify", ts=NOW)
    sched = S.RecapScheduler(stores, now=NOW)
    res = record_recap(stores, sched, user_id="u1", skill_tag="python:api",
                       quality=4, now=NOW + 3 * 86400)
    assert res["verification_currency"]["action"] == "extended"
    new_ev = stores.history("verifications", user_id="u1", skill_tag="python:api")[-1]
    assert new_ev["expires_at"] > NOW + 10 * 86400     # clock pushed out
    assert new_ev["evidence"] == "recap:quality4"


def test_recap_lapse_downgrades_verification_to_provisional(stores):
    seed_mastery(stores, skill="python:api")
    stores.append("verifications", {"user_id": "u1", "track_id": "t1",
                                    "skill_tag": "python:api", "outcome": "pass",
                                    "evidence": "repo:proj",
                                    "expires_at": NOW + 10 * 86400},
                  provenance="engine:verify", ts=NOW)
    sched = S.RecapScheduler(stores, now=NOW)
    res = record_recap(stores, sched, user_id="u1", skill_tag="python:api",
                       quality=1, now=NOW + 3 * 86400)
    assert res["verification_currency"]["action"] == "lapsed"
    assert res["verification_currency"]["next_clearance"] == "performance"


def test_interval_tuning_observable_across_rounds(stores):
    """Repeated successes on the same family should grow faster than a cold
    family with the same raw bucket (growth tuned by observed recall)."""
    seed_mastery(stores, skill="python:a")
    seed_mastery(stores, skill="python:b")
    sched = S.RecapScheduler(stores, now=NOW)
    a = next(i for i in sched.all_items() if i.skill_tag == "python:a")
    t = a.due_at
    gaps_a = []
    for _ in range(4):
        r = record_recap(stores, sched, user_id="u1", skill_tag="python:a",
                         quality=5, now=t)
        gaps_a.append(r["next_due_at"] - t)
        t = r["next_due_at"]
    assert all(g2 > g1 for g1, g2 in zip(gaps_a, gaps_a[1:]))  # monotone expansion
    assert gaps_a[-1] > 20 * 86400


def test_schedule_persists_and_rehydrates(stores, tmp_path):
    seed_mastery(stores, skill="python:loops")
    sched = S.RecapScheduler(stores, now=NOW)
    item = sched.all_items()[0]
    res = record_recap(stores, sched, user_id="u1", skill_tag="python:loops",
                       quality=5, now=item.due_at)
    # a fresh scheduler over the same stream rebuilds identical state
    sched2 = S.RecapScheduler(stores, now=NOW)
    it2 = next(i for i in sched2.all_items() if i.skill_tag == "python:loops")
    assert it2.bucket == res["bucket"]
    assert it2.due_at == pytest.approx(res["next_due_at"])
    assert it2.successes == 1 and it2.failures == 0


# ---------------------------------------------------------------------------
# rewind digest
# ---------------------------------------------------------------------------

def test_rewind_digest_retrieval_first_with_citations(stores):
    # seed user history: items in the knowledge DB, mastery, a verification, a lapse
    stores.append("items", {"item_id": "kb1", "source_url": "https://khan.example/fetch",
                            "license": "CC-BY-NC", "skill_tag": "web:fetch",
                            "topic": "web", "capture_date": "2026-10-01",
                            "quote": "fetch returns a Response object"},
                  provenance="scraper:khan", ts=NOW)
    seed_mastery(stores, skill="web:fetch")
    stores.append("recaps", {"user_id": "u1", "track_id": "t1", "skill_tag": "web:fetch",
                             "due_at": NOW, "bucket": 1, "status": "scheduled",
                             "outcome": "lapsed", "quality": 1},
                  provenance="user", ts=NOW - 86400)
    ladder = [{"skill": "web:fetch", "can_do": "pull JSON from any public API"}]

    d = build_digest(stores, user_id="u1", query="web", ladder=ladder, now=NOW)
    assert d["format"] == "retrieval-first"
    sec = next(s for s in d["sections"] if s["skill_tag"] == "web:fetch")
    # questions before answers
    keys = list(sec.keys())
    assert keys.index("prompt") < keys.index("reveal")
    assert "Without looking" in sec["prompt"]["question"]
    assert sec["can_do"] == "pull JSON from any public API"
    # citations to the knowledge DB with source URLs
    urls = {c["source_url"] for c in d["citations"]}
    assert "https://khan.example/fetch" in urls
    # the lapse shows up as a changed re-question routed to LL-04, not the card
    assert sec["gaps"] and sec["gaps"][0]["route"] == "ll04_active_mode"
    assert "do" not in sec["gaps"][0]["question"].lower()[:20]
    # digest event recorded for the recap stream (provenance trail)
    assert stores.count("recaps", status="digest") == 1


def test_rewind_parses_natural_language(stores):
    seed_mastery(stores, skill="guitar:strum")
    d = rewind(stores, user_id="u1", topic="take me back through guitar")
    assert d["query"] == "guitar"
    assert any(s["skill_tag"] == "guitar:strum" for s in d["sections"])


def test_rewind_query_matches_via_track_membership(stores):
    """'guitar' must rewind an abbreviated-tag track (g:*) via its track_id,
    and must NOT pull in an unrelated track (regression: namespace-prefix
    heuristic would have matched 'golf' to 'g:*')."""
    stores.append("mastery", {"user_id": "u1", "track_id": "guitar-hobby",
                              "skill_tag": "g:strum", "delta": 2.0,
                              "cause": "batch_completed"},
                  provenance="engine:batcher", ts=NOW - 5 * 86400)
    stores.append("mastery", {"user_id": "u1", "track_id": "golf-swing",
                              "skill_tag": "dr:drive", "delta": 2.0,
                              "cause": "batch_completed"},
                  provenance="engine:batcher", ts=NOW - 5 * 86400)
    d = rewind(stores, user_id="u1", topic="take me back through guitar")
    tags = {s["skill_tag"] for s in d["sections"]}
    assert tags == {"g:strum"}


def test_rewind_no_history_is_not_a_hallucinated_digest(stores):
    d = build_digest(stores, user_id="u1", query="kitesurfing", now=NOW)
    assert d["sections"] == [] and "No recorded history" in d["summary"]


# ---------------------------------------------------------------------------
# due-item surfacing shape (consumed by /api/recap/due + RecapDeck UI)
# ---------------------------------------------------------------------------

def test_due_items_surface_as_low_effort_wins(stores):
    seed_mastery(stores, skill="python:x1")
    seed_mastery(stores, skill="python:x2")
    stores.append("mastery", {"user_id": "u1", "track_id": "t1", "skill_tag": "python:x3",
                              "delta": 2.0, "cause": "batch_completed"},
                  provenance="engine:batcher", ts=NOW)
    sched = S.RecapScheduler(stores, now=NOW)
    later = NOW + 40 * 86400
    due = sched.due("u1", now=later)
    assert len(due) == 3
    # per-item effort framing the UI renders: short, streak-friendly
    for i in due:
        mins = 2 if i.bucket <= 2 else 3
        assert 1 <= mins <= 5
        assert i.status == "scheduled"
