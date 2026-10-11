"""Analytic rubric scorer (LL-05 §2).

Model-assisted scoring with:
  - rubric text injected VERBATIM into the prompt (LL-01 §5c),
  - prompt versioning (PROMPT_VERSION + rubric_id@version cited in the result),
  - per-criterion rationale + confidence + evidence citations,
  - a human-escalation band around the pass threshold (LL-01 §5b).

The scoring prompt lives in prompts/score_rubric.md and is version-pinned.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from jsonschema import Draft202012Validator

from .evidence import Submission

PROMPT_VERSION = "v1.2"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_SCORING_SCHEMA = json.loads(
    (Path(__file__).resolve().parent / "schemas" / "scoring_result.json").read_text()
)
_SCHEMA_VALIDATOR = Draft202012Validator(_SCORING_SCHEMA)


class ModelClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class RubricError(ValueError):
    pass


def load_rubric(payload: dict) -> dict:
    """Validate a rubric against schemas/rubric.json and normalize weights."""
    schema = json.loads((Path(__file__).resolve().parent / "schemas" / "rubric.json").read_text())
    errs = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errs:
        raise RubricError("; ".join(f"$.{'.'.join(map(str, e.absolute_path))}: {e.message}"
                                    for e in errs[:5]))
    total_w = sum(c["weight"] for c in payload["criteria"])
    if abs(total_w - 1.0) > 0.01:
        raise RubricError(f"criteria weights must sum to 1.0 (got {total_w:.3f})")
    # anchor exemplars are non-negotiable (LL-01 §5): at least one anchor per rubric,
    # and pass-band levels must carry anchors.
    max_score = max(int(k) for c in payload["criteria"] for k in c["levels"])
    for c in payload["criteria"]:
        if not any(lv.get("anchors") for lv in c["levels"].values()):
            raise RubricError(f"criterion {c['criterion_id']}: anchor exemplars are required")
    return payload


def render_rubric_text(rubric: dict) -> str:
    """Inject the rubric verbatim (levels, criteria, anchors) into the prompt."""
    lines = [f"RUBRIC {rubric['rubric_id']} {rubric['version']} "
             f"(skill {rubric['skill_tag']}, level {rubric['level_index']})"]
    label_by_score = {l["score"]: l["label"] for l in rubric["levels"]}
    for c in rubric["criteria"]:
        lines.append(f"- Criterion {c['criterion_id']} \"{c['name']}\" (weight {c['weight']})")
        for score_str, lev in sorted(c["levels"].items(), key=lambda kv: int(kv[0]), reverse=True):
            anchors = "; ".join(a["ref"] for a in lev.get("anchors", [])) or "none"
            lines.append(f"    [{score_str}={label_by_score.get(int(score_str), '')}] "
                         f"{lev['description']} | anchors: {anchors}")
    return "\n".join(lines)


def build_prompt(rubric: dict, submission: Submission,
                 evidence_text: str, defense_text: str | None = None) -> tuple[str, str]:
    """Return (system, user) for the scoring call. System = template + rubric verbatim."""
    template = (PROMPTS_DIR / "score_rubric.md").read_text(encoding="utf-8")
    system = template.replace("{{PROMPT_VERSION}}", PROMPT_VERSION)
    user = "\n\n".join(filter(None, [
        render_rubric_text(rubric),
        f"EVIDENCE KIND: {submission.kind}\n"
        f"ARTIFACT REFS: {json.dumps(submission.artifact_refs())}\n"
        f"PROVENANCE: {json.dumps(submission.provenance)}",
        f"EVIDENCE CONTENT:\n{evidence_text}",
        (f"DEFENSE TRANSCRIPT:\n{defense_text}") if defense_text else None,
    ]))
    return system, user


@dataclass
class ScoredVerdict:
    result: dict            # scoring_result.json-shaped
    passed: bool
    human_escalation: bool


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise RubricError(f"model response contained no JSON object: {text[:200]!r}")
    return json.loads(m.group(0))


def score_submission(rubric: dict, submission: Submission, model: ModelClient,
                     evidence_text: str, defense_text: str | None = None) -> ScoredVerdict:
    """Score one submission against a rubric using a model client."""
    rubric = load_rubric(rubric)
    system, user = build_prompt(rubric, submission, evidence_text, defense_text)
    raw = _extract_json(model.complete(system, user))

    max_score = max(int(l["score"]) for l in rubric["levels"])
    crit_by_id = {c["criterion_id"]: c for c in rubric["criteria"]}
    criterion_scores = []
    weighted = 0.0
    for c in rubric["criteria"]:
        cid = c["criterion_id"]
        entry = raw.get("criteria", {}).get(cid)
        if entry is None:
            raise RubricError(f"model omitted criterion {cid}")
        score = int(entry["score"])
        if not 0 <= score <= max_score:
            raise RubricError(f"criterion {cid}: score {score} outside 0..{max_score}")
        weighted += c["weight"] * (score / max_score)
        refs = entry.get("evidence_refs") or submission.artifact_refs()
        rationale = entry.get("rationale", "").strip()
        if not rationale:
            raise RubricError(f"criterion {cid}: scoring requires per-criterion rationale")
        criterion_scores.append({
            "criterion_id": cid,
            "score": score,
            "max_score": max_score,
            "rationale": rationale,
            "confidence": float(entry.get("confidence", 0.5)),
            "evidence_refs": list(refs),
        })

    passed = weighted >= rubric["pass_threshold"]
    in_band = abs(weighted - rubric["pass_threshold"]) <= rubric["escalation_band"]
    result = {
        "rubric_ref": f"{rubric['rubric_id']}@{rubric['version']}",
        "prompt_version": PROMPT_VERSION,
        "submission_id": submission.submission_id,
        "criterion_scores": criterion_scores,
        "weighted_score": round(weighted, 4),
        "passed": bool(passed),
        "human_escalation": bool(in_band),
        "verifier": {"kind": "model", "model": getattr(model, "model_name", "unknown")},
        "evidence_cited": sorted({r for cs in criterion_scores for r in cs["evidence_refs"]}),
    }
    errs = sorted(_SCHEMA_VALIDATOR.iter_errors(result), key=lambda e: list(e.absolute_path))
    if errs:
        raise RubricError("scoring result failed schema: " + errs[0].message)
    return ScoredVerdict(result=result, passed=passed, human_escalation=in_band)
