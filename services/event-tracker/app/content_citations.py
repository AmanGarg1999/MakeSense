"""Cited-content adapter for LL-08.

The anti-hallucination contract (vision §2.4, non-negotiable #2) means every
generated learning step must trace to a tagged source item. This module reads
the knowledge-DB pack index actually present in the repo
(packs/dist/manifest.verify.json — produced by the REM-1 pack build) and turns
its entries into citation records carrying source, licence, capture date and a
content-addressed locator (sha256).

When the pack manifest is absent the adapter returns empty citations and callers
must NOT assert uncited content (project_together mode refuses to emit an
uncited step).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

_REPO_ROOTS = [
    Path(__file__).resolve().parents[3],  # repo root (event-tracker layout)
    Path(__file__).resolve().parents[1],  # containerized layout
]

DEFAULT_MANIFEST = "packs/dist/manifest.verify.json"


def manifest_path() -> Optional[Path]:
    env = os.environ.get("MSPACK_MANIFEST")
    if env and Path(env).exists():
        return Path(env)
    for root in _REPO_ROOTS:
        cand = root / DEFAULT_MANIFEST
        if cand.exists():
            return cand
    return None


def load_pack_index(path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Load the pack manifest's index + provenance. None when no pack is present."""
    p = path or manifest_path()
    if not p or not Path(p).exists():
        return None
    with open(p, encoding="utf-8") as fh:
        m = json.load(fh)
    src = m.get("source", {}) or {}
    return {
        "pack_id": m.get("pack_id"),
        "title": m.get("title"),
        "schema_version": m.get("schema_version"),
        "capture_date": m.get("created_at"),
        "source": {
            "name": src.get("name"),
            "license": src.get("license"),
            "upstream_url": src.get("upstream_url"),
            "subject": src.get("subject"),
        },
        "items": m.get("index", []),
    }


def _citation(pack: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    src = pack["source"]
    sha = item.get("sha256", "")
    return {
        "content_id": item.get("id"),
        "chapter": item.get("chapter"),
        "kind": item.get("kind"),
        "path": item.get("path"),
        "sha256": sha,
        "locator": f"{pack.get('pack_id')}/{item.get('id')}#sha256:{sha[:12]}",
        "source": src.get("name"),
        "source_url": src.get("upstream_url"),
        "license": src.get("license"),
        "capture_date": pack.get("capture_date"),
        "pack_id": pack.get("pack_id"),
    }


def cite_for_keywords(pack: Optional[dict[str, Any]], keywords: list[str],
                      per_skill: Optional[int] = 2,
                      prefer_kind: str = "text") -> list[dict[str, Any]]:
    """Return up to `per_skill` distinct citations whose chapter matches a keyword.

    per_skill=None returns the full matched pool (used to rotate citations
    across the steps of a project curriculum).
    """
    if not pack or not keywords:
        return []
    kws = [k.lower() for k in keywords]
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    # two passes: preferred kind first, then any kind
    for want in (prefer_kind, None):
        for item in pack["items"]:
            if want and item.get("kind") != want:
                continue
            chapter = str(item.get("chapter", "")).lower()
            if not any(k in chapter for k in kws):
                continue
            cid = item.get("id")
            if cid in seen:
                continue
            seen.add(cid)
            hits.append(_citation(pack, item))
            if per_skill is not None and len(hits) >= per_skill:
                return hits
    return hits


def _keywords_for_skill(skill: str, kg: dict[str, Any]) -> list[str]:
    node = (kg.get("skills") or {}).get(skill, {})
    keywords = list(node.get("citation_keywords") or [])
    if not keywords:
        keywords = [skill.replace("_", " ")] + list(node.get("topics") or [])
    return keywords


def citation_pool(skill: str, kg: dict[str, Any],
                  pack: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    """The full set of pack items that can substantiate a skill (all matches)."""
    return cite_for_keywords(pack, _keywords_for_skill(skill, kg), per_skill=None)


def cite_for_skill(skill: str, kg: dict[str, Any], pack: Optional[dict[str, Any]],
                   per_skill: int = 2) -> list[dict[str, Any]]:
    """Cite content for a skill, using KG citation_keywords when present, else the skill's own name/topics."""
    return cite_for_keywords(pack, _keywords_for_skill(skill, kg), per_skill=per_skill)


def verify_citations(citations: list[dict[str, Any]], pack: Optional[dict[str, Any]]) -> bool:
    """A citation set is valid only if every entry traces back to a real pack item."""
    if not citations:
        return False
    if not pack:
        return False
    by_id = {i.get("id"): i for i in pack["items"]}
    for c in citations:
        item = by_id.get(c.get("content_id"))
        if not item or item.get("sha256") != c.get("sha256"):
            return False
    return True
