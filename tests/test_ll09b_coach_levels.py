"""LL-09b acceptance tests: Coach Engine level-aware pedagogy switching.

Core (no DB): unit tests proving micro vs a degree level produce DIFFERENT
coach behavior from the SAME input state — action id, cycle, feedback
timing, radar granularity, recap multiplier, challenge params.

Integration (needs DATABASE_URL, same convention as LL-09a tests): the
/api/coach routes resolve the caller's level from their active pathway
(LL-09a get_active_pathway) and the DB level_metadata row folds over the
code pedagogy template.

  DATABASE_URL=postgresql://makesense:***@localhost:55451/makesense
"""

import asyncio
import os
import time
from pathlib import Path

import pytest

from server.pathway_service import PATHWAY_LEVELS
from ll09b.coach_engine import CoachEngine, CoachAction
from ll09b.level_config import (
    DEGREE_LEVELS,
    LEVEL_CONFIGS,
    level_config_for,
    recap_multiplier_for,
)

CANONICAL_LEVELS = ["micro", "certificate", "undergrad", "masters", "phd", "mba"]

PID = os.getpid()
USER_A = 940_000 + (PID % 50_000)


# ---------------------------------------------------------------------------
# Shared "same input state" fixtures (the acceptance surface)
# ---------------------------------------------------------------------------

STATE_FAILING = {
    "skill": "music:barre_chords",
    "skills": ["music:barre_chords", "music:strum", "music:rhythm"],
    "attempts": 1,
    "correct": False,
    "mastered": ["music:strum"],
    "session_minutes": 45.0,
}

STATE_SUCCEEDING = {**STATE_FAILING, "attempts": 0, "correct": True}


def engine_for(level: str) -> CoachEngine:
    e = CoachEngine()
    e.setLearningLevel(level)
    return e


# ---------------------------------------------------------------------------
# 1. Config integrity
# ---------------------------------------------------------------------------

def test_configs_cover_canonical_enum_exactly():
    assert set(LEVEL_CONFIGS) == set(CANONICAL_LEVELS)
    assert LEVEL_CONFIGS.keys() != set(DEGREE_LEVELS)  # micro excluded from degrees


def test_level_config_isolated_copy():
    cfg = level_config_for("micro")
    cfg["cycle"].append("tampered")
    assert "tampered" not in level_config_for("micro")["cycle"]


def test_unknown_level_rejected():
    with pytest.raises(KeyError):
        CoachEngine().setLearningLevel("wat")


def test_set_learning_level_aliases_equivalent():
    e = CoachEngine()
    assert e.setLearningLevel("phd") == e.set_learning_level("phd")
    assert e.level == "phd"


# ---------------------------------------------------------------------------
# 2. ACCEPTANCE: same state, micro vs each degree level -> different behavior
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("degree", DEGREE_LEVELS)
@pytest.mark.parametrize("state", [STATE_FAILING, STATE_SUCCEEDING], ids=["failing", "succeeding"])
def test_micro_vs_degree_diverge_same_state(degree, state):
    micro = engine_for("micro").coach_action(state)
    prog = engine_for(degree).coach_action(state)

    assert micro.action != prog.action, (
        f"{degree} and micro produced identical action '{micro.action}'"
    )
    # micro: rapid cycle + immediate feedback + NO long-term tracking
    assert micro.payload["feedback"] == "immediate"
    assert micro.payload["track_history"] is False
    assert micro.payload.get("instruments") is None
    # degree: program instruments engaged + long-term tracking on
    assert prog.payload["track_history"] is True
    assert prog.payload["instruments"] == LEVEL_CONFIGS[degree]["instruments"]
    assert prog.payload["long_term_instrument"] in LEVEL_CONFIGS[degree]["instruments"]


def test_micro_rapid_cycle_follows_question_attempt_hint_retry():
    e = engine_for("micro")
    actions = [e.coach_action({**STATE_FAILING, "attempts": n}).action for n in range(4)]
    assert actions == ["micro_question", "micro_attempt", "micro_hint", "micro_retry"]
    # success exits the cycle into the next concept
    assert e.coach_action(STATE_SUCCEEDING).action == "advance_concept"


def test_degree_cycle_rotates_through_level_template():
    e = engine_for("undergrad")
    a0 = e.coach_action(STATE_FAILING)
    # feeding last_action back advances the position deterministically
    a1 = e.coach_action({**STATE_FAILING, "last_action": a0.action})
    cycle = LEVEL_CONFIGS["undergrad"]["cycle"]
    assert a0.payload["stage"] in cycle
    assert a1.payload["stage"] == cycle[(cycle.index(a0.payload["stage"]) + 1) % len(cycle)]


# ---------------------------------------------------------------------------
# 3. Radar granularity (mk-027 contract)
# ---------------------------------------------------------------------------

def test_radar_micro_atomic_degree_clustered():
    micro = engine_for("micro").radar_update(STATE_FAILING)
    cert = engine_for("certificate").radar_update(STATE_FAILING)

    assert micro["granularity"] == "atomic_skills"
    assert {n["id"] for n in micro["nodes"]} == set(STATE_FAILING["skills"])

    assert cert["granularity"] == "competency_clusters"
    (node,) = cert["nodes"]                      # all three are music:*
    assert node["id"] == "cluster:music"
    assert set(node["members"]) == set(STATE_FAILING["skills"])
    assert node["mastered"] is False             # not all members mastered


# ---------------------------------------------------------------------------
# 4. Spaced recap multiplier (LL-06 contract; additive)
# ---------------------------------------------------------------------------

