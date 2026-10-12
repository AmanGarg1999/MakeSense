"""LL-09a acceptance tests: multi-level learning pathways schema + API.

Spins up the real FastAPI app (server.main) against a postgres DB via
TestClient (lifespan runs init_db, which applies migration 009), then proves:

1. Migration 009 applies clean on an existing DB (idempotent re-run).
2. Schema shape: CHECK constraints on the canonical level enum.
3. Seeded level_metadata for all 6 levels.
4. Pathway CRUD + GET /pathways?level= filter.
5. Curriculum ordering + PUT replace.
6. Transcript upsert + credential validation.
7. Coach Engine helper get_active_pathway returns pathway+curriculum+metadata.
8. Invalid level / malformed UUID rejected with 4xx.

Required env:
  DATABASE_URL=postgresql://makesense:***@localhost:55447/makesense
"""

import asyncio
import os
import time
from pathlib import Path

import pytest

MIGRATION_009 = Path(__file__).resolve().parent.parent / "server" / "migrations" / "009_learning_pathways.sql"

CANONICAL_LEVELS = ["micro", "certificate", "undergrad", "masters", "phd", "mba"]

PID = os.getpid()
USER_A = 930_000 + (PID % 50_000)


def hdr(user_id: int):
    return {"X-User-ID": str(user_id)}


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from server.main import app

    with TestClient(app) as c:
        yield c


def _dsn():
    return os.environ["DATABASE_URL"]


@pytest.fixture(autouse=True)
def test_users(client):
    """Ensure the test user exists (pathways FK -> users.id ON DELETE CASCADE)."""
    import asyncpg

    async def _up():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute(
                "INSERT INTO users (id, email) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING",
                USER_A, f"ll09a-{time.time_ns()}@test.local",
            )
        finally:
            await conn.close()

    asyncio.run(_up())
    yield

    async def _clean():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute("DELETE FROM users WHERE id = $1", USER_A)
        finally:
            await conn.close()

    asyncio.run(_clean())


# ---------------------------------------------------------------------------
# 1-3. Migration + seed
# ---------------------------------------------------------------------------

def test_migration_009_idempotent_rerun():
    """Applying 009 twice on an already-migrated DB must not error."""
    import asyncpg

    sql = MIGRATION_009.read_text(encoding="utf-8")

    async def _run():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute(sql)
            await conn.execute(sql)  # second pass must be a no-op
        finally:
            await conn.close()

    asyncio.run(_run())


def test_level_metadata_seeded_all_six_levels(client):
    r = client.get("/api/pathways/levels")
    assert r.status_code == 200, r.text
    rows = r.json()
    levels = {row["level"] for row in rows}
    assert levels == set(CANONICAL_LEVELS)
    for row in rows:
        assert row["typical_duration_weeks"] > 0
        assert row["recap_interval_days"] > 0
        assert row["credit_system"] and row["assessment_type"] and row["mentor_model"]


def test_level_check_constraint_rejects_unknown_level():
    import asyncpg

    async def _run():
        conn = await asyncpg.connect(_dsn())
        try:
            with pytest.raises(asyncpg.exceptions.CheckViolationError):
                await conn.execute(
                    "INSERT INTO learning_pathways (user_id, level) VALUES ($1, 'highschool')",
                    USER_A,
                )
        finally:
            await conn.close()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 4. CRUD + level filter
# ---------------------------------------------------------------------------

def _create(client, level, **kw):
    body = {"level": level, "title": kw.get("title", f"{level} pathway")}
    if "curriculum" in kw:
        body["curriculum"] = kw["curriculum"]
    if "target_completion" in kw:
        body["target_completion"] = kw["target_completion"]
    return client.post("/api/pathways", json=body, headers=hdr(USER_A))


def test_create_read_filter_update_delete(client):
    created = {}
    for level in CANONICAL_LEVELS:
        r = _create(client, level)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["level"] == level
        assert p["status"] == "active"
        assert p["user_id"] == USER_A
        created[level] = p["id"]

    # read back each
    for level, pid in created.items():
        r = client.get(f"/api/pathways/{pid}", headers=hdr(USER_A))
        assert r.status_code == 200
        assert r.json()["level"] == level

    # GET /pathways?level=masters returns only masters pathways
    r = client.get("/api/pathways?level=masters", headers=hdr(USER_A))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1 and rows[0]["id"] == created["masters"]

    # update: pause the micro pathway
    r = client.patch(f"/api/pathways/{created['micro']}",
                     json={"status": "paused"}, headers=hdr(USER_A))
    assert r.status_code == 200 and r.json()["status"] == "paused"

    # delete the mba pathway
    r = client.delete(f"/api/pathways/{created['mba']}", headers=hdr(USER_A))
    assert r.status_code == 200 and r.json()["deleted"] is True
    r = client.get(f"/api/pathways/{created['mba']}", headers=hdr(USER_A))
    assert r.status_code == 404

    # invalid level rejected by pydantic pattern (422)
    r = _create(client, "kindergarten")
    assert r.status_code == 422

    # malformed uuid -> 422, unknown-but-valid uuid -> 404
    assert client.get("/api/pathways/not-a-uuid", headers=hdr(USER_A)).status_code == 422
    import uuid
    assert client.get(f"/api/pathways/{uuid.uuid4()}", headers=hdr(USER_A)).status_code == 404


