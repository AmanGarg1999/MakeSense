"""Content Pack Format v1 manifest loader/validator (mk-015 extension, LL-09c).

Schema files live in packs/schema/:
  pack-manifest-v0.schema.json           — the original envelope (UNCHANGED;
                                           existing packs/dist packs must
                                           validate exactly as before)
  pack-manifest-v1-additions.schema.json — level metadata (level_target,
                                           prerequisites, credit_value,
                                           assessment_spec, estimated_hours,
                                           learning_outcomes) merged onto the v0
                                           core at load time (_compose_v1_schema)
                                           so the generations can't drift. All
                                           additions OPTIONAL => every valid v0
                                           manifest is a valid v1 manifest.

Back-compat rule (LL-09c card): a pack with no level fields loads with
level_target = ["micro", "certificate"].

assessment_spec.rubric_ref is an OPAQUE reference in the LL-05 format
`rubric_id@version` (see packages/assessment/schemas/rubric.json). The
verification engine owns rubric semantics; we validate the SHAPE only and
never resolve the reference.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "packs" / "schema"
CANONICAL_LEVELS = ["micro", "certificate", "undergrad", "masters", "phd", "mba"]
DEFAULT_LEVEL_TARGET = ["micro", "certificate"]  # v0 back-compat interpretation

# `name@vX` — must match the LL-05 scoring-result rubric_ref format.
RUBRIC_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*@v[0-9]+(\.[0-9]+)*$")

ASSESSMENT_TYPES = ["auto", "peer", "defense", "case_study"]
BLOOM_LEVELS = ["remember", "understand", "apply", "analyze", "evaluate", "create"]

_PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


class PackValidationError(ValueError):
    """Raised on schema violation, bad level metadata, or a prerequisite cycle."""


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _compose_v1_schema() -> dict:
    """v1 = v0 core (verbatim, never edited) + optional level-metadata fields.

    Merged at load time rather than duplicated so the two generations can never
    drift: v0's required envelope + additionalProperties:false applies, with the
    additive level fields folded into `properties` and schema_version widened
    to accept "0" | "1".
    """
    import copy

    v0 = copy.deepcopy(_load_schema("pack-manifest-v0.schema.json"))
    adds = _load_schema("pack-manifest-v1-additions.schema.json")
    for key in ("$schema", "$id", "title", "description"):
        v0.pop(key, None)
    v0["$id"] = "https://makesense.dev/schema/pack-manifest-v1.json"
    v0["title"] = "MakeSense content pack manifest v1 (Content Pack Format v1 + level metadata)"
    v0["properties"]["schema_version"] = {"enum": ["0", "1"]}
    v0["properties"].update(adds["properties"])
    return v0


_V0_SCHEMA = _load_schema("pack-manifest-v0.schema.json")
_V1_SCHEMA = _compose_v1_schema()
_V0_VALIDATOR = Draft202012Validator(_V0_SCHEMA)
_V1_VALIDATOR = Draft202012Validator(_V1_SCHEMA)


@dataclass
class PackManifest:
    """Normalized view of a pack manifest after validation."""
    pack_id: str
    version: str
    title: str
    schema_version: str
    raw: Dict[str, Any] = field(repr=False)
    level_target: List[str] = field(default_factory=lambda: list(DEFAULT_LEVEL_TARGET))
    prerequisites: List[Dict[str, Any]] = field(default_factory=list)
    credit_value: float = 0.0
    estimated_hours: Optional[float] = None
    assessment_spec: Optional[Dict[str, Any]] = None
    learning_outcomes: List[Dict[str, Any]] = field(default_factory=list)

    def serves(self, level: str) -> bool:
        return level in self.level_target


def validate_manifest(payload: Dict[str, Any]) -> PackManifest:
    """Schema-validate then semantically validate one manifest.

    A schema_version == "0" document is validated against the ORIGINAL v0
    schema first (unchanged acceptance criterion: existing packs validate
    exactly as before), then checked for level metadata as if optional.
    A "1" document validates against the v1 schema.
    """
    sv = str(payload.get("schema_version", ""))
    if sv == "0":
        errs = sorted(_V0_VALIDATOR.iter_errors(payload), key=lambda e: list(e.absolute_path))
    elif sv == "1":
        errs = sorted(_V1_VALIDATOR.iter_errors(payload), key=lambda e: list(e.absolute_path))
    else:
        raise PackValidationError(f"unsupported schema_version: {sv!r} (expected '0' or '1')")
    if errs:
        raise PackValidationError("; ".join(
            f"$.{'.'.join(map(str, e.absolute_path))}: {e.message}" for e in errs[:5]))

    # ---- level metadata (optional in both generations) ----
    level_target = payload.get("level_target", DEFAULT_LEVEL_TARGET)
    bad = [lvl for lvl in level_target if lvl not in CANONICAL_LEVELS]
    if bad:
        raise PackValidationError(
            f"level_target contains unknown levels {bad} (canonical: {CANONICAL_LEVELS})")
    if not level_target:
        raise PackValidationError("level_target must be a non-empty array")

    prereqs = payload.get("prerequisites", [])
    seen_prereq: Set[str] = set()
    for i, p in enumerate(prereqs):
        pid = p.get("pack_id", "")
        if not _PACK_ID_RE.match(pid):
            raise PackValidationError(f"prerequisites[{i}].pack_id invalid: {pid!r}")
        if pid == payload["pack_id"]:
            raise PackValidationError(f"prerequisites[{i}]: pack cannot depend on itself ({pid})")
        if pid in seen_prereq:
            raise PackValidationError(f"duplicate prerequisite pack_id: {pid}")
        seen_prereq.add(pid)
        mm = p.get("min_mastery", 0.0)
        if not (isinstance(mm, (int, float)) and 0 <= mm <= 1):
            raise PackValidationError(f"prerequisites[{i}].min_mastery must be in [0,1] (got {mm!r})")
        lc = p.get("level_context")
        if lc is not None and lc not in CANONICAL_LEVELS:
            raise PackValidationError(
                f"prerequisites[{i}].level_context {lc!r} not a canonical level")

    spec = payload.get("assessment_spec")
    if spec is not None:
        t = spec.get("type")
        if t not in ASSESSMENT_TYPES:
            raise PackValidationError(
                f"assessment_spec.type {t!r} not in {ASSESSMENT_TYPES}")
        ref = spec.get("rubric_ref", "")
        if not RUBRIC_REF_RE.match(ref or ""):
            raise PackValidationError(
                f"assessment_spec.rubric_ref {ref!r} must look like 'rubric_id@version' "
                "(LL-05 format; shape-only, we never resolve it)")
        pt = spec.get("passing_threshold")
        if not (isinstance(pt, (int, float)) and 0 <= pt <= 1):
            raise PackValidationError("assessment_spec.passing_threshold must be in [0,1]")

    for i, o in enumerate(payload.get("learning_outcomes", [])):
        bl = o.get("bloom_level")
        if bl not in BLOOM_LEVELS:
            raise PackValidationError(
                f"learning_outcomes[{i}].bloom_level {bl!r} not in {BLOOM_LEVELS}")
        if not o.get("competency_id") or not o.get("measurable_criterion"):
            raise PackValidationError(f"learning_outcomes[{i}] needs competency_id + measurable_criterion")

    eh = payload.get("estimated_hours")
    if eh is not None and (not isinstance(eh, (int, float)) or eh < 0):
        raise PackValidationError("estimated_hours must be a non-negative number")
    cv = payload.get("credit_value", 0)
    if not isinstance(cv, (int, float)) or cv < 0:
        raise PackValidationError("credit_value must be a non-negative number")

    return PackManifest(
        pack_id=payload["pack_id"],
        version=payload["version"],
        title=payload["title"],
        schema_version=sv,
        raw=payload,
        level_target=list(level_target),
        prerequisites=list(prereqs),
        credit_value=float(cv),
        estimated_hours=float(eh) if eh is not None else None,
        assessment_spec=spec,
        learning_outcomes=list(payload.get("learning_outcomes", [])),
    )


def load_manifest(path: Path) -> PackManifest:
    return validate_manifest(json.loads(Path(path).read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Prerequisite DAG: cycle detection across a set of packs
# ---------------------------------------------------------------------------

def validate_prereq_graph(manifests: List[PackManifest]) -> List[List[str]]:
    """Return every prerequisite cycle found (DFS on pack_id edges), [] if acyclic.

    'prerequisites' declare a directed acyclic graph: edge pack -> prerequisite
    (a pack must be completed before its dependant). A cycle would make a
    pathway unsatisfiable, so the packager must reject it at assembly time.
    """
    edges = {m.pack_id: [p["pack_id"] for p in m.prerequisites] for m in manifests}
    cycles: List[List[str]] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {pid: WHITE for pid in edges}
    stack: List[str] = []

    def dfs(node: str) -> None:
        color[node] = GRAY
        stack.append(node)
        for dep in edges.get(node, []):
            if dep not in color:            # external/unknown pack id — no cycle through it here
                continue
            if color[dep] == GRAY:          # back edge -> cycle
                idx = stack.index(dep)
                cycles.append(stack[idx:] + [dep])
            elif color[dep] == WHITE:
                dfs(dep)
        stack.pop()
        color[node] = BLACK

    for pid in edges:
        if color[pid] == WHITE:
            dfs(pid)
    return cycles


def normalize_prereq_graph(manifests: List[PackManifest]) -> List[str]:
    """Topological order (prereqs first). Raises on cycle. Kahn's algorithm."""
    ids = {m.pack_id for m in manifests}
    indeg = {pid: 0 for pid in ids}
    dependents: Dict[str, List[str]] = {pid: [] for pid in ids}
    for m in manifests:
        for p in m.prerequisites:
            dep = p["pack_id"]
            if dep in ids:
                indeg[m.pack_id] += 1
                dependents[dep].append(m.pack_id)
    # deterministic: sort by pack_id
    ready = sorted(pid for pid, d in indeg.items() if d == 0)
    order: List[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for nxt in sorted(dependents[node]):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)
        ready.sort()
    if len(order) != len(ids):
        remaining = sorted(ids - set(order))
        raise PackValidationError(f"prerequisite cycle among packs: {remaining}")
    return order
