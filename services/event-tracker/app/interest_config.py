"""Shared config + KG loader for LL-08 (interest drift, modes, future paths).

Every threshold lives in config/interest_drift.json and the competency KG seed
lives in data/skill_kg.json — never as magic numbers in code. Mirrors
app/dial_config.py (LL-04) so both engines resolve repo paths the same way.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# repo root = three levels up from services/event-tracker/app/
_REPO_ROOTS = [
    Path(os.environ["INTEREST_CONFIG"]).resolve().parents[1]
    if os.environ.get("INTEREST_CONFIG")
    else None,
    Path(__file__).resolve().parents[3],  # event-tracker layout: repo root
    Path(__file__).resolve().parents[1],  # containerized /app layout
]


def _find(rel: str) -> Path:
    env = os.environ.get("INTEREST_CONFIG") if rel.endswith("interest_drift.json") else None
    if env:
        return Path(env)
    for root in _REPO_ROOTS:
        if root is None:
            continue
        cand = root / rel
        if cand.exists():
            return cand
    raise FileNotFoundError(f"{rel} not found; set INTEREST_CONFIG / KG_CONFIG")


def config_path() -> Path:
    return _find("config/interest_drift.json")


def kg_path() -> Path:
    return _find("data/skill_kg.json")


def load_config() -> dict[str, Any]:
    with open(config_path(), encoding="utf-8") as fh:
        cfg = json.load(fh)
    _validate(cfg)
    return cfg


def load_kg() -> dict[str, Any]:
    with open(kg_path(), encoding="utf-8") as fh:
        return json.load(fh)


def _validate(cfg: dict[str, Any]) -> None:
    for section in ("time", "signal_weights", "profile", "change_point",
                    "drift", "goal_protection", "mode_routing", "future_paths",
                    "project_mode"):
        if section not in cfg:
            raise ValueError(f"interest_drift.json missing required section: {section}")
    for key in ("half_life_days",):
        if key not in cfg["time"]:
            raise ValueError(f"time missing threshold: {key}")
    for key in ("bucket_seconds", "baseline_buckets", "recent_buckets",
                "min_share_delta", "min_domain_weight", "min_confidence"):
        if key not in cfg["change_point"]:
            raise ValueError(f"change_point missing threshold: {key}")
    modes = set(cfg["mode_routing"]["modes"])
    for m in list(cfg["mode_routing"]["by_level"].values()) + \
             list(cfg["mode_routing"]["by_goal"].values()):
        if m not in modes:
            raise ValueError(f"mode_routing references unknown mode: {m}")
    if "verification_endpoint" not in cfg["mode_routing"]:
        raise ValueError("mode_routing.verification_endpoint is required (LL-05)")
