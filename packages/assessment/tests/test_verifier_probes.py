"""LL-05 §3 transfer tests + oral defense; §5 verifier orchestration end-to-end."""
import json

import pytest

from packages.assessment import verifier as V
from packages.assessment.probes import (Probe, ProbeSet, defense_verdict,
                                        generate_probes, record_answer)
from packages.assessment.registry import VerificationRegistry

from helpers import ScriptedModel, rubric_4level, scoring_response, sub_payload, ts


PROBE_JSON = json.dumps({"probes": [
    {"probe_id": "p1", "kind": "transfer_application",
     "prompt": "Apply the same rate-limiter design to a WebSocket fan-out service.",
     "rubric_hint": "reuses token-bucket structure in new surface",
     "derived_from": "blob:artifact-0"},
    {"probe_id": "p2", "kind": "perturbation",
     "prompt": "Requirement changes: window doubles. Which lines break and why?",
     "rubric_hint": "predicts behavior change without running it",
     "derived_from": "blob:artifact-0"},
    {"probe_id": "p3", "kind": "debug_seed",
     "prompt": "Off-by-one seeded in the refill loop — find and fix it live.",
     "rubric_hint": "locates defect via reasoning",
     "derived_from": "blob:artifact-0"},
]})


def test_generate_probes_and_record_answers():
    model = ScriptedModel([PROBE_JSON])
    ps = generate_probes(model, skill_tag="python", level_index=2,
                         can_do="build a rate limiter",
                         artifact_description="token-bucket middleware",
                         evidence_refs=["blob:artifact-0"])
    assert len(ps.probes) == 3
    kinds = {p.kind for p in ps.probes}
    assert "transfer_application" in kinds and "perturbation" in kinds
    record_answer(ps, "p1", True, transcript_ref="blob:defense-1")
    record_answer(ps, "p2", True)
    record_answer(ps, "p3", False)
    d = defense_verdict(ps)
    assert d["outcome"] == "failed"
    assert d["escalate"] == "in_session"        # LL-01 §3.3 rung 3
    assert d["probes_total"] == 3 and d["probes_answered"] == 3


def test_defense_block_shape():
    ps = ProbeSet("python", 2, probes=[Probe("p1", "perturbation", "q", "hint", "blob:a")])
    record_answer(ps, "p1", True)
    block = ps.as_defense_block()
    assert block["satisfactory"] is True and block["probes_answered"] == 1


# ---- orchestration -----------------------------------------------------------

def test_end_to_end_code_execution_verified_and_scheduled(registry):
    out = V.grade_submission(sub_payload("code_execution"), rubric=None, model=None,
                  registry=registry)
    assert out.verdict == "verified" and out.status == "current"
    ev = registry.latest("u42", "python", 2)
    assert ev.primary_evidence == "E3"
    assert ev.expires_at is not None             # 30d first re-check (coding family)


def test_explain_only_attempt_is_rejected_and_audited(registry):
    """ACCEPTANCE: rejected explain-only case leaves an append-only trace."""
    out = V.grade_submission(sub_payload("explanation", rung=("artifact",)),
                  rubric=None, model=None, registry=registry)
    assert out.verdict == "rejected"
    ev = registry.latest("u42", "python", 2)
    assert ev.verdict == "rejected" and "integrity" in (ev.notes or "")
    assert ev.expires_at is None


def test_failing_tests_reject(registry):
    out = V.grade_submission(sub_payload("code_execution",
                              exec_result={"ran": True, "tests_passed": 3,
                                           "tests_total": 8}),
                  rubric=None, model=None, registry=registry)
    assert out.verdict == "rejected"


def test_rubric_scored_path_cites_prompt_version(registry):
    r = rubric_4level(scores=(3, 3, 3))
    model = ScriptedModel([scoring_response(r)])
    out = V.grade_submission(sub_payload("media_recording", rung=("performance",),
                              artifacts=[{"ref": "blob:take.mp4"}],
                              transcript="full piece, no edits"),
                  rubric=r, model=model, registry=registry,
                  evidence_text="[video] continuous take, in time")
    assert out.verdict == "verified"
    ev = registry.latest("u42", "python", 2)
    assert ev.prompt_version and ev.rubric_ref == "rb_coding_lvl2@v1.0"
    assert ev.scoring["criterion_scores"][0]["rationale"]


def test_detector_prior_raises_defense_rung_not_verdict(registry):
    """LL-01 §3.1: detector output never convicts — it requests a defense."""
    out = V.grade_submission(sub_payload("code_execution",
                              process={"ai_detector_prior": 0.9}),
                  rubric=None, model=None, registry=registry)
    assert out.verdict == "provisional" and out.escalation_rung == "defense"
    assert out.requeue["type"] == "defense_request"


def test_rung_needing_defense_without_answers_is_provisional(registry):
    out = V.grade_submission(sub_payload("code_execution",
                              rung=("artifact", "oral_defense")),
                  rubric=None, model=None, registry=registry)
    assert out.verdict == "provisional"
    assert out.requeue["type"] == "defense_request"


def test_passed_defense_verifies(registry):
    out = V.grade_submission(sub_payload("code_execution", rung=("artifact", "oral_defense"),
                              defense={"probes_total": 2, "probes_answered": 2,
                                       "satisfactory": True}),
                  rubric=None, model=None, registry=registry)
    assert out.verdict == "verified"


def test_failed_defense_escalates_in_session(registry):
    out = V.grade_submission(sub_payload("code_execution", rung=("artifact", "oral_defense"),
                              defense={"probes_total": 2, "probes_answered": 2,
                                       "satisfactory": False}),
                  rubric=None, model=None, registry=registry)
    assert out.verdict == "rejected" and out.escalation_rung == "in_session"
    assert out.requeue["type"] == "in_session_recreation"


def test_reinforced_recheck_expands_interval(registry):
    first = V.grade_submission(sub_payload("code_execution", submitted=ts(31)),
                    rubric=None, model=None, registry=registry)
    ev1 = registry.latest("u42", "python", 2)
    out2 = V.grade_submission(sub_payload("code_execution", submitted=ts(0),
                              intent="recheck", recheck_of=ev1.event_id),
                   rubric=None, model=None, registry=registry)
    assert out2.verdict == "reinforced"
    ev2 = registry.latest("u42", "python", 2)
    assert ev2.recheck_of == ev1.event_id
    # interval expands: second gap (30d->60d) larger than first
    from datetime import datetime
    d = lambda s: datetime.fromisoformat(s)
    gap1 = (d(ev1.expires_at) - d(ev1.verified_at)).days
    gap2 = (d(ev2.expires_at) - d(ev2.verified_at)).days
    assert gap1 == 30 and gap2 == 60


def test_tick_expiry_downgrades_and_queues(registry):
    V.grade_submission(sub_payload("code_execution", submitted=ts(45)),
            rubric=None, model=None, registry=registry)
    outcomes = V.tick_expiry(registry, now=ts(0))
    assert len(outcomes) == 1
    o = outcomes[0]
    assert o.status == "expired" and o.verdict == "provisional"
    assert o.requeue is not None and o.requeue["type"] == "reverify"
    # append-only: the original verified event still stands, new provisional on top
    ev = registry.latest("u42", "python", 2)
    assert ev.verdict == "provisional"
    assert V.current_status(registry, "u42", "python", 2) == "provisional"


def test_current_status_unverified(registry):
    assert V.current_status(registry, "nobody", "python", 0) == "unverified"
