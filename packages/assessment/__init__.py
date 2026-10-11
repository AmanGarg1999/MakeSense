"""LL-05 Skill Verification Engine.

Evidence intake -> rubric scoring -> transfer/defense probes -> append-only
verification registry -> mastery-decay expiry clock.
See README.md and docs/research/skill-verification.md (LL-01)."""
from .capture import (CameraOcrAdapter, CaptureResult, InAppCaptureAdapter,
                      RepoAdapter, SandboxRunnerAdapter, VoiceAsrAdapter)
from .evidence import (EvidenceIntakeError, Submission, build_submission,
                       intake, validate_submission)
from .expiry import (FAMILY_INTERVALS, ExpiryStatus, build_recheck_task,
                     compute_status, count_clean_rechecks, next_interval_days)
from .probes import Probe, ProbeSet, defense_verdict, generate_probes, record_answer
from .registry import RegistryError, VerificationRegistry
from .rubric import PROMPT_VERSION, RubricError, load_rubric, score_submission
from .verifier import GradeOutcome, current_status, grade_submission as grade, tick_expiry

__all__ = [
    "EvidenceIntakeError", "Submission", "build_submission", "intake",
    "validate_submission", "CaptureResult", "VoiceAsrAdapter", "CameraOcrAdapter",
    "SandboxRunnerAdapter", "RepoAdapter", "InAppCaptureAdapter",
    "load_rubric", "score_submission", "RubricError", "PROMPT_VERSION",
    "generate_probes", "record_answer", "defense_verdict", "Probe", "ProbeSet",
    "VerificationRegistry", "RegistryError",
    "FAMILY_INTERVALS", "ExpiryStatus", "compute_status", "next_interval_days",
    "build_recheck_task", "count_clean_rechecks",
    "grade", "tick_expiry", "current_status", "GradeOutcome",
]
