"""LL-07: Batches, side quests, and the stores layer.

Engagement packaging on top of gamification (mk-028) and the pack format:

- ``ll07.stores``   — one queryable module over the six persistent inventories
                      (items, snapshots, mastery, verifications, recaps, quests).
- ``ll07.batches``  — chunk ladder rungs into weekly-ish skill batches with
                      per-track pacing; completion events feed the mastery ledger.
- ``ll07.quests``   — side-quest engine: optional enrichments from ladder
                      adjacency or interest signals; contributes to mastery,
                      never gates the main path.

Vision: docs/learning-loop-vision.md §3.
"""

from ll07.stores import Stores, STORE_NAMES
from ll07.batches import plan_batches, record_batch_completion
from ll07.quests import generate_quests, accept_quest, complete_quest, expire_stale_quests

__all__ = [
    "Stores", "STORE_NAMES",
    "plan_batches", "record_batch_completion",
    "generate_quests", "accept_quest", "complete_quest", "expire_stale_quests",
]
