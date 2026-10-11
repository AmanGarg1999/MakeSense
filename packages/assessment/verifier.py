"""End-to-end verification orchestration (LL-05).

Flow: evidence intake -> integrity re-check -> rubric scoring -> LL-01 §3.3
escalation ladder -> verdict -> append to registry -> expiry clock.

Escalation ladder (logged per event, never a verdict by itself):
    artifact (routine)  ->  defense request  ->  in-session re-creation
                        ->  provisional flag + spaced re-check
AI-detector output (`provenance.process_signals.ai_detector_prior`) is only an
anomaly prior that raises the rung — LL-01 §3.1.

Registry events carry their own expires_at; a rung's status (current/stale/
expired) is always DERIVED from the latest event (append-only). An expired rung
downgrades to provisional via a new event + a queued re-verify task — never an
UPDATE (LL-01 §4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from . import expiry
from .evidence import (EvidenceIntakeError, PERFORMANCE_RUNG_TYPES, Submission,
                       intake)
from .probes import ProbeSet
from .registry import VerificationRegistry
from .rubric import ScoredVerdict, score_submission

# evidence kind -> LL-01 §1 evidence class
KIND_TO_CLASS = {
    "code_execution": "E3",       # sandboxed, auto-scoreable simulation
    "media_recording": "E1",      # artifact (recording)
    "photo": "E1",                # artifact (physical work)
    "project_repo": "E5",         # process evidence (commit graph)
    "in_app_capture": "E2",       # performance in environment
    "explanation": "E4",          # viva-style, ONLY when the rung asks for it
    "quiz_result": "E1",          # weakest product evidence; quiz-only rungs
}

ANOMALY_DETECTOR_PRIOR = 0.7      # raises artifact -> defense
IMPLAUSIBLE_FAST_S = 30.0         # finished a performance task < 30s -> anomaly


@dataclass
class GradeOutcome:
    verdict: str                        # verified | reinforced | provisional | rejected
    status: str                         # registry-derived: current | stale | expired | provisional
    event_id: Optional[str] = None
    scoring: Optional[dict] = None
    human_escalation: bool = False
    escalation_rung: str = "artifact"
    requeue: Optional[dict] = None      # re-verify task when verdict provisional
    reasons: list[str] = field(default_factory=list)


def _evidence_class(sub: Submission) -> str:
    return KIND_TO_CLASS.get(sub.kind, "E1")


def _anomaly_signals(sub: Submission) -> list[str]:
    """Anomaly priors — trigger a defense rung, are NEVER verdicts (LL-01 §3.1)."""
    flags: list[str] = []
    ps = sub.provenance.get("process_signals", {}) or {}
    prior = ps.get("ai_detector_prior")
    if prior is not None and float(prior) >= ANOMALY_DETECTOR_PRIOR:
        flags.append(f"ai_detector_prior {prior} >= {ANOMALY_DETECTOR_PRIOR}")
    elapsed = ps.get("elapsed_s")
    if (elapsed is not None and float(elapsed) < IMPLAUSIBLE_FAST_S
            and sub.requires_performance):
        flags.append(f"implausible time profile: {elapsed}s for a performance task")
    return flags


def grade_submission(
    payload: dict,
    *,
    rubric: Optional[dict],
    model: Any,                      # ModelClient (rubric scoring); unused if rubric None
    registry: VerificationRegistry,
    evidence_text: str = "",
    family: Optional[str] = None,
    track_id: Optional[str] = None,
) -> GradeOutcome:
    """Grade one submission end-to-end and append the resulting event."""
    # 1. Intake (+ schema-level integrity rule).
    try:
        sub = intake(payload)
    except EvidenceIntakeError as e:
        if "INTEGRITY" in str(e) or (payload.get("evidence", {}).get("kind") == "explanation"
                                     and PERFORMANCE_RUNG_TYPES
                                     & set(payload.get("rung_evidence_types", []))):
            # Rejected explain-only attempts are recorded too — append-only audit.
            ev = registry.append(
                user_id=payload.get("user_id", "?"),
                skill_tag=payload.get("skill_tag", "?"),
                level_index=int(payload.get("level_index", 0)),
                verdict="rejected", verifier={"kind": "deterministic"},
                submission_id=payload.get("submission_id"),
                evidence_refs=[a.get("ref") for a in
                               (payload.get("evidence", {}).get("artifacts") or [])],
                notes=f"integrity: explain-only on performance rung — {e}",
            )
            return GradeOutcome(verdict="rejected", status="provisional",
                                event_id=ev.event_id,
                                reasons=["explain-only cannot satisfy a performance rung"])
        raise

    # 2. Defense-in-depth integrity re-check (schema already gates this).
    if sub.is_explain_only and sub.requires_performance:
        raise EvidenceIntakeError("INTEGRITY: explain-only submission on a performance rung")

    # 3. Scoring: rubric (model-assisted) or deterministic (code execution outcome).
    scored: Optional[ScoredVerdict] = None
    passed: bool
    reasons: list[str] = []
    if rubric is not None:
        scored = score_submission(rubric, sub, model, evidence_text)
        passed = scored.passed
        reasons += [f"weighted {scored.result['weighted_score']:.2f}",
                    f"rubric {scored.result['rubric_ref']}"]
    elif sub.kind == "code_execution":
        ex = sub.evidence["execution"]
        passed = bool(ex.get("ran")) and ex["tests_passed"] >= ex["tests_total"] > 0
        reasons.append(f"tests {ex['tests_passed']}/{ex['tests_total']}")
    elif sub.kind == "in_app_capture":
        perf = sub.evidence["performance"]
        passed = bool(perf.get("completed"))
        reasons.append("in-app task completed" if passed else "in-app task not completed")
    elif sub.kind == "project_repo":
        repo = sub.evidence["repo"]
        passed = repo.get("author_commits", 0) >= 1
        reasons.append(f"author commits {repo.get('author_commits', 0)}")
    else:
        raise EvidenceIntakeError(
            f"no rubric provided and kind {sub.kind!r} has no deterministic scorer")

    if not passed:
        ev = registry.append(
            user_id=sub.user_id, skill_tag=sub.skill_tag, level_index=sub.level_index,
            track_id=track_id or sub.track_id, verdict="rejected",
            primary_evidence=_evidence_class(sub), evidence_refs=sub.artifact_refs(),
            submission_id=sub.submission_id, verifier=_verifier(scored),
            scoring=scored.result if scored else None,
            rubric_ref=_rubric_ref(scored), prompt_version=_prompt_version(scored),
            verified_at=sub.provenance["timestamp"],
            notes="; ".join(reasons))
        return GradeOutcome(verdict="rejected", status="provisional", event_id=ev.event_id,
                            scoring=scored.result if scored else None, reasons=reasons)

    # 4. Escalation ladder: anomalies and defense-type rungs gate 'verified'.
    rung = "artifact"
    requeue = None
    anomalies = _anomaly_signals(sub)
    need_defense = "oral_defense" in sub.rung_evidence_types or "transfer_test" in sub.rung_evidence_types
    defense_state = sub.evidence.get("kind") and sub.defense

    if anomalies or need_defense:
        rung = "defense"
        if defense_state is None:
            if anomalies and not need_defense:
                # artifact passes routine scoring but an anomaly prior says: ask for defense
                verdict = "provisional"
                requeue = {"type": "defense_request",
                           "user_id": str(sub.user_id), "skill_tag": sub.skill_tag,
                           "level_index": sub.level_index,
                           "reason": "; ".join(anomalies),
                           "created_at": datetime.now(timezone.utc).isoformat()}
            else:
                verdict = "provisional"
                requeue = {"type": "defense_request",
                           "user_id": str(sub.user_id), "skill_tag": sub.skill_tag,
                           "level_index": sub.level_index,
                           "reason": "rung requires oral defense / transfer probe",
                           "created_at": datetime.now(timezone.utc).isoformat()}
        else:
            # Defense answers arrive pre-aggregated (ProbeSet.as_defense_block()).
            d = sub.defense
            if d.get("satisfactory") is False:
                verdict, rung = "rejected", "in_session"
                requeue = {"type": "in_session_recreation",
                           "user_id": str(sub.user_id), "skill_tag": sub.skill_tag,
                           "level_index": sub.level_index,
                           "reason": "defense unsatisfactory — live re-creation required",
                           "created_at": datetime.now(timezone.utc).isoformat()}
            elif d.get("satisfactory") is None:
                verdict, rung = "provisional", "defense"
                requeue = {"type": "defense_request", "user_id": str(sub.user_id),
                           "skill_tag": sub.skill_tag, "level_index": sub.level_index,
                           "reason": "defense incomplete",
                           "created_at": datetime.now(timezone.utc).isoformat()}
            else:
                verdict = "verified"
    else:
        verdict = "verified"

    # 5. Reinforced? A spaced re-verification (intent='recheck') that passes cleanly.
    latest = registry.latest(sub.user_id, sub.skill_tag, sub.level_index)
    is_recheck = payload.get("intent") == "recheck"
    if verdict == "verified" and is_recheck:
        verdict = "reinforced"

    # 6. Expiry clock.
    fam = expiry.family_for(sub.skill_tag, family)
    hist = [h.as_dict() for h in registry.history(sub.user_id, sub.skill_tag, sub.level_index)]
    clean = expiry.count_clean_rechecks(hist) + (1 if is_recheck else 0)
    verified_at = sub.provenance["timestamp"]
    expires_at = (expiry.next_due(verified_at, fam, clean)
                  if verdict in ("verified", "reinforced") else None)

    ev = registry.append(
        user_id=sub.user_id, skill_tag=sub.skill_tag, level_index=sub.level_index,
        track_id=track_id or sub.track_id, verdict=verdict,
        primary_evidence=_evidence_class(sub),
        corroborating=(["E4"] if sub.defense else None),
        evidence_refs=sub.artifact_refs(), submission_id=sub.submission_id,
        verifier=_verifier(scored), scoring=scored.result if scored else None,
        rubric_ref=_rubric_ref(scored), prompt_version=_prompt_version(scored),
        escalation_rung=rung, verified_at=verified_at, expires_at=expires_at,
        recheck_of=payload.get("recheck_of") or (latest.event_id if (is_recheck and latest) else None),
        supersedes=latest.event_id if (verdict == "reinforced" and latest) else None,
        notes="; ".join(reasons + anomalies))
    return GradeOutcome(
        verdict=verdict,
        status="current" if verdict in ("verified", "reinforced") else "provisional",
        event_id=ev.event_id, scoring=scored.result if scored else None,
        human_escalation=bool(scored and scored.human_escalation),
        escalation_rung=rung, requeue=requeue, reasons=reasons + anomalies)


def grade_probe_answers(ps: ProbeSet, *, model: Any,
                        rubric_hint_text: str = "") -> dict:
    """Score a completed probe set: each answer gets a satisfactory flag from the
    model. Returns the defense block for attachment to a submission."""
    from .probes import record_answer  # local import avoids cycle at module load
    for p in ps.probes:
        if p.answered:
            continue
        raw = model.complete(
            "You judge an oral-defense/transfer answer against the probe's rubric hint. "
            "Reply ONLY JSON: {\"satisfactory\": true|false, \"reason\": \"...\"}",
            f"PROBE ({p.kind}): {p.prompt}\nRUBRIC HINT: {p.rubric_hint}\n{rubric_hint_text}")
        import json as _json, re as _re
        m = _re.search(r"\{.*\}", raw, _re.DOTALL)
        data = _json.loads(m.group(0)) if m else {"satisfactory": False, "reason": "unparseable"}
        record_answer(ps, p.probe_id, bool(data.get("satisfactory")),
                      transcript_ref=data.get("transcript_ref"))
    return ps.as_defense_block()


def tick_expiry(registry: VerificationRegistry, *, now: Optional[str] = None,
                family: Optional[str] = None) -> list[GradeOutcome]:
    """Run the decay clock over the registry: expired rungs get a NEW provisional
    event appended + a re-verify task queued (never an UPDATE)."""
    outcomes: list[GradeOutcome] = []
    now_iso = now or datetime.now(timezone.utc).isoformat()
    for ev in registry.all_latest():
        if ev.verdict not in ("verified", "reinforced") or not ev.expires_at:
            continue
        hist = [h.as_dict() for h in registry.history(ev.user_id, ev.skill_tag, ev.level_index)]
        clean = expiry.count_clean_rechecks(hist)
        st = expiry.compute_status(
            user_id=ev.user_id, skill_tag=ev.skill_tag, level_index=ev.level_index,
            latest_verdict=ev.verdict, verified_at=ev.verified_at,
            expires_at=ev.expires_at, clean_rechecks=clean, track_id=ev.track_id,
            family=family, now=now_iso)
        if st.status == "expired":
            new_ev = registry.append(
                user_id=ev.user_id, skill_tag=ev.skill_tag, level_index=ev.level_index,
                track_id=ev.track_id, verdict="provisional",
                verifier={"kind": "deterministic"}, evidence_refs=ev.evidence_refs,
                verified_at=ev.verified_at, notes="verification lapsed (decay clock)",
                escalation_rung="provisional_flag")
            task = st.recheck_task or expiry.build_recheck_task(
                user_id=ev.user_id, skill_tag=ev.skill_tag, level_index=ev.level_index,
                track_id=ev.track_id, family=expiry.family_for(ev.skill_tag, family),
                clean_rechecks=clean)
            outcomes.append(GradeOutcome(verdict="provisional", status="expired",
                                         event_id=new_ev.event_id, requeue=task,
                                         reasons=["expiry clock: due_at passed + grace"]))
        elif st.status == "stale":
            outcomes.append(GradeOutcome(verdict=ev.verdict, status="stale",
                                         event_id=ev.event_id,
                                         reasons=[f"re-check due {st.due_at}"]))
    return outcomes


def current_status(registry: VerificationRegistry, user_id: Any, skill_tag: str,
                   level_index: int, *, family: Optional[str] = None,
                   now: Optional[str] = None) -> str:
    """Derived lifecycle state for a rung (LL-01 §7 seed): unverified / provisional /
    current / stale / expired."""
    ev = registry.latest(user_id, skill_tag, level_index)
    if ev is None:
        return "unverified"
    if ev.verdict not in ("verified", "reinforced"):
        return "provisional" if ev.verdict == "provisional" else "unverified"
    if not ev.expires_at:
        return "current"
    hist = [h.as_dict() for h in registry.history(user_id, skill_tag, level_index)]
    clean = expiry.count_clean_rechecks(hist)
    return expiry.compute_status(
        user_id=user_id, skill_tag=skill_tag, level_index=level_index,
        latest_verdict=ev.verdict, verified_at=ev.verified_at, expires_at=ev.expires_at,
        clean_rechecks=clean, track_id=ev.track_id, family=family,
        now=now or datetime.now(timezone.utc).isoformat()).status


def _verifier(scored: Optional[ScoredVerdict]) -> dict:
    if scored is None:
        return {"kind": "deterministic"}
    return dict(scored.result["verifier"])


def _rubric_ref(scored: Optional[ScoredVerdict]) -> Optional[str]:
    return scored.result["rubric_ref"] if scored else None


def _prompt_version(scored: Optional[ScoredVerdict]) -> Optional[str]:
    return scored.result.get("prompt_version") if scored else None
