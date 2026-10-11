"""Evidence intake (LL-05 §1).

Validates artifact submissions against schemas/evidence_submission.json.
Enforces the schema-level integrity rule (also re-checked here for a clear error):
a ladder rung whose evidence types are performance-grade can NEVER be attempted
with an explain-only submission.

Evidence kinds:
  - code_execution   : code that must execute (sandbox run + unit test outcome)
  - media_recording  : audio/video recording (ASR transcript via mk-019 voice capture)
  - photo            : photo of physical work (camera OCR / handwriting via mk-019)
  - project_repo     : repo reference with commit authorship stats
  - in_app_capture   : in-app performance capture (metrics + environment)
  - explanation      : theoretical / explain-only  -> never satisfies performance rungs
  - quiz_result      : quiz-only rungs
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

# Evidence types on a ladder rung (LL-02 skill_ladders.evidence_types) that demand
# performance — an explanation cannot ground them (Miller 'shows/does', work sampling).
PERFORMANCE_RUNG_TYPES = {
    "artifact", "project", "performance", "in_app", "simulation", "transfer_test",
}
EXPLAIN_ONLY_KINDS = {"explanation"}


def _schema(name: str) -> dict:
    with open(SCHEMA_DIR / name, "r", encoding="utf-8") as fh:
        return json.load(fh)


EVIDENCE_SCHEMA = _schema("evidence_submission.json")
_VALIDATOR = Draft202012Validator(EVIDENCE_SCHEMA)


class EvidenceIntakeError(ValueError):
    """Raised for a submission that cannot be accepted."""

    def __init__(self, message: str, errors: Optional[list[str]] = None):
        super().__init__(message)
        self.errors = errors or [message]


@dataclass
class Submission:
    submission_id: str
    user_id: Any
    skill_tag: str
    level_index: int
    rung_evidence_types: list[str]
    evidence: dict
    provenance: dict
    track_id: Optional[str] = None
    defense: Optional[dict] = None

    @property
    def kind(self) -> str:
        return self.evidence["kind"]

    @property
    def is_explain_only(self) -> bool:
        return self.kind in EXPLAIN_ONLY_KINDS

    @property
    def requires_performance(self) -> bool:
        return bool(PERFORMANCE_RUNG_TYPES.intersection(self.rung_evidence_types))

    def artifact_refs(self) -> list[str]:
        refs = [a["ref"] for a in self.evidence.get("artifacts", [])]
        if "repo" in self.evidence:
            refs.append(self.evidence["repo"].get("url", "repo:unknown"))
        if "execution" in self.evidence:
            refs.append(f"sandbox:{self.evidence['execution'].get('sandbox', 'run')}")
        if "performance" in self.evidence:
            refs.append(f"in_app:{self.evidence['performance'].get('environment', 'capture')}")
        return refs or [f"submission:{self.submission_id}"]

    def to_dict(self) -> dict:
        out = {
            "submission_id": self.submission_id,
            "user_id": self.user_id,
            "skill_tag": self.skill_tag,
            "level_index": self.level_index,
            "rung_evidence_types": self.rung_evidence_types,
            "evidence": self.evidence,
            "provenance": self.provenance,
        }
        if self.track_id:
            out["track_id"] = self.track_id
        if self.defense:
            out["defense"] = self.defense
        return out


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def new_submission_id() -> str:
    return "sub_" + uuid.uuid4().hex[:16]


def build_submission(
    *,
    user_id: Any,
    skill_tag: str,
    level_index: int,
    rung_evidence_types: list[str],
    kind: str,
    artifacts: Optional[list[dict]] = None,
    execution: Optional[dict] = None,
    performance: Optional[dict] = None,
    repo: Optional[dict] = None,
    transcript: Optional[str] = None,
    ocr_text: Optional[str] = None,
    environment: str = "unknown",
    submitted_at: Optional[str] = None,
    process_signals: Optional[dict] = None,
    defense: Optional[dict] = None,
    track_id: Optional[str] = None,
    submission_id: Optional[str] = None,
) -> dict:
    """Convenience builder producing a schema-shaped submission payload."""
    evidence: dict[str, Any] = {"kind": kind}
    if artifacts:
        evidence["artifacts"] = artifacts
    if execution:
        evidence["execution"] = execution
    if performance:
        evidence["performance"] = performance
    if repo:
        evidence["repo"] = repo
    if transcript is not None:
        evidence["transcript"] = transcript
    if ocr_text is not None:
        evidence["ocr_text"] = ocr_text
    provenance: dict[str, Any] = {
        "timestamp": submitted_at or datetime.now(timezone.utc).isoformat(),
        "environment": environment,
    }
    if process_signals:
        provenance["process_signals"] = process_signals
    return {
        "submission_id": submission_id or new_submission_id(),
        "user_id": user_id,
        "skill_tag": skill_tag,
        "level_index": level_index,
        "rung_evidence_types": rung_evidence_types,
        "requires_performance": bool(PERFORMANCE_RUNG_TYPES.intersection(rung_evidence_types)),
        "evidence": evidence,
        "provenance": provenance,
        **({"track_id": track_id} if track_id else {}),
        **({"defense": defense} if defense else {}),
    }


def validate_submission(payload: dict) -> Submission:
    """Validate a raw payload; raise EvidenceIntakeError listing all schema errors.

    The performance/explain-only rule is enforced by the schema's if/then block;
    this wrapper adds a dedicated message when that is the failing condition.
    """
    errors = sorted(_VALIDATOR.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        messages = []
        for err in errors:
            path = "$" + "".join(f"[{p!r}]" for p in err.absolute_path)
            messages.append(f"{path}: {err.message}")
        # Friendly re-check of the integrity rule for a clear headline message.
        rung_types = set(payload.get("rung_evidence_types", []))
        kind = payload.get("evidence", {}).get("kind")
        if kind == "explanation" and PERFORMANCE_RUNG_TYPES & rung_types:
            messages.insert(
                0,
                "INTEGRITY: explain-only submission cannot satisfy a performance-grade "
                f"rung (rung requires one of {sorted(PERFORMANCE_RUNG_TYPES & rung_types)})",
            )
        raise EvidenceIntakeError("; ".join(messages[:5]), errors=messages)
    return Submission(
        submission_id=payload["submission_id"],
        user_id=payload["user_id"],
        skill_tag=payload["skill_tag"],
        level_index=payload["level_index"],
        rung_evidence_types=payload["rung_evidence_types"],
        evidence=payload["evidence"],
        provenance=payload["provenance"],
        track_id=payload.get("track_id"),
        defense=payload.get("defense"),
    )


def intake(payload: dict) -> Submission:
    """Public intake entrypoint: validate and return the typed Submission."""
    return validate_submission(payload)
