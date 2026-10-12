"""License compliance per pathway level (mk-016, LL-09c).

Rules (docs/legal conventions + CC license terms):
  - CC-BY-NC-SA-4.0 ("NC" = non-commercial): allowed on micro/certificate/
    undergrad (personal & institutional teaching use), NOT allowed as
    tuition-charged graduate/degree content (masters/phd/mba) — those levels
    require a license without NC, or explicit fair-use review.
  - CC-BY-SA-4.0 / CC-BY-4.0: allowed at all levels.
  - MIT/Apache-2.0/BSD: allowed at all levels.
  - proprietary/all-rights-reserved: micro-only (private study), flagged
    everywhere else.
  - packs embedding a model build must carry the `legal` block (schema v0
    $defs.legal / MAK-17 checklist) — a model with redistribution
    'not_permitted' fails at every level.
"""
from __future__ import annotations

from typing import Any, Dict, List

# license id -> levels it may serve
_ALWAYS_OK = {
    "CC-BY-SA-4.0", "CC-BY-4.0", "CC0-1.0", "PDDL-1.0",
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
}
_NONCOMMERCIAL = {"CC-BY-NC-4.0", "CC-BY-NC-SA-4.0", "CC-BY-NC-ND-4.0"}
_DEGREE_LEVELS = {"masters", "phd", "mba"}   # tuition-bearing -> NC disallowed


def license_allowed_for_level(license_id: str, level: str) -> bool:
    lic = (license_id or "").strip()
    if lic in _ALWAYS_OK:
        return True
    if lic in _NONCOMMERCIAL:
        return level not in _DEGREE_LEVELS
    if lic.upper().startswith("GEMMA"):
        # Gemma terms: non-commercial, per MAK-17 review — same gate as CC-NC
        return level not in _DEGREE_LEVELS
    # unknown / proprietary: micro only (private study)
    return level == "micro"


def check_pack_licenses(manifest: Dict[str, Any]) -> List[str]:
    """Return a list of human-readable compliance violations ([] = compliant)."""
    problems: List[str] = []
    source_license = (manifest.get("source") or {}).get("license", "")
    for level in manifest.get("level_target", ["micro", "certificate"]):
        if not license_allowed_for_level(source_license, level):
            problems.append(
                f"source license {source_license!r} not permitted at level '{level}'")

    legal = manifest.get("legal")
    if legal:
        notices = set(legal.get("notices_included", []))
        for ml in legal.get("model_licenses", []):
            redist = ml.get("redistribution")
            if redist == "not_permitted":
                problems.append(
                    f"model {ml['model']} license {ml['license']!r} forbids redistribution")
            if redist == "conditional" and not notices:
                problems.append(
                    f"model {ml['model']} redistribution is conditional but no notice files bundled")
    return problems
