"""LL-09c Cloud API acceptance tests (mk-017) against the LL-09a tables.

Runs the real FastAPI app (lifespan -> init_db applies migration 010) against
a postgres DB, then proves:
1. GET  /api/packs?level=            — level filter, back-compat defaults
2. GET  /api/packs?prereq_satisfied= — transcript mastery gating
3. POST /api/packs                   — packager validation gate (schema,
   license, prerequisite-cycle rejection against the registry)
4. POST /api/pathways/{id}/curriculum — bulk assign w/ sequence, unknown-pack
   and level-mismatch rejection, credits defaulted from the registry
5. Migration 010 idempotent re-run.

Required env:
  DATABASE_URL=postgresql://makesense:***@localhost:55447/makesense
"""
import asyncio
import json
import os
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "packs" / "samples"

PID = os.getpid()
USER_A = 940_000 + (PID % 50_000)
SUFFIX = f"{PID}"  # pack ids are registry-global; namespace per run


def hdr(user_id: int = USER_A):
    return {"X-User-ID": str(user_id)}


def sample(name):
    return json.loads((SAMPLES / name / "manifest.json").read_text())


def namespaced(name, prereq_map=None):
    """Rewrite pack_id (+ prereq + rubric edges) so parallel test runs don't
    collide in the shared registry."""
    m = sample(name)
    m["pack_id"] = f"{m['pack_id']}-{SUFFIX}"
    m["prerequisites"] = [
        {**p, "pack_id": (prereq_map or {}).get(p["pack_id"], p["pack_id"])}
        for p in m.get("prerequisites", [])
    ]
    return m


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
    import asyncpg

    async def _up():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute(
                "INSERT INTO users (id, email) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING",
                USER_A, f"ll09c-{time.time_ns()}@test.local")
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


@pytest.fixture(scope="module")
def registry(client):
    """Register the three sample packs (namespaced) once for the module."""
    ids = {}
    for name in ("micro-python-foundations",
                 "undergrad-data-foundations",
                 "masters-research-methods"):
        payload = sample(name)
        new_id = f"{payload['pack_id']}-{SUFFIX}"
        payload = namespaced(name, ids)
        assert payload["pack_id"] == new_id
        r = client.post("/api/packs", json=payload, headers=hdr())
        assert r.status_code == 200, r.text
        ids[name] = new_id
    yield ids
    import asyncpg
    async def _drop():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute(
                "DELETE FROM content_packs WHERE pack_id = ANY($1::text[])",
                list(ids.values()))
        finally:
            await conn.close()
    asyncio.run(_drop())


# ---------------------------------------------------------------------------
# 1. GET /api/packs — level filter + back-compat
# ---------------------------------------------------------------------------

def test_get_packs_level_filter(client, registry):
    r = client.get("/api/packs", params={"level": "undergrad"}, headers=hdr())
    assert r.status_code == 200
    packs = r.json()["packs"]
    titles = {p["pack_id"] for p in packs}
    # undergrad pack serves undergrad + certificate
    assert registry["undergrad-data-foundations"] in titles
    assert registry["masters-research-methods"] not in titles
    assert all("undergrad" in p["level_target"] for p in packs)


def test_get_packs_backcompat_default_levels(client, registry):
    """A v0 pack with NO level fields must load and surface as
    level_target=[micro, certificate]."""
    legacy = sample("legacy-v0-study-pack")
    legacy["pack_id"] = f"legacy-v0-study-pack-{SUFFIX}"
    r = client.post("/api/packs", json=legacy, headers=hdr())
    assert r.status_code == 200, r.text
    assert r.json()["level_target"] == ["micro", "certificate"]

    r = client.get("/api/packs", params={"level": "micro"}, headers=hdr())
    assert legacy["pack_id"] in {p["pack_id"] for p in r.json()["packs"]}
    r = client.get("/api/packs", params={"level": "phd"}, headers=hdr())
    assert legacy["pack_id"] not in {p["pack_id"] for p in r.json()["packs"]}
    client.get  # noqa: register cleanup below
    import asyncpg
    async def _drop():
        conn = await asyncpg.connect(_dsn())
        await conn.execute("DELETE FROM content_packs WHERE pack_id = $1", legacy["pack_id"])
        await conn.close()
    asyncio.run(_drop())


def test_get_packs_bad_level_rejected(client):
    r = client.get("/api/packs", params={"level": "bachelors"}, headers=hdr())
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 2. GET /api/packs?prereq_satisfied=true — transcript gating
# ---------------------------------------------------------------------------

