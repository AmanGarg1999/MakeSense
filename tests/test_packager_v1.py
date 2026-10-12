"""LL-09c packager acceptance tests (offline, no DB).

Proves the mk-015/mk-016 rules:
1. Existing v0 packs (packs/dist manifest, legacy sample) validate UNCHANGED
   against the untouched v0 schema and load with back-compat level_target.
2. A new multi-level v1 sample pack passes with full level metadata.
3. Cycle detection: validator rejects A->B->A prerequisite graphs; acyclic
   graphs topo-sort with prerequisites first.
4. assessment_spec.rubric_ref is shape-only (LL-05 name@vX); bad refs reject.
5. License compliance per level (CC-NC disallowed on degree levels).
6. Delta/bridge pack generation (undergrad -> masters).
7. Packager level vocabulary == server PATHWAY_LEVELS (LL-09a source of truth).
"""
import copy
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))

from packages.packager import (
    PackValidationError,
    validate_manifest,
    validate_prereq_graph,
    normalize_prereq_graph,
    build_delta_pack,
    bridge_pack_manifest,
    license_allowed_for_level,
    check_pack_licenses,
    PACKER_LEVELS,
    DEFAULT_LEVEL_TARGET,
)
from packages.packager.manifest import _V0_VALIDATOR

SAMPLES = ROOT / "packs" / "samples"


def load_sample(name):
    return json.loads((SAMPLES / name / "manifest.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Back-compat: existing packs validate unchanged
# ---------------------------------------------------------------------------

def test_v0_schema_file_untouched():
    """v0 core schema still pins schema_version const "0" (never edited for v1)."""
    schema = json.loads((ROOT / "packs" / "schema" / "pack-manifest-v0.schema.json").read_text())
    assert schema["properties"]["schema_version"] == {"const": "0"}


def test_legacy_v0_sample_validates_unchanged():
    m = load_sample("legacy-v0-study-pack")
    errs = list(_V0_VALIDATOR.iter_errors(m))
    assert errs == [], f"v0 sample broke v0 schema: {errs}"
    pm = validate_manifest(m)
    assert pm.schema_version == "0"
    assert pm.level_target == DEFAULT_LEVEL_TARGET == ["micro", "certificate"]


def test_dist_pack_manifest_validates_unchanged():
    """The real built pack manifest in packs/dist must still validate (v0)."""
    p = ROOT / "packs" / "dist" / "manifest.verify.json"
    if not p.exists():
        pytest.skip("dist manifest not present")
    m = json.loads(p.read_text())
    if str(m.get("schema_version")) != "0":
        pytest.skip("dist manifest is not a v0 doc")
    errs = list(_V0_VALIDATOR.iter_errors(m))
    assert errs == [], f"dist pack broke v0 schema: {[e.message for e in errs]}"


# ---------------------------------------------------------------------------
# 2. New multi-level v1 sample pack
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "micro-python-foundations",
    "undergrad-data-foundations",
    "masters-research-methods",
])
def test_v1_samples_pass(name):
    pm = validate_manifest(load_sample(name))
    assert pm.schema_version == "1"
    assert set(pm.level_target) <= set(PACKER_LEVELS)
    assert pm.level_target


def test_multilevel_pack_serves_multiple_levels():
    pm = validate_manifest(load_sample("undergrad-data-foundations"))
    assert pm.serves("undergrad") and pm.serves("certificate")
    assert not pm.serves("phd")
    assert pm.prerequisites[0]["pack_id"] == "micro-python-foundations"
    assert pm.assessment_spec["type"] == "case_study"
    assert pm.credit_value == 3.0


def test_v1_rejects_unknown_level_and_bad_prereq():
    m = load_sample("micro-python-foundations")
    bad = copy.deepcopy(m); bad["level_target"] = ["bachelors"]
    with pytest.raises(PackValidationError):
        validate_manifest(bad)
    bad2 = copy.deepcopy(m); bad2["prerequisites"] = [{"pack_id": "micro-python-foundations"}]
    with pytest.raises(PackValidationError, match="itself"):
        validate_manifest(bad2)


# ---------------------------------------------------------------------------
# 3. Cycle detection (DAG)
# ---------------------------------------------------------------------------

def _mini(pack_id, prereqs):
    return validate_manifest({
        "schema_version": "1", "pack_id": pack_id, "version": "1.0.0",
        "title": pack_id, "created_at": "2026-10-12T09:00:00+00:00",
        "locale": "en-IN", "source": {"name": "t", "license": "CC-BY-SA-4.0"},
        "index": [{"id": f"{pack_id}/c1", "kind": "text", "chapter": "c",
                   "path": "x.json", "sha256": "0" * 64}],
        "encryption": {"payload": "aes-256-gcm"},
        "delta": {"delta_from": None, "changed_chunks": [], "removed_chunks": []},
        "stats": {"chunks": 1},
        "level_target": ["undergrad"],
        "prerequisites": [{"pack_id": p, "min_mastery": 0.8} for p in prereqs],
    })


