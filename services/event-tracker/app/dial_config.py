"""Shared config loader for the LL-04 delivery dial.

All thresholds for the active/passive delivery engine live in
config/delivery_dial.json — never as magic numbers in code.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# repo root = three levels up from services/event-tracker/app/
_REPO_CANDIDATES = [
    Path(os.environ.get("DELIVERY_DIAL_CONFIG", "")).parent
    if os.environ.get("DELIVERY_DIAL_CONFIG")
    else None,
    Path(__file__).resolve().parents[3],  # repo root (event-tracker layout)
    Path(__file__).resolve().parents[1],  # services/<svc> layout (containerized /app)
]


def config_path() -> Path:
    env = os.environ.get("DELIVERY_DIAL_CONFIG")
    if env:
        return Path(env)
    for root in _REPO_CANDIDATES:
        if root is None:
            continue
        candidate = root / "config" / "delivery_dial.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("delivery_dial.json not found; set DELIVERY_DIAL_CONFIG")


def load_config() -> dict[str, Any]:
    with open(config_path(), encoding="utf-8") as fh:
        cfg = json.load(fh)
    _validate(cfg)
    return cfg


def _validate(cfg: dict[str, Any]) -> None:
    for section in ("modes", "track_defaults", "segment_classifier",
                    "engagement", "flip_rule", "companion_voice"):
        if section not in cfg:
            raise ValueError(f"delivery_dial.json missing required section: {section}")
    for key in ("min_sessions_per_skill", "passive_abandon_rate_threshold",
                "failed_retrieval_count_threshold", "escalation_sessions",
                "lookback_sessions"):
        if key not in cfg["flip_rule"]:
            raise ValueError(f"flip_rule missing threshold: {key}")
