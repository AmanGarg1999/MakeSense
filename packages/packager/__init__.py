"""MakeSense Packager Service (mk-016) — pack manifest validation for
Content Pack Format v1 with multi-level pathway metadata (LL-09c).

Public API:
  load_manifest(payload)          -> normalized PackManifest
  validate_manifest(payload)      -> PackManifest (raises PackValidationError)
  validate_prereq_graph(manifests)-> list of cycle paths (empty = OK)
  build_delta_pack(base, ...)     -> delta/bridge pack manifest (dict)
  license_allowed_for_level(lic, level) -> bool
"""
from .manifest import (
    PackManifest,
    PackValidationError,
    load_manifest,
    validate_manifest,
    validate_prereq_graph,
    normalize_prereq_graph,
    DEFAULT_LEVEL_TARGET,
)
from .delta import build_delta_pack, bridge_pack_manifest
from .license import license_allowed_for_level, check_pack_licenses
from .levels import PACKER_LEVELS, level_rank

__all__ = [
    "PackManifest", "PackValidationError", "load_manifest", "validate_manifest",
    "validate_prereq_graph", "normalize_prereq_graph", "DEFAULT_LEVEL_TARGET",
    "build_delta_pack", "bridge_pack_manifest",
    "license_allowed_for_level", "check_pack_licenses",
    "PACKER_LEVELS", "level_rank",
]
