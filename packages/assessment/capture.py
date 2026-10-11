"""Multimodal capture adapters (reuse of mk-019 camera OCR / handwriting / voice).

Each adapter normalizes raw captures into the `evidence` shapes consumed by
`evidence.build_submission`. They call out to capture pipelines via injected
callables so tests run without the real models; production wiring points the
ASR/OCR callables at the existing multimodal endpoints and the sandbox runner
at the code-execution service.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .evidence import sha256_bytes


@dataclass
class CaptureResult:
    kind: str                                  # evidence kind for build_submission
    artifacts: list[dict] = field(default_factory=list)
    transcript: Optional[str] = None
    ocr_text: Optional[str] = None
    execution: Optional[dict] = None           # code_execution payload
    performance: Optional[dict] = None         # in_app_capture payload
    repo: Optional[dict] = None                # project_repo payload
    captured_via: str = "direct_upload"

    def as_evidence_kwargs(self) -> dict[str, Any]:
        """Expand into keyword args for evidence.build_submission()."""
        return {
            "kind": self.kind,
            "artifacts": self.artifacts or None,
            "transcript": self.transcript,
            "ocr_text": self.ocr_text,
            "execution": self.execution,
            "performance": self.performance,
            "repo": self.repo,
        }


class VoiceAsrAdapter:
    """Audio/video recording -> transcript (mk-019 voice capture / faster-whisper)."""

    def __init__(self, asr: Callable[[bytes], str]):
        self._asr = asr

    def capture(self, media: bytes, ref: str, media_type: str = "audio/mpeg") -> CaptureResult:
        return CaptureResult(
            kind="media_recording",
            artifacts=[{"ref": ref, "sha256": sha256_bytes(media), "media_type": media_type,
                        "captured_via": "voice_asr"}],
            transcript=self._asr(media),
            captured_via="voice_asr",
        )


class CameraOcrAdapter:
    """Photo of physical work / handwriting -> extracted text (mk-019 camera OCR)."""

    def __init__(self, ocr: Callable[[bytes], str]):
        self._ocr = ocr

    def capture(self, image: bytes, ref: str, handwriting: bool = False) -> CaptureResult:
        return CaptureResult(
            kind="photo",
            artifacts=[{"ref": ref, "sha256": sha256_bytes(image), "media_type": "image/jpeg",
                        "captured_via": "handwriting" if handwriting else "camera_ocr"}],
            ocr_text=self._ocr(image),
            captured_via="handwriting" if handwriting else "camera_ocr",
        )


class SandboxRunnerAdapter:
    """Code-that-must-execute: run in sandbox + execute unit tests, capture outcome."""

    def __init__(self, run: Callable[[dict], dict]):
        self._run = run

    def capture(self, source_ref: str, test_spec: dict,
                sandbox: str = "docker:py311-sandbox") -> CaptureResult:
        result = self._run({"source_ref": source_ref, "tests": test_spec, "sandbox": sandbox})
        return CaptureResult(
            kind="code_execution",
            artifacts=[{"ref": source_ref, "captured_via": "sandbox_runner"}],
            execution=result,
            captured_via="sandbox_runner",
        )


class RepoAdapter:
    """Project repo evidence: URL + HEAD sha + commit authorship stats (E5)."""

    def capture(self, url: str, head_sha: str, commit_count: int, author_commits: int) -> CaptureResult:
        return CaptureResult(
            kind="project_repo",
            repo={"url": url, "head_sha": head_sha,
                  "commit_count": commit_count, "author_commits": author_commits},
            captured_via="repo_fetch",
        )


class InAppCaptureAdapter:
    """In-app performance capture: task completed + metric in the practice surface."""

    def capture(self, environment: str, metric: str, value: Any, threshold: Any,
                completed: bool) -> CaptureResult:
        return CaptureResult(
            kind="in_app_capture",
            performance={"completed": completed, "metric": metric, "value": value,
                         "threshold": threshold, "environment": environment},
            captured_via="in_app_recorder",
        )