def test_recap_multiplier_scales_micro_to_phd():
    assert recap_multiplier_for("micro") < recap_multiplier_for("certificate")
    assert recap_multiplier_for("certificate") <= recap_multiplier_for("undergrad")
    assert recap_multiplier_for("undergrad") < recap_multiplier_for("phd")
    plan_m = engine_for("micro").recap_plan(STATE_FAILING)
    plan_p = engine_for("phd").recap_plan(STATE_FAILING)
    assert plan_m["interval_multiplier"] != plan_p["interval_multiplier"]
    assert plan_m["cadence_label"] == "daily-scale"
    assert plan_p["cadence_label"] == "program-scale"


# ---------------------------------------------------------------------------
# 5. Challenge-generator hook (LL-07 contract; additive)
# ---------------------------------------------------------------------------

def test_challenge_params_level_derived_and_additive():
    m = engine_for("micro").challenge_request(STATE_FAILING)
    p = engine_for("phd").challenge_request(STATE_FAILING)
    assert m["single_concept"] is True and p["single_concept"] is False
    assert m["difficulty_target"] < p["difficulty_target"]
    assert m["cadence_minutes"] < p["cadence_minutes"]
    assert m["level"] == "micro" and p["level"] == "phd"


def test_instrument_rotation_micro_none():
    assert engine_for("micro").instrument_for(STATE_FAILING) is None
    e = engine_for("undergrad")
    n = len(LEVEL_CONFIGS["undergrad"]["instruments"])
    ins = [e.instrument_for({**STATE_FAILING, "session_minutes": 30 * i})
           for i in range(n)]
    assert len(set(ins)) == n          # full deterministic rotation
    assert e.instrument_for({**STATE_FAILING, "session_minutes": 30 * n}) == ins[0]  # wraps


# ---------------------------------------------------------------------------
# 6. API integration (active-pathway level resolution + level_metadata fold)
# ---------------------------------------------------------------------------

HAS_DB = bool(os.environ.get("DATABASE_URL"))


@pytest.fixture(scope="module")
def client():
    if not HAS_DB:
        pytest.skip("DATABASE_URL not set")
    from fastapi.testclient import TestClient
    from server.main import app

    with TestClient(app) as c:
        yield c


def _dsn():
    return os.environ["DATABASE_URL"]


def hdr(user_id: int):
    return {"X-User-ID": str(user_id)}


@pytest.fixture()
def pathway_micro_and_masters(client):
    """Create one micro + one masters pathway for USER_A; return ids."""
    import asyncpg

    async def _ensure_user():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute(
                "INSERT INTO users (id, email) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING",
                USER_A, f"ll09b-{time.time_ns()}@test.local",
            )
        finally:
            await conn.close()

    asyncio.run(_ensure_user())
    r = client.post(
        "/api/pathways",
        json={"level": "micro", "title": "Micro: barre chords week"},
        headers=hdr(USER_A),
    )
    assert r.status_code == 200, r.text
    ids = {"micro": r.json()["id"]}
    r = client.post(
        "/api/pathways",
        json={"level": "masters", "title": "Masters: thesis track"},
        headers=hdr(USER_A),
    )
    assert r.status_code == 200, r.text
    ids["masters"] = r.json()["id"]
    yield ids
    asyncio.run(_cleanup())


async def _cleanup():
    import asyncpg
    conn = await asyncpg.connect(_dsn())
    try:
        await conn.execute("DELETE FROM users WHERE id = $1", USER_A)
    finally:
        await conn.close()


@pytest.mark.skipif(not HAS_DB, reason="DATABASE_URL not set")
def test_coach_levels_endpoint_lists_canonical(client):
    r = client.get("/api/coach/levels")
    assert r.status_code == 200
    assert {row["level"] for row in r.json()} == set(CANONICAL_LEVELS)


@pytest.mark.skipif(not HAS_DB, reason="DATABASE_URL not set")
def test_coach_action_level_override_diverges(client):
    """Same POST state, only the override differs -> different behavior."""
    body = {"state": STATE_FAILING}
    r_m = client.post("/api/coach/action", headers=hdr(USER_A),
                      json={**body, "level": "micro"})
    r_p = client.post("/api/coach/action", headers=hdr(USER_A),
                      json={**body, "level": "phd"})
    assert r_m.status_code == r_p.status_code == 200
    jm, jp = r_m.json(), r_p.json()
    assert jm["action"] != jp["action"]
    assert jm["payload"]["track_history"] is False
    assert jp["payload"]["track_history"] is True
    # DB facts folded over pedagogy (level_metadata row present on degree)
    assert jp["payload"].get("recap_plan", {}).get("metadata_recap_days") == 60
    assert jm["challenge_params"]["difficulty_target"] < jp["challenge_params"]["difficulty_target"]


@pytest.mark.skipif(not HAS_DB, reason="DATABASE_URL not set")
def test_coach_resolves_level_from_active_pathway(client, pathway_micro_and_masters):
    """With a masters pathway started LAST, /api/coach/action (no override)
    must pick up the masters pedagogy via get_active_pathway."""
    # both pathways are active; the most recently started wins (LL-09a rule)
    r = client.post("/api/coach/action", headers=hdr(USER_A),
                    json={"state": STATE_FAILING})
    assert r.status_code == 200
    j = r.json()
    assert j["level"] == "masters"
    assert j["action"].startswith("masters_")
    assert j["payload"]["feedback"] == LEVEL_CONFIGS["masters"]["feedback"]