def test_cycle_detected_and_rejected():
    a, b, c = _mini("cycle-a", ["cycle-c"]), _mini("cycle-b", ["cycle-a"]), _mini("cycle-c", ["cycle-b"])
    cycles = validate_prereq_graph([a, b, c])
    assert cycles, "A->C->B->A cycle must be detected"
    assert len(cycles[0]) >= 3
    with pytest.raises(PackValidationError):
        normalize_prereq_graph([a, b, c])


def test_self_cycle_rejected_in_manifest_validation():
    with pytest.raises(PackValidationError, match="itself"):
        _mini("self-a", ["self-a"])


def test_acyclic_graph_topo_orders_prereqs_first():
    adv = _mini("dag-advanced", ["dag-base"])
    base = _mini("dag-base", [])
    assert validate_prereq_graph([adv, base]) == []
    order = normalize_prereq_graph([adv, base])
    assert order.index("dag-base") < order.index("dag-advanced")


def test_real_samples_are_acyclic():
    ms = [validate_manifest(load_sample(n)) for n in
          ("micro-python-foundations", "undergrad-data-foundations", "masters-research-methods")]
    assert validate_prereq_graph(ms) == []


# ---------------------------------------------------------------------------
# 4. assessment_spec: opaque rubric_ref shape (LL-05 owns semantics)
# ---------------------------------------------------------------------------

def test_rubric_ref_shape_enforced():
    m = load_sample("micro-python-foundations")
    bad = copy.deepcopy(m); bad["assessment_spec"]["rubric_ref"] = "https://rubrics.internal/42"
    with pytest.raises(PackValidationError, match="rubric_ref"):
        validate_manifest(bad)
    ok = copy.deepcopy(m); ok["assessment_spec"]["rubric_ref"] = "py-foundations-l1@v2.1"
    assert validate_manifest(ok).assessment_spec["rubric_ref"].endswith("@v2.1")


def test_assessment_type_enum():
    m = copy.deepcopy(load_sample("masters-research-methods"))
    m["assessment_spec"]["type"] = "oral_exam"
    with pytest.raises(PackValidationError, match="assessment_spec.type"):
        validate_manifest(m)


# ---------------------------------------------------------------------------
# 5. License compliance per level
# ---------------------------------------------------------------------------

def test_nc_license_disallowed_on_degree_levels():
    assert license_allowed_for_level("CC-BY-NC-SA-4.0", "undergrad")
    assert not license_allowed_for_level("CC-BY-NC-SA-4.0", "masters")
    assert not license_allowed_for_level("CC-BY-NC-SA-4.0", "phd")
    assert license_allowed_for_level("CC-BY-SA-4.0", "phd")


def test_check_pack_licenses_flags_manifest():
    m = load_sample("masters-research-methods")
    nc = copy.deepcopy(m); nc["source"]["license"] = "CC-BY-NC-SA-4.0"
    problems = check_pack_licenses(nc)
    assert any("masters" in p for p in problems)
    assert check_pack_licenses(m) == []


# ---------------------------------------------------------------------------
# 6. Delta / bridge pack generation
# ---------------------------------------------------------------------------

def test_bridge_pack_undergrad_to_masters():
    base = load_sample("undergrad-data-foundations")
    adv = load_sample("masters-research-methods")
    delta = bridge_pack_manifest(base, adv)
    pm = validate_manifest(delta)                      # must pass v1 validation
    assert "masters" in pm.level_target and "undergrad" in pm.level_target
    assert pm.prerequisites[0]["pack_id"] == "undergrad-data-foundations"
    # delta carries only the advanced chunks the base lacks
    base_ids = {c["id"] for c in base["index"]}
    assert all(c["id"] not in base_ids for c in delta["index"])
    assert delta["delta"]["delta_from"] == "masters-research-methods"


def test_bridge_same_level_rejected():
    base = load_sample("undergrad-data-foundations")
    with pytest.raises(ValueError, match="not above"):
        bridge_pack_manifest(base, copy.deepcopy(base))


# ---------------------------------------------------------------------------
# 7. Level vocabulary stays in sync with LL-09a source of truth
# ---------------------------------------------------------------------------

def test_levels_match_server_enum():
    src = (ROOT / "server" / "pathway_service.py").read_text()
    import re
    m = re.search(r"PATHWAY_LEVELS\s*(?::[^=\n]+)?=\s*\[(.*?)\]", src, re.S)
    server_levels = re.findall(r"['\"](\w+)['\"]", m.group(1))
    assert server_levels == PACKER_LEVELS
