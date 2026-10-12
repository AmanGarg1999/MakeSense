"""LL-06 recap API: due-item surfacing + outcomes + on-demand rewind.

Reads/writes the LL-07 stores (SQLite, append-only) that the learning loop's
Python side maintains (``MAKENSE_STORES_DB``, default ``data/stores.db``).
Shapes here match ``ll06.scheduler.RecapItem.as_row`` + outcomes so the
WatermelonDB client mirror and the React surfaces consume the same JSON.
"""

import os
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ll06.scheduler import RecapScheduler
from ll06.digest import rewind
from ll06.outcomes import record_recap
from ll07.stores import Stores

router = APIRouter()

_STORES_DB = os.environ.get(
    "MAKENSE_STORES_DB",
    str(Path(__file__).resolve().parents[2] / "data" / "stores.db"))


def _stores() -> Stores:
    Path(_STORES_DB).parent.mkdir(parents=True, exist_ok=True)
    return Stores(_STORES_DB)


class RecapSubmit(BaseModel):
    skill_tag: str
    quality: int          # SM-2 style 0-5
    track_id: str | None = None


@router.get("/recap/{user_id}/due")
async def due_recaps(user_id: str, track_id: str | None = None):
    """Due recap items for the home/coach surface — short, streak-friendly wins."""
    stores = _stores()
    try:
        sched = RecapScheduler(stores)
        now = time.time()
        items = sched.due(user_id, track_id=track_id, now=now)
        return {
            "due": [{**i.as_row(),
                     "minutes": 2 if i.bucket <= 2 else 3,
                     "overdue_days": max(0, int((now - i.due_at) // 86400))}
                    for i in items],
            "upcoming_count": len(sched.upcoming(user_id)),
        }
    finally:
        stores.close()


@router.post("/recap/{user_id}/submit")
async def submit_recap(user_id: str, payload: RecapSubmit):
    stores = _stores()
    try:
        sched = RecapScheduler(stores)
        try:
            res = record_recap(stores, sched, user_id=user_id,
                               skill_tag=payload.skill_tag,
                               quality=payload.quality,
                               track_id=payload.track_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        return res
    finally:
        stores.close()


@router.get("/recap/{user_id}/rewind")
async def recap_rewind(user_id: str, topic: str = Query(..., min_length=1)):
    """"Take me back through X" — retrieval-first digest with citations."""
    stores = _stores()
    try:
        snap = stores.latest("snapshots")
        ladder = snap.get("rungs") if snap else None
        return rewind(stores, user_id=user_id, topic=topic, ladder=ladder)
    finally:
        stores.close()
