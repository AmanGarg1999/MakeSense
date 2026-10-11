"""Shared fakes/builders for LL-05 assessment tests."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from packages.assessment import evidence


class ScriptedModel:
    """ModelClient fake: pops canned responses in call order."""

    model_name = "scripted-test-model"

    def __init__(self, responses=None):
        self._responses = list(responses or [])
        self.calls = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self._responses:
            return self._responses.pop(0)
        raise AssertionError("ScriptedModel ran out of responses")


def rubric_4level(scores=("3", "3", "2")):
    """Coding-flavored analytic rubric: 4 levels (0..3), weights sum to 1, anchors set."""
    levels = {"3": {"description": "Strong: correct, clean, explains tradeoffs",
                    "anchors": [{"ref": "anchor:strong-001"}]},
              "2": {"description": "Working: correct with minor issues",
                    "anchors": [{"ref": "anchor:working-001"}]},
              "1": {"description": "Novice: partial",
                    "anchors": [{"ref": "anchor:novice-001"}]},
              "0": {"description": "No evidence of the criterion",
                    "anchors": [{"ref": "anchor:none-001"}]}}
    return {
        "rubric_id": "rb_coding_lvl2", "version": "v1.0", "skill_tag": "python",
        "level_index": 2, "evidence_class": "E3",
        "levels": [{"score": i, "label": lbl} for i, lbl in
                   [(0, "Novice"), (1, "Working-low"), (2, "Proficient"), (3, "Strong")]],
        "criteria": [
            {"criterion_id": "correctness", "name": "Correctness", "weight": 0.5,
             "levels": levels},
            {"criterion_id": "design", "name": "Design/maintainability", "weight": 0.3,
             "levels": levels},
            {"criterion_id": "explanation", "name": "Explanation quality", "weight": 0.2,
             "levels": levels},
        ],
        "pass_threshold": 0.65, "escalation_band": 0.08,
        "_scores": [int(s) for s in scores],   # consumed by scoring_response()
    }


def scoring_response(rubric, confidences=None):
    """Build the model's JSON answer giving each criterion the packed scores."""
    scores = rubric.get("_scores", [])
    out = {"criteria": {}}
    for i, c in enumerate(rubric["criteria"]):
        out["criteria"][c["criterion_id"]] = {
            "score": scores[i] if i < len(scores) else 0,
            "rationale": f"Observed for {c['criterion_id']}: matches that level's description.",
            "evidence_refs": [f"blob:artifact-{i}"],
            "confidence": (confidences[i] if confidences else 0.9),
        }
    return json.dumps(out)


def ts(days_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def sub_payload(kind="code_execution", rung=("artifact",), *, exec_result=None,
                performance=None, repo=None, artifacts=None, transcript=None,
                ocr_text=None, submitted=None, process=None, defense=None,
                intent=None, recheck_of=None, skill="python", level=2, user="u42"):
    p = evidence.build_submission(
        user_id=user, skill_tag=skill, level_index=level,
        rung_evidence_types=list(rung), kind=kind,
        artifacts=artifacts if artifacts is not None
        else [{"ref": "blob:artifact-0"}],
        execution=exec_result if exec_result is not None
        else ({"ran": True, "tests_passed": 8, "tests_total": 8,
               "sandbox": "docker:py311-sandbox"} if kind == "code_execution" else None),
        performance=performance, repo=repo, transcript=transcript, ocr_text=ocr_text,
        environment="test-harness", submitted_at=submitted, process_signals=process,
        defense=defense)
    if intent:
        p["intent"] = intent
    if recheck_of:
        p["recheck_of"] = recheck_of
    return p
