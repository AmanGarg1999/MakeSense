"""LL-06 API surface: /api/recap routes serve due-items + rewind.

Proves the home/coach surfacing (RecapCard/RecapSession consume exactly these
JSON shapes) end-to-end through the FastAPI router over a file-backed store.
"""

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.routers import recap as recap_router
from ll07.stores import Stores


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = str(tmp_path / "stores.db")
    monkeypatch.setattr(recap_router, "_STORES_DB", db)
    app = FastAPI()
    app.include_router(recap_router.router, prefix="/api")
    # seed: one skill already past due, one far in the future
    s = Stores(db)
    now = time.time()
    # overdue via a past lapse (recap event folds due_at from history)
    s.append("recaps", {"user_id": "u1", "track_id": "t1",
                        "skill_tag": "python:closures", "due_at": now - 2 * 86400,
                        "bucket": 1, "status": "scheduled",
                        "outcome": "lapsed", "quality": 2},
             provenance="user", ts=now - 2 * 86400)
    # fresh mastery -> scheduled ahead, not due
    s.append("mastery", {"user_id": "u1", "track_id": "t1",
                         "skill_tag": "web:fetch", "delta": 2.0,
                         "cause": "batch_completed"},
             provenance="engine:batcher", ts=now - 1 * 86400)
    s.close()
    yield TestClient(app)


def test_due_surfacing_shape(client):
    r = client.get("/api/recap/u1/due")
    assert r.status_code == 200
    body = r.json()
    tags = [d["skill_tag"] for d in body["due"]]
    assert "python:closures" in tags            # 40-day-old mastery is overdue
    for d in body["due"]:
        assert d["minutes"] in (2, 3)            # low-effort framing
        assert d["overdue_days"] >= 0
    assert body["upcoming_count"] + len(body["due"]) >= 2


def test_submit_updates_schedule_and_currency(client):
    due = client.get("/api/recap/u1/due").json()["due"]
    target = next(d for d in due if d["skill_tag"] == "python:closures")
    r = client.post("/api/recap/u1/submit",
                    json={"skill_tag": target["skill_tag"],
                          "track_id": target["track_id"], "quality": 5})
    assert r.status_code == 200
    res = r.json()
    assert res["passed"] is True
    assert res["next_due_at"] > time.time()      # pushed out of the due window
    after = client.get("/api/recap/u1/due").json()["due"]
    assert "python:closures" not in [d["skill_tag"] for d in after]


def test_submit_unknown_skill_is_404(client):
    r = client.post("/api/recap/u1/submit",
                    json={"skill_tag": "kitesurfing:gybe", "quality": 4})
    assert r.status_code == 404


def test_rewind_route_returns_cited_digest(client):
    r = client.get("/api/recap/u1/rewind", params={"topic": "take me back through python"})
    assert r.status_code == 200
    d = r.json()
    assert d["format"] == "retrieval-first"
    assert d["sections"] and d["summary"]
    # retrieval-first ordering holds through the API layer
    sec = d["sections"][0]
    assert list(sec.keys()).index("prompt") < list(sec.keys()).index("reveal")
