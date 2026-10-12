"""Level vocabulary for the packager.

Canonical enum source of truth is server/pathway_service.py:PATHWAY_LEVELS
(LL-09a). Duplicated here as plain data because the packager runs offline
during pack assembly and must not import the server stack. Tests assert
equality against the server list.
"""
from typing import List

PACKER_LEVELS: List[str] = ["micro", "certificate", "undergrad", "masters", "phd", "mba"]

# Monotonic rank for "delta pack" level ordering (undergrad -> masters bridge).
LEVEL_RANK = {lvl: i for i, lvl in enumerate(PACKER_LEVELS)}


def level_rank(level: str) -> int:
    try:
        return LEVEL_RANK[level]
    except KeyError:
        raise ValueError(f"unknown pathway level: {level!r} (expected one of {PACKER_LEVELS})")