def _pathway(client, level):
    r = client.post("/api/pathways", json={
        "title": f"ll09c {level} pathway", "level": level, "goal": "test"},
        headers=hdr())
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_prereq_satisfied_filter(client, registry):
    # before any mastery: masters pack should be gated out
    r = client.get("/api/packs",
                   params={"level": "masters", "prereq_satisfied": "true"},
                   headers=hdr())
    assert registry["masters-research-methods"] not in {
        p["pack_id"] for p in r.json()["packs"]}

    # record transcript mastery for the undergrad prereq (min_mastery 0.85)
    pw = _pathway(client, "masters")
    r = client.post(f"/api/pathways/{pw}/transcript", json={
        "content_pack_id": registry["undergrad-data-foundations"],
        "mastery_score": 0.9}, headers=hdr())
    assert r.status_code == 200, r.text

    r = client.get("/api/packs",
                   params={"level": "masters", "prereq_satisfied": "true"},
                   headers=hdr())
    ids = {p["pack_id"] for p in r.json()["packs"]}
    assert registry["masters-research-methods"] in ids

    # and a low mastery does NOT satisfy: the transcript entry is an upsert
    # (latest score wins per user+pathway+pack), so 0.1 replaces 0.9 and the
    # masters pack is gated out again.
    r = client.post(f"/api/pathways/{pw}/transcript", json={
        "content_pack_id": registry["undergrad-data-foundations"],
        "mastery_score": 0.1}, headers=hdr())
    assert r.status_code == 200
    r = client.get("/api/packs",
                   params={"level": "masters", "prereq_satisfied": "true"},
                   headers=hdr())
    assert registry["masters-research-methods"] not in {
        p["pack_id"] for p in r.json()["packs"]}


# ---------------------------------------------------------------------------
# 3. POST /api/packs — validation gate
# ---------------------------------------------------------------------------

def test_register_rejects_bad_manifest(client):
    r = client.post("/api/packs", json={"pack_id": "x"}, headers=hdr())
    assert r.status_code == 422


def test_register_rejects_license_violation(client, registry):
    m = namespaced("masters-research-methods", registry)
    m["pack_id"] = f"nc-masters-{SUFFIX}"
    m["source"]["license"] = "CC-BY-NC-SA-4.0"   # NC disallowed at masters
    r = client.post("/api/packs", json=m, headers=hdr())
    assert r.status_code == 422 and "license" in r.text.lower()


def test_register_rejects_prereq_cycle(client, registry):
    """A -> B -> A across registry + candidate must be rejected."""
    # undergrad already prereqs micro; re-register micro (same pack_id; the
    # cycle check runs BEFORE the upsert, so a rejection leaves the registry
    # untouched) with micro prereq'ing undergrad -> real cycle.
    m = namespaced("micro-python-foundations", registry)
    m["prerequisites"] = [{"pack_id": registry["undergrad-data-foundations"],
                           "min_mastery": 0.5}]
    r = client.post("/api/packs", json=m, headers=hdr())
    assert r.status_code == 422 and "cycle" in r.text.lower()


# ---------------------------------------------------------------------------
# 4. POST /api/pathways/{id}/curriculum
# ---------------------------------------------------------------------------

def test_curriculum_bulk_assign(client, registry):
    pw = _pathway(client, "undergrad")
    r = client.post(f"/api/pathways/{pw}/curriculum", json={"items": [
        {"content_pack_id": registry["micro-python-foundations"]},
        {"content_pack_id": registry["undergrad-data-foundations"]},
    ]}, headers=hdr())
    assert r.status_code == 200, r.text
    curr = r.json()["curriculum"]
    assert [c["sequence"] for c in curr] == [0, 1]
    assert curr[1]["credits"] == 3.0          # defaulted from pack credit_value


def test_curriculum_rejects_unknown_pack(client, registry):
    pw = _pathway(client, "undergrad")
    r = client.post(f"/api/pathways/{pw}/curriculum", json={"items": [
        {"content_pack_id": "no-such-pack-xyz"}]}, headers=hdr())
    assert r.status_code == 422 and "unknown" in r.text.lower()


def test_curriculum_rejects_level_mismatch(client, registry):
    pw = _pathway(client, "phd")
    r = client.post(f"/api/pathways/{pw}/curriculum", json={"items": [
        {"content_pack_id": registry["undergrad-data-foundations"]}]},
        headers=hdr())
    assert r.status_code == 422 and "serves" in r.text.lower()


def test_curriculum_rejects_duplicate_sequence(client, registry):
    pw = _pathway(client, "undergrad")
    r = client.post(f"/api/pathways/{pw}/curriculum", json={"items": [
        {"content_pack_id": registry["micro-python-foundations"], "sequence": 0},
        {"content_pack_id": registry["undergrad-data-foundations"], "sequence": 0},
    ]}, headers=hdr())
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 5. Migration idempotency
# ---------------------------------------------------------------------------

def test_migration_010_idempotent(client):
    import asyncpg
    sql = (ROOT / "server" / "migrations" / "010_content_pack_registry.sql").read_text()
    async def _re():
        conn = await asyncpg.connect(_dsn())
        try:
            await conn.execute(sql)   # re-run must not raise
            n = await conn.fetchval("SELECT count(*) FROM content_packs")
        finally:
            await conn.close()
        return n
    assert asyncio.run(_re()) >= 0
