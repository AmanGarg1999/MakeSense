"""LL-06: Spaced recap/review subsystem + on-demand rewind.

Vision: docs/learning-loop-vision.md §3 ("Recap/review: user-initiated +
interval-driven, Leitner/SM-2 style buckets, tuned per skill decay rate from
verification results") and §2.8 (stuck detection — change strategy, don't
repeat).

Modules:
- ``ll06.scheduler`` — the spaced-recap scheduler: Leitner buckets seeded from
  the mastery ledger (ll07.stores ``mastery``/``verifications``) + the LL-05
  verification-expiry feed (``packages.assessment.registry.due_events``).
  Intervals grow ×GROWTH on success, reset on lapse; growth is tuned per
  skill-family by observed recall success. All state is append-only into the
  stores ``recaps`` stream (offline-capable; mirrors the WatermelonDB pull
  shape on the client).
- ``ll06.digest``   — user-initiated rewind: "take me back through X" builds a
  retrieval-first review digest (questions before answers) from the knowledge
  DB + what the user actually did/missed, with citations.
- ``ll06.outcomes`` — recap-session completion: updates mastery, extends or
  resets verification currency (LL-05 expiry math), and routes recap failures
  back into LL-04 delivery (flip to active mode / re-teach prerequisite)
  instead of repeating the same card.
"""

from ll06.scheduler import RecapScheduler
from ll06.digest import build_digest, rewind
from ll06.outcomes import record_recap

__all__ = ["RecapScheduler", "build_digest", "rewind", "record_recap"]
