"""LL-05 §2 rubric scorer: schema validation, anchors, citations, escalation band."""
import pytest

from packages.assessment import rubric as R
from packages.assessment.rubric import RubricError, load_rubric, score_submission

from helpers import ScriptedModel, rubric_4level, scoring_response, sub_payload
from packages.assessment import evidence


def _sub(**kw):
    return evidence.intake(sub_payload(**kw))


def test_rubric_requires_weights_sum_anchors_and_version():
    r = rubric_4level()
    assert load_rubric(r) is r                       # valid
    bad = dict(r, version="draft")                   # version pattern v<n>
    with pytest.raises(RubricError):
        load_rubric(bad)
    bad = dict(r)
    bad["criteria"] = [dict(c) for c in r["criteria"]]
    bad["criteria"][0]["weight"] = 0.9
    with pytest.raises(RubricError, match="weights"):
        load_rubric(bad)
    bad = dict(r)
    bad["criteria"] = [{**c, "levels": {k: {kk: vv for kk, vv in lv.items() if kk != "anchors"}
                                       for k, lv in c["levels"].items()}}
                       for c in r["criteria"]]
    with pytest.raises(RubricError, match="anchor"):
        load_rubric(bad)


def test_scoring_cites_evidence_and_prompt_version():
    r = rubric_4level(scores=(3, 3, 2))
    model = ScriptedModel([scoring_response(r)])
    v = score_submission(r, _sub(), model, evidence_text="runs, 8/8 tests")
    assert v.passed
    res = v.result
    assert res["prompt_version"] == R.PROMPT_VERSION
    assert res["rubric_ref"] == "rb_coding_lvl2@v1.0"
    for cs in res["criterion_scores"]:
        assert cs["rationale"].strip()
        assert cs["evidence_refs"]
    assert res["evidence_cited"]
    # rubric text injected verbatim into the system+user prompt
    joined = "\n".join(a + b for a, b in model.calls)
    assert "Strong: correct, clean" in joined
    assert "anchor:strong-001" in joined


def test_weighted_math_and_fail():
    r = rubric_4level(scores=(1, 1, 0))    # 0.5*1/3+0.3*1/3+0.2*0 = 0.267
    v = score_submission(r, _sub(), ScriptedModel([scoring_response(r)]), "weak work")
    assert not v.passed
    assert 0.26 < v.result["weighted_score"] < 0.28


def test_escalation_band_triggers_human_review():
    # target weighted ~0.66 (threshold .65, band .08): scores 2,2,2 -> 0.667
    r = rubric_4level(scores=(2, 2, 2))
    v = score_submission(r, _sub(), ScriptedModel([scoring_response(r)]), "ok")
    assert v.passed
    assert v.human_escalation is True    # within band of threshold


def test_missing_criterion_or_rationale_rejected():
    r = rubric_4level()
    bad = {"criteria": {c["criterion_id"]:
                        {"score": 3, "rationale": "", "evidence_refs": []}
                        for c in r["criteria"][:2]}}   # omits third, empty rationale
    import json
    with pytest.raises(RubricError):
        score_submission(r, _sub(), ScriptedModel([json.dumps(bad)]), "x")


def test_out_of_range_score_rejected():
    r = rubric_4level()
    import json
    resp = json.loads(scoring_response(r))
    resp["criteria"]["correctness"]["score"] = 5
    with pytest.raises(RubricError, match="outside"):
        score_submission(r, _sub(), ScriptedModel([json.dumps(resp)]), "x")


def test_non_json_response_rejected():
    r = rubric_4level()
    with pytest.raises(RubricError, match="no JSON"):
        score_submission(r, _sub(), ScriptedModel(["sorry, no JSON here"]), "x")
