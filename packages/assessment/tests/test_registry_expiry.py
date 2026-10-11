"""LL-05 §4 verification registry: append-only + §5 expiry transitions."""
import pytest
import sqlite3

from packages.assessment.registry import RegistryError, VerificationRegistry

from helpers import ts


def _append(r, verdict="verified", expires=None, skill="python", level=2,
            recheck_of=None, user="u42", verified=None):
    return r.append(user_id=user, skill_tag=skill, level_index=level,
                    verdict=verdict, verifier={"kind": "deterministic"},
                    evidence_refs=["blob:a1"], verified_at=verified or ts(0),
                    expires_at=expires, recheck_of=recheck_of)


def test_append_and_latest(registry):
    e1 = _append(registry, verdict="verified")
    e2 = _append(registry, verdict="reinforced", verified=ts(10))
    latest = registry.latest("u42", "python", 2)
    assert latest.event_id == e1.event_id          # most recent verified_at wins
    assert len(registry.history("u42", "python")) == 2


def test_append_only_sqlite_rejects_update_delete(registry):
    ev = _append(registry)
    with pytest.raises(sqlite3.IntegrityError):
        registry._conn.execute("UPDATE verification_registry SET verdict='rejected' "
                               "WHERE event_id=?", (ev.event_id,))
    registry._conn.rollback()
    with pytest.raises(sqlite3.IntegrityError):
        registry._conn.execute("DELETE FROM verification_registry")
    registry._conn.rollback()
    assert registry.count() == 1


def test_verdict_and_class_validation(registry):
    with pytest.raises(RegistryError):
        _append(registry, verdict="probably")
    with pytest.raises(RegistryError):
        registry.append(user_id=1, skill_tag="x", level_index=0, verdict="verified",
                        verifier={"kind": "deterministic"}, primary_evidence="E9")
    with pytest.raises(RegistryError):
        registry.append(user_id=1, skill_tag="x", level_index=0, verdict="verified",
                        verifier={"kind": "wizard"})


def test_due_events_lists_past_expiry(registry):
    _append(registry, expires=ts(3))                # expired 3 days ago
    _append(registry, skill="guitar", expires=ts(-30))   # due in 30 days
    due = registry.due_events(ts(0))
    assert [d.skill_tag for d in due] == ["python"]


# ---- expiry clock (LL-01 §9) -------------------------------------------------

from packages.assessment import expiry


def test_family_intervals_seed_first_recheck():
    assert expiry.next_interval_days("coding", 0) == 30
    assert expiry.next_interval_days("language", 0) == 21
    assert expiry.next_interval_days("finance", 0) == 60


def test_sm2_expansion_and_ceiling():
    i = [expiry.next_interval_days("coding", n) for n in range(6)]
    assert i == [30, 60, 150, 180, 180, 180]      # ×2.5 growth, ceiling 180
    assert expiry.next_interval_days("math", 1) == 38
    assert expiry.next_interval_days("math", 2) == 90      # ceiling


def test_status_transitions_current_stale_expired():
    verified = "2026-01-01T00:00:00+00:00"
    due = expiry.next_due(verified, "coding", 0)          # +30d = 2026-01-31
    assert due.startswith("2026-01-31")
    kw = dict(user_id=1, skill_tag="python", level_index=2,
              latest_verdict="verified", verified_at=verified,
              expires_at=due, clean_rechecks=0)
    st_now = expiry.compute_status(**kw, now="2026-01-15T00:00:00+00:00")
    assert st_now.status == "current" and st_now.recheck_task is None
    # 3 days past due, within grace (max(7, 25%*30)=7d): stale
    st_stale = expiry.compute_status(**kw, now="2026-02-03T00:00:00+00:00")
    assert st_stale.status == "stale" and st_stale.recheck_task is None
    # 15 days past due (>7d grace): expired + re-verify task queued
    st_exp = expiry.compute_status(**kw, now="2026-02-15T00:00:00+00:00")
    assert st_exp.status == "expired"
    task = st_exp.recheck_task
    assert task is not None
    assert task["type"] == "reverify"
    assert task["required_evidence"] == "performance"
    assert task["downgrade_to"] == "provisional"


def test_count_clean_rechecks_expands_and_resets():
    hist = [{"verdict": "verified", "recheck_of": None, "verified_at": ts(31)},
            {"verdict": "reinforced", "recheck_of": "ver_1", "verified_at": ts(1)},
            {"verdict": "reinforced", "recheck_of": "ver_2", "verified_at": ts(-1)}]
    assert expiry.count_clean_rechecks(hist) == 2
    hist.append({"verdict": "rejected", "recheck_of": "ver_3", "verified_at": ts(-2)})
    assert expiry.count_clean_rechecks(hist) == 0     # lapse resets SM-2 count


def test_family_for_tag_aliases():
    assert expiry.family_for("javascript-dom") == "coding"
    assert expiry.family_for("classical_guitar") == "guitar"
    assert expiry.family_for("knitting") == "default"
    assert expiry.family_for("anything", family="math") == "math"
