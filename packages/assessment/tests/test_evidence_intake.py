"""LL-05 §1 evidence intake: each evidence type + the explain-only rejection."""
import pytest
from jsonschema import Draft202012Validator

from packages.assessment import evidence
from packages.assessment.evidence import EvidenceIntakeError

from helpers import sub_payload


def test_code_execution_intake():
    s = evidence.intake(sub_payload("code_execution"))
    assert s.kind == "code_execution"
    assert s.requires_performance
    assert any(r.startswith("sandbox:") for r in s.artifact_refs())


def test_code_execution_missing_execution_payload_rejected():
    p = sub_payload("code_execution")
    del p["evidence"]["execution"]
    with pytest.raises(EvidenceIntakeError, match="execution"):
        evidence.intake(p)


def test_media_recording_intake():
    s = evidence.intake(sub_payload("media_recording",
                                   artifacts=[{"ref": "blob:take.mp4",
                                               "media_type": "video/mp4",
                                               "captured_via": "voice_asr"}],
                                   transcript="played the piece cleanly from memory"))
    assert s.evidence["transcript"]


def test_media_recording_without_artifact_rejected():
    p = sub_payload("media_recording")
    p["evidence"].pop("artifacts", None)
    with pytest.raises(EvidenceIntakeError):
        evidence.intake(p)


def test_photo_intake():
    s = evidence.intake(sub_payload("photo",
                                    artifacts=[{"ref": "blob:workbench.jpg",
                                                "captured_via": "camera_ocr"}],
                                    ocr_text="dovetail joint, 12mm"))
    assert s.evidence["ocr_text"]


def test_project_repo_intake():
    s = evidence.intake(sub_payload("project_repo",
                                    repo={"url": "https://gh/user/proj",
                                          "head_sha": "b4d7551", "commit_count": 14,
                                          "author_commits": 12}))
    assert "https://gh/user/proj" in s.artifact_refs()


def test_in_app_capture_intake():
    s = evidence.intake(sub_payload("in_app_capture",
                                    performance={"completed": True, "metric": "accuracy",
                                                 "value": 0.91, "threshold": 0.85,
                                                 "environment": "track-app"}))
    assert s.requires_performance


def test_explanation_allowed_on_explain_rungs():
    s = evidence.intake(sub_payload("explanation", rung=("oral_defense",)))
    assert s.is_explain_only
    assert not s.requires_performance


def test_explain_only_rejected_on_performance_rung_schema_level():
    """ACCEPTANCE: no pass from theoretical/explain-only on a performance rung —
    rejected by the JSON Schema itself, not just app code."""
    p = sub_payload("explanation", rung=("artifact",))
    errs = list(Draft202012Validator(evidence.EVIDENCE_SCHEMA).iter_errors(p))
    assert errs, "schema must reject explain-only on performance rungs"
    with pytest.raises(EvidenceIntakeError, match="INTEGRITY"):
        evidence.intake(p)


def test_integrity_flag_derived_by_builder():
    p = sub_payload("explanation", rung=("performance",))
    assert p["requires_performance"] is True      # derived from rung types
    assert p["evidence"]["kind"] == "explanation"
    with pytest.raises(EvidenceIntakeError):
        evidence.validate_submission(p)
