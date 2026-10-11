"""Transfer tests + oral-defense probes (LL-05 §3).

Anti-impostor-completion per LL-01 §3.2:
  - pattern 3 (viva-over-artifact): perturbation questions — "change requirement X",
    "why does removing this line break test Y", live-debug a seeded defect.
  - pattern 4 (transfer probe): near-but-novel context application. §6: keep
    transfer *near-to-mid* — far transfer is empirically weak, so probes must share
    the underlying structure while changing the surface.

Generation is model-assisted and prompt-versioned; every probe records the
artifact/evidence it was derived from. Probe answers attach to a submission's
`defense` block and are scored as E4 (defense) / E8 (transfer) evidence.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

PROBE_PROMPT_VERSION = "v1.0"

PROBE_KINDS = {"perturbation", "explain_artifact", "debug_seed", "transfer_application"}

SYSTEM_TEMPLATE = """You are designing verification probes for a skill assessment ({PROBE_PROMPT_VERSION}). \
Given the learner's artifact description and the skill's ladder rung, produce exactly \
{n_transfer} transfer-application probes (novel but structurally-similar context — \
near/mid transfer only, never far) and {n_defense} oral-defense probes over the artifact \
(perturbation "change requirement X and what breaks", explanation "why does this part \
work", or live-debug of a plausible seeded defect). Do not probe trivia the artifact \
doesn't contain.

Reply with ONLY a JSON object:
{"probes": [{"probe_id": "...", "kind": "perturbation|explain_artifact|debug_seed|transfer_application", \
"prompt": "...", "rubric_hint": "...", "derived_from": "<evidence ref the probe targets>"}]}
"""


@dataclass
class Probe:
    probe_id: str
    kind: str
    prompt: str
    rubric_hint: str
    derived_from: str
    answered: bool = False
    satisfactory: Optional[bool] = None
    transcript_ref: Optional[str] = None

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass
class ProbeSet:
    skill_tag: str
    level_index: int
    probes: list[Probe] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "probes_total": len(self.probes),
            "probes_answered": sum(1 for p in self.probes if p.answered),
            "satisfactory": (None if any(p.satisfactory is None for p in self.probes)
                             else all(bool(p.satisfactory) for p in self.probes)),
        }

    def as_defense_block(self) -> dict:
        """Shape for evidence Submission.defense."""
        refs = [p.transcript_ref for p in self.probes if p.transcript_ref]
        return {**self.summary(), "transcript_ref": refs[0] if refs else f"probes:{self.skill_tag}"}


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"probe model response had no JSON object: {text[:200]!r}")
    return json.loads(m.group(0))


def generate_probes(model, *, skill_tag: str, level_index: int, can_do: str,
                    artifact_description: str, evidence_refs: list[str],
                    n_transfer: int = 2, n_defense: int = 2) -> ProbeSet:
    """Model-assisted probe generation. `model` is a ModelClient (complete(system, user) -> str)."""
    system = (SYSTEM_TEMPLATE
              .replace("{PROBE_PROMPT_VERSION}", PROBE_PROMPT_VERSION)
              .replace("{n_transfer}", str(n_transfer))
              .replace("{n_defense}", str(n_defense)))
    user = "\n".join([
        f"SKILL: {skill_tag} (ladder level {level_index})",
        f"CAN-DO STATEMENT BEING VERIFIED: {can_do}",
        f"ARTIFACT DESCRIPTION: {artifact_description}",
        f"EVIDENCE REFS: {json.dumps(evidence_refs)}",
    ])
    raw = _extract_json(model.complete(system, user))
    ps = ProbeSet(skill_tag=skill_tag, level_index=level_index)
    for i, p in enumerate(raw.get("probes", [])):
        kind = p.get("kind", "explain_artifact")
        if kind not in PROBE_KINDS:
            raise ValueError(f"probe {i}: unknown kind {kind!r}")
        ps.probes.append(Probe(
            probe_id=p.get("probe_id") or f"prb_{uuid.uuid4().hex[:12]}",
            kind=kind,
            prompt=str(p["prompt"]).strip(),
            rubric_hint=str(p.get("rubric_hint", "")).strip(),
            derived_from=str(p.get("derived_from") or (evidence_refs[0] if evidence_refs
                                                       else f"artifact:{skill_tag}")),
        ))
    if not ps.probes:
        raise ValueError("model generated no probes")
    return ps


def record_answer(ps: ProbeSet, probe_id: str, satisfactory: bool,
                  transcript_ref: Optional[str] = None) -> ProbeSet:
    for p in ps.probes:
        if p.probe_id == probe_id:
            p.answered = True
            p.satisfactory = bool(satisfactory)
            p.transcript_ref = transcript_ref
            return ps
    raise KeyError(f"probe {probe_id} not in set")


def defense_verdict(ps: ProbeSet) -> dict:
    """Aggregate a probe set into the defense block. Unsatisfactory defense per
    LL-01 §3.3 escalates to the in-session re-creation rung — the verifier acts on
    'escalate'."""
    s = ps.summary()
    if s["satisfactory"] is None:
        return {**s, "outcome": "incomplete", "escalate": None}
    if s["satisfactory"]:
        return {**s, "outcome": "passed", "escalate": None}
    failed_kinds = {p.kind for p in ps.probes if not p.satisfactory}
    escalate = ("in_session" if {"perturbation", "debug_seed"} & failed_kinds
                else "defense")
    return {**s, "outcome": "failed", "escalate": escalate}
