"""LL-02 acceptance tests: multi-track state + goal-relative skill ladders.

Spins up the real FastAPI app (server.main) against a postgres dev DB via
TestClient (lifespan runs init_db + ladder_service wiring), then proves the
two acceptance criteria from card t_48c67ccb:

1. A user can run 2 concurrent tracks with INDEPENDENT mastery state.
2. Ladder instantiation is goal-relative: the same skill_tag with
   hobby vs job-ready goal_type produces different rungs and can-do lists.

Override the user store via `test_users` autouse fixture so tests never
depend on seeded rows (the app has no auth layer; user ids come from the
X-User-ID header and the service defaults to 1).

Required env (set by conftest or caller):
  DATABASE_URL=postgresql://makesense:***@localhost:55442/makesense
"""

import asyncio
import os
import time
from pathlib import Path

import pytest

PID = os.getpid()
USER_A = 900_000 + (PID % 50_000)
USER_B = USER_A + 1_000_000


def hdr(user_id: int):
    return {"X-User-ID": str(user_id)}


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from server.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def test_users(client):
    """Ensure the two test users exist (tracks FK -> users.id ON DELETE CASCADE).

    Uses a short-lived dedicated connection instead of the app pool: the pool's
    connections are bound to the TestClient portal's event loop, which is closed
    by the time this fixture body runs on the main thread.
    """
    import asyncpg

    dsn = os.environ["DATABASE_URL"]

    async def _up():
        conn = await asyncpg.connect(dsn)
        try:
            for uid, email in ((USER_A, f"ll02a-{time.time_ns()}@test.local"),
                               (USER_B, f"ll02b-{time.time_ns()}@test.local")):
                await conn.execute(
                    "INSERT INTO users (id, email) VALUES ($1, $2) "
                    "ON CONFLICT (id) DO NOTHING",
                    uid, email,
                )
        finally:
            await conn.close()

    asyncio.run(_up())
    yield
    # teardown: cascade removes their tracks/sessions/checkpoints
    async def _clean():
        conn = await asyncpg.connect(dsn)
        try:
            await conn.execute("DELETE FROM users WHERE id = ANY($1::bigint[])",
                               [USER_A, USER_B])
        finally:
            await conn.close()

    asyncio.run(_clean())


