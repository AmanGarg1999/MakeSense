"""Level-specific delta pack generation (mk-016, LL-09c).

A delta pack carries ONLY the content that bridges a learner from one pathway
level to the next (e.g. undergrad -> masters bridge). The chunk bodies are
envelope-managed (mspack AES payloads); the delta manifest references chunk
ids by index entry, never duplicates content.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .levels import level_rank
from .manifest import DEFAULT_LEVEL_TARGET


def _chunk_ids(manifest: Dict[str, Any]) -> List[str]:
    return [c["id"] for c in manifest.get("index", [])]


def build_delta_pack(
    base_manifest: Dict[str, Any],
    advanced_manifest: Dict[str, Any],
    *,
    pack_id: str,
    version: str = "1.0.0",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Delta = chunks present in the advanced pack that the base pack lacks.

    Delta chunk entries carry base/advanced provenance in `chapter` labels only
    (schema v0 index entries are additionalProperties:false), so the index keeps
    the exact v0 shape. The bridge serves the ADVANCED level plus one level of
    on-ramp review (base level kept for repeat learners).
    """
    base_ids = set(_chunk_ids(base_manifest))
    changed = [c for c in advanced_manifest.get("index", []) if c["id"] not in base_ids]
    removed = sorted(base_ids - set(_chunk_ids(advanced_manifest)))

    base_levels = base_manifest.get("level_target", DEFAULT_LEVEL_TARGET)
    adv_levels = advanced_manifest.get("level_target", DEFAULT_LEVEL_TARGET)
    # bridge target = the highest level the advanced side serves; on-ramp = the
    # highest the base side serves (the learner is coming FROM that level)
    top = max(set(adv_levels), key=level_rank)
    ramp = max(set(base_levels), key=level_rank)
    level_target = sorted({ramp, top}, key=level_rank)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    delta = {
        "schema_version": "1",
        "pack_id": pack_id,
        "version": version,
        "title": title or (
            f"{base_manifest.get('title', '?')} -> {advanced_manifest.get('title', '?')} "
            f"bridge ({ramp} to {top})"
        ),
        "created_at": now,
        "locale": advanced_manifest.get("locale", "en-IN"),
        "source": dict(advanced_manifest.get("source", {"name": "derived"})),
        "index": changed,
        "encryption": dict(advanced_manifest.get("encryption", {"payload": "aes-256-gcm"})),
        "delta": {
            "delta_from": advanced_manifest["pack_id"],
            "changed_chunks": [c["id"] for c in changed],
            "removed_chunks": removed,
        },
        "stats": {"chunks": len(changed)},
        "level_target": level_target,
        "prerequisites": [
            {"pack_id": base_manifest["pack_id"], "min_mastery": 0.8, "level_context": ramp},
        ],
        "estimated_hours": max(1, round(len(changed) / 25)),
    }
    if advanced_manifest.get("assessment_spec"):
        delta["assessment_spec"] = dict(advanced_manifest["assessment_spec"])
    if advanced_manifest.get("credit_value"):
        delta["credit_value"] = advanced_manifest["credit_value"]
    # learning outcomes: only those not already covered by the base pack
    base_outcomes = {o["competency_id"] for o in base_manifest.get("learning_outcomes", [])}
    new_outcomes = [o for o in advanced_manifest.get("learning_outcomes", [])
                    if o["competency_id"] not in base_outcomes]
    if new_outcomes:
        delta["learning_outcomes"] = new_outcomes
    return delta


def bridge_pack_manifest(base_manifest: Dict[str, Any],
                        advanced_manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience: auto-name an undergrad->masters style bridge pack."""
    base_levels = base_manifest.get("level_target", DEFAULT_LEVEL_TARGET)
    adv_levels = advanced_manifest.get("level_target", DEFAULT_LEVEL_TARGET)
    b = max(base_levels, key=level_rank)
    a = max(adv_levels, key=level_rank)
    if level_rank(a) <= level_rank(b):
        raise ValueError(
            f"advanced pack level set {adv_levels} is not above base {base_levels}; "
            "nothing to bridge")
    return build_delta_pack(
        base_manifest, advanced_manifest,
        pack_id=f"bridge-{b}-to-{a}-{base_manifest['pack_id']}",
    )
