#!/usr/bin/env python3
"""LL-09a demo: create one learning pathway per canonical level and read it
back against a running server (or an in-process TestClient).

Usage:
  python scripts/demo_learning_pathways.py                 # in-process, needs DATABASE_URL
  BASE_URL=http://localhost:8000 X_USER_ID=42 python scripts/demo_learning_pathways.py

Creates: pathways for micro/certificate/undergrad/masters/phd/mba, each with a
2-item curriculum; a transcript entry with a credential; then GETs each back,
prints a summary table, and cleans up the pathways it created.
"""

import os
import sys

LEVELS = ["micro", "certificate", "undergrad", "masters", "phd", "mba"]
USER_ID = int(os.environ.get("X_USER_ID", "940001"))


def make_client():
    base = os.environ.get("BASE_URL")
    if base:
        import httpx
        return httpx.Client(base_url=base, timeout=30)
    # in-process: boots the real app via lifespan (init_db runs migrations)
    from fastapi.testclient import TestClient
    from server.main import app
    return TestClient(app)


def main() -> int:
    client = make_client()
    ctx = client if os.environ.get("BASE_URL") else client.__enter__()
    headers = {"X-User-ID": str(USER_ID)}
    created = []
    try:
        # ensure user exists when running in-process against the dev DB
        if not os.environ.get("BASE_URL"):
            import asyncio, asyncpg

            async def _up():
                conn = await asyncpg.connect(os.environ["DATABASE_URL"])
                try:
                    await conn.execute(
                        "INSERT INTO users (id, email) VALUES ($1,$2) "
                        "ON CONFLICT (id) DO NOTHING",
                        USER_ID, f"ll09a-demo-{USER_ID}@demo.local",
                    )
                finally:
                    await conn.close()
            asyncio.run(_up())

        print(f"{'level':<12} {'pathway id':<38} {'status':<8} curriculum")
        for level in LEVELS:
            r = ctx.post("/api/pathways", headers=headers, json={
                "level": level,
                "title": f"Demo {level} pathway",
                "curriculum": [
                    {"content_pack_id": f"pack-{level}-core", "sequence": 0,
                     "required": True, "credits": 4},
                    {"content_pack_id": f"pack-{level}-elective", "sequence": 1,
                     "required": False, "credits": 2},
                ],
            })
            r.raise_for_status()
            p = r.json()
            created.append(p["id"])

            g = ctx.get(f"/api/pathways/{p['id']}", headers=headers)
            g.raise_for_status()
            got = g.json()
            assert got["level"] == level, "read-back level mismatch"
            packs = ",".join(c["content_pack_id"] for c in got["curriculum"])
            print(f"{level:<12} {got['id']:<38} {got['status']:<8} {packs}")

            t = ctx.post(f"/api/pathways/{p['id']}/transcript", headers=headers, json={
                "content_pack_id": f"pack-{level}-core",
                "mastery_score": 0.91,
                "credential_issued": True,
                "credential_type": f"{level}-badge",
            })
            t.raise_for_status()

        # level filter + coach helper
        r = ctx.get("/api/pathways?level=phd", headers=headers)
        r.raise_for_status()
        print(f"\nGET /pathways?level=phd -> {len(r.json())} pathway(s)")

        r = ctx.get("/api/pathways/active", headers=headers)
        r.raise_for_status()
        a = r.json()
        meta = a["level_metadata"]
        print(f"active pathway: level={a['level']} recap_every={meta['recap_interval_days']}d "
              f"mentor={meta['mentor_model']}")

        levels = ctx.get("/api/pathways/levels").json()
        print(f"level_metadata rows: {sorted(x['level'] for x in levels)}")
        print("\nDEMO OK")
        return 0
    finally:
        for pid in created:
            try:
                ctx.delete(f"/api/pathways/{pid}", headers=headers)
            except Exception:
                pass
        if not os.environ.get("BASE_URL"):
            client.__exit__(None, None, None)


if __name__ == "__main__":
    sys.exit(main())