def _create_track(client, user_id, skill_tag, goal_type, goal_level="novice"):
    r = client.post(
        "/api/tracks",
        json={"skill_graph_ref": f"kg:{skill_tag}", "skill_tag": skill_tag,
              "goal_level": goal_level, "goal_type": goal_type},
        headers=hdr(user_id),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_create_and_list_two_concurrent_tracks(client):
    t1 = _create_track(client, USER_A, "personal_finance", "hobby")
    t2 = _create_track(client, USER_A, "personal_finance", "job-ready")

    assert t1["id"] != t2["id"]
    assert t1["status"] == "active" and t2["status"] == "active"

    listing = client.get("/api/tracks", headers=hdr(USER_A)).json()
    ids = {t["id"] for t in listing}
    assert {t1["id"], t2["id"]} <= ids
    goal_types = {t["goal_type"] for t in listing}
    assert {"hobby", "job-ready"} <= goal_types


def test_mastery_state_is_independent_per_track(client):
    t1 = _create_track(client, USER_A, "personal_finance", "hobby")
    t2 = _create_track(client, USER_A, "personal_finance", "job-ready")

    # mutate track 1 only
    mv1 = t1["mastery_vector"]
    first_key = next(iter(mv1))
    mv1[first_key]["score"] = 42
    p = client.patch(f"/api/tracks/{t1['id']}",
                     json={"mastery_vector": mv1, "progress_pct": 37.5},
                     headers=hdr(USER_A))
    assert p.status_code == 200
    assert p.json()["mastery_vector"][first_key]["score"] == 42

    # track 2 untouched
    got2 = client.get(f"/api/tracks/{t2['id']}", headers=hdr(USER_A)).json()
    assert all(v["score"] == 0 for v in got2["mastery_vector"].values())
    assert got2["progress_pct"] == 0.0


def test_tracks_are_per_user_isolated(client):
    ta = _create_track(client, USER_A, "personal_finance", "hobby")
    # other user cannot see or touch it
    assert client.get(f"/api/tracks/{ta['id']}", headers=hdr(USER_B)).status_code == 403
    listing_b = client.get("/api/tracks", headers=hdr(USER_B)).json()
    assert ta["id"] not in {t["id"] for t in listing_b}


def test_goal_relative_ladder_instantiation(client):
    hobby = client.post("/api/tracks/ladders/personal_finance/hobby/instantiate").json()
    job = client.post("/api/tracks/ladders/personal_finance/job-ready/instantiate").json()

    assert hobby["total_rungs"] == 4 and job["total_rungs"] == 4

    def can_do(ladder):
        return [c for rung in ladder["ladder"]
                for ss in rung["sub_skills"]
                for c in ss["can_do_statements"]]

    hc, jc = can_do(hobby), can_do(job)
    assert len(hc) > 0, "hobby ladder produced no can-do list"
    assert len(jc) > 0, "job-ready ladder produced no can-do list"
    # goal-relative: the can-do lists must differ
    assert set(hc) != set(jc)

    # mastery vector template differs between goal types
    assert set(hobby["mastery_vector"]) != set(job["mastery_vector"])


def test_ladder_detail_and_available_ladders(client):
    ladders = client.get("/api/tracks/ladders/available").json()
    tags = {(l["skill_tag"], l["goal_type"]) for l in ladders}
    assert ("personal_finance", "hobby") in tags
    assert ("personal_finance", "job-ready") in tags

    detail = client.get("/api/tracks/ladders/personal_finance/job-ready").json()
    assert [r["level_name"] for r in detail["rungs"]] == \
        ["Novice", "Competent", "Proficient", "Expert"]


def test_unknown_ladder_404(client):
    r = client.post("/api/tracks/ladders/nonexistent_skill_xyz/hobby/instantiate")
    assert r.status_code == 404


def test_track_status_lifecycle(client):
    t = _create_track(client, USER_A, "personal_finance", "hobby")
    tid = t["id"]

    assert client.patch(f"/api/tracks/{tid}", json={"status": "paused"},
                        headers=hdr(USER_A)).json()["status"] == "paused"
    assert client.patch(f"/api/tracks/{tid}", json={"status": "done"},
                        headers=hdr(USER_A)).json()["status"] == "done"

    only_active = client.get("/api/tracks?status=active", headers=hdr(USER_A)).json()
    assert tid not in {x["id"] for x in only_active}

    d = client.delete(f"/api/tracks/{tid}", headers=hdr(USER_A))
    assert d.status_code == 200 and d.json()["success"] is True


def test_session_recording_advances_activity(client):
    t = _create_track(client, USER_A, "personal_finance", "hobby")
    r = client.post(f"/api/tracks/{t['id']}/sessions",
                    json={"session_type": "practice", "duration_seconds": 1200,
                          "nodes_completed": 3, "mastery_deltas": {"Budgeting Basics": 0.2}},
                    headers=hdr(USER_A))
    assert r.status_code == 200
    assert "session_id" in r.json()


def test_dashboard_aggregates_tracks(client):
    _create_track(client, USER_A, "personal_finance", "hobby")
    _create_track(client, USER_A, "personal_finance", "job-ready")
    d = client.get("/api/tracks/dashboard", headers=hdr(USER_A)).json()
    assert "tracks" in d and "total_active_tracks" in d
    assert d["total_active_tracks"] >= 2


def test_verification_advances_rung(client):
    t = _create_track(client, USER_A, "personal_finance", "hobby")
    tid = t["id"]
    assert t["current_ladder_rung"] == 0

    r = client.post(
        f"/api/tracks/{tid}/verify/0",
        json={"evidence": [{"type": "quiz", "ref": "q:demo"}],
              "rubric_scores": {"accuracy": {"score": 85},
                                "completeness": {"score": 90}},
              "verifier": "model"},
        headers=hdr(USER_A),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["passed"] is True
    assert body["next_rung"] == 1

    got = client.get(f"/api/tracks/{tid}", headers=hdr(USER_A)).json()
    assert got["current_ladder_rung"] == 1
    assert got["progress_pct"] == 50.0
    # a checkpoint for the new rung exists
    statuses = {cp["level_index"]: cp["status"] for cp in got["verification_checkpoints"]}
    assert statuses.get(0) == "verified"
    assert statuses.get(1) == "pending"


def test_verify_wrong_rung_rejected(client):
    t = _create_track(client, USER_A, "personal_finance", "hobby")
    r = client.post(
        f"/api/tracks/{t['id']}/verify/2",
        json={"evidence": [], "rubric_scores": {"x": {"score": 99}}, "verifier": "model"},
        headers=hdr(USER_A),
    )
    assert r.status_code == 400


def test_migration_006_idempotent_rerun(client):
    """The salvage fixed migration 006 to re-run clean (helper fn + upsert)."""
    import asyncpg

    sql = (Path(__file__).parent.parent / "server" / "migrations"
           / "006_skill_tracks_and_ladders.sql").read_text()

    async def _run():
        conn = await asyncpg.connect(os.environ["DATABASE_URL"])
        try:
            await conn.execute(sql)
            n = await conn.fetchval("SELECT count(*) FROM skill_ladders")
        finally:
            await conn.close()
        return n

    n = asyncio.run(_run())
    assert n >= 16  # seed ladders intact after second apply
    # app still functional after the rerun
    assert client.get("/api/tracks", headers=hdr(USER_A)).status_code == 200