def test_pathways_scoped_to_owner(client):
    other = USER_A + 5_000_000
    r = _create(client, "phd")
    assert r.status_code == 200
    pid = r.json()["id"]
    # a different user must not see it
    r = client.get(f"/api/pathways/{pid}", headers=hdr(other))
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 5. Curriculum
# ---------------------------------------------------------------------------

def test_curriculum_ordering_and_replace(client):
    packs = [
        {"content_pack_id": "pack-b", "sequence": 1, "required": True, "credits": 3},
        {"content_pack_id": "pack-a", "sequence": 0, "required": True, "credits": 4},
        {"content_pack_id": "pack-c", "sequence": 2, "required": False, "credits": 0},
    ]
    r = _create(client, "certificate", curriculum=packs)
    assert r.status_code == 200
    pid = r.json()["id"]
    seq = [(c["content_pack_id"], c["credits"]) for c in r.json()["curriculum"]]
    assert seq == [("pack-a", 4), ("pack-b", 3), ("pack-c", 0)]

    r = client.put(f"/api/pathways/{pid}/curriculum", headers=hdr(USER_A),
                    json={"items": [{"content_pack_id": "pack-x", "sequence": 0}]})
    assert r.status_code == 200
    assert [c["content_pack_id"] for c in r.json()["curriculum"]] == ["pack-x"]


# ---------------------------------------------------------------------------
# 6. Transcript
# ---------------------------------------------------------------------------

def test_transcript_upsert_and_credential_validation(client):
    r = _create(client, "undergrad")
    pid = r.json()["id"]

    r = client.post(f"/api/pathways/{pid}/transcript", headers=hdr(USER_A), json={
        "content_pack_id": "pack-101", "mastery_score": 0.82,
    })
    assert r.status_code == 200
    assert r.json()["mastery_score"] == pytest.approx(0.82)
    assert r.json()["credential_issued"] is False

    # upsert same pack
    r = client.post(f"/api/pathways/{pid}/transcript", headers=hdr(USER_A), json={
        "content_pack_id": "pack-101", "mastery_score": 0.95,
        "credential_issued": True, "credential_type": "degree-part",
    })
    assert r.status_code == 200 and r.json()["mastery_score"] == pytest.approx(0.95)

    r = client.get(f"/api/pathways/{pid}/transcript", headers=hdr(USER_A))
    assert len(r.json()) == 1

    # credential_issued without credential_type -> 422
    r = client.post(f"/api/pathways/{pid}/transcript", headers=hdr(USER_A), json={
        "content_pack_id": "pack-102", "mastery_score": 1.0, "credential_issued": True,
    })
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 7. Coach Engine helper
# ---------------------------------------------------------------------------

def test_get_active_pathway_helper(client):
    import asyncpg
    from server.pathway_service import get_active_pathway

    packs = [{"content_pack_id": "m-p1", "sequence": 0},
             {"content_pack_id": "m-p2", "sequence": 1, "required": False}]
    r = _create(client, "micro", curriculum=packs)
    assert r.status_code == 200

    async def _read():
        conn = await asyncpg.connect(_dsn())
        try:
            pool = await asyncpg.create_pool(_dsn())
            try:
                return await get_active_pathway(pool, USER_A)
            finally:
                await pool.close()
        finally:
            await conn.close()

    active = asyncio.run(_read())
    assert active is not None
    assert active["level"] == "micro"
    assert active["status"] == "active"
    assert [c["content_pack_id"] for c in active["curriculum"]] == ["m-p1", "m-p2"]
    assert active["level_metadata"]["level"] == "micro"
    assert active["level_metadata"]["recap_interval_days"] > 0

    # same shape via HTTP for the Coach Engine's REST path
    r = client.get("/api/pathways/active", headers=hdr(USER_A))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(active["id"])
    assert body["level_metadata"]["typical_duration_weeks"] == \
        active["level_metadata"]["typical_duration_weeks"]
