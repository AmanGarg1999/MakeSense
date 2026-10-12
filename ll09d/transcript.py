"""LL-09d: transcript document builder for degree-pathway export.

Turns the LL-09a tables (learning_pathways, pathway_curriculum,
user_transcript, level_metadata) into a canonical, schema-versioned JSON
document — the single payload shape shared by the JSON download and the PDF
renderer (ll09d/pdf.py).

The frontend mirror lives in frontend/src/lib/transcriptExport.js
(schema `makesense.transcript/v1`); tests/fixtures/
ll09d_transcript_fixture.json + the paired Python/Node test suites lock the
two implementations to identical numbers (cross-language contract).

Level vocabulary comes from server.pathway_service.PATHWAY_LEVELS (LL-09a
contract — never re-declared here).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

TRANSCRIPT_SCHEMA = "makesense.transcript/v1"

# 4.0-scale letter grades; identical thresholds to the JS mirror.
def letter_grade(mastery: float) -> str:
    if mastery >= 0.93: return "A"
    if mastery >= 0.87: return "A-"
    if mastery >= 0.80: return "B+"
    if mastery >= 0.73: return "B"
    if mastery >= 0.67: return "B-"
    if mastery >= 0.60: return "C+"
    if mastery >= 0.53: return "C"
    if mastery >= 0.40: return "D"
    return "F"


def _num(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return f if f == f else 0.0  # NaN guard


def _iso(v: Any) -> Optional[str]:
    """Normalise str/datetime/date to an ISO-8601 UTC string (or None)."""
    if v is None:
        return None
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(v, date):
        return v.isoformat()
    s = str(v)
    try:
        return _iso(datetime.fromisoformat(s.replace("Z", "+00:00")))
    except ValueError:
        return s or None


def _as_date_str(v: Any) -> Optional[str]:
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return None if v is None else str(v)


def _round2(x: float) -> float:
    return round(x * 100) / 100


def build_transcript_document(
    pathway: Dict[str, Any],
    transcript: Optional[List[Dict[str, Any]]] = None,
    level_row: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Canonical transcript doc for one pathway.

    ``pathway`` must contain the pathway row fields plus a ``curriculum`` list
    (GET /api/pathways/{id} / get_active_pathway shape). ``transcript`` is the
    user_transcript row list; ``level_row`` the optional level_metadata row.
    TypeError when the pathway carries no level — never export garbage.
    """
    if not isinstance(pathway, dict):
        raise TypeError("build_transcript_document: pathway dict required")
    level = pathway.get("level")
    if not level or not isinstance(level, str):
        raise TypeError("build_transcript_document: pathway has no level (cannot export)")

    raw_curr = pathway.get("curriculum")
    curriculum: List[Dict[str, Any]] = raw_curr if isinstance(raw_curr, list) else []
    entries: List[Dict[str, Any]] = transcript if transcript is not None else []
    by_pack: Dict[str, Dict[str, Any]] = {
        e["content_pack_id"]: e for e in entries
        if isinstance(e, dict) and e.get("content_pack_id") is not None
    }

    earned = 0.0
    completed = 0
    weighted_sum = 0.0
    weight_total = 0.0

    records: List[Dict[str, Any]] = []
    for item in curriculum:
        credit = _num(item.get("credits"))
        pack_key = str(item.get("content_pack_id"))
        entry = by_pack.get(pack_key)
        done = bool(entry and entry.get("completed_at") is not None)
        mastery = _num(entry.get("mastery_score")) if entry else 0.0
        if done:
            completed += 1
            earned += credit
            weighted_sum += mastery * credit
            weight_total += credit
        records.append({
            "content_pack_id": item.get("content_pack_id"),
            "sequence": item.get("sequence"),
            "required": item.get("required", True) is not False,
            "credits": credit,
            "completed": done,
            "completed_at": _iso(entry.get("completed_at")) if entry else None,
            "mastery_score": mastery if done else None,
            "grade_points": _round2(mastery * 4) if done else None,
            "grade_letter": letter_grade(mastery) if done else None,
            "credential_issued": bool(entry.get("credential_issued")) if entry else False,
            "credential_type": (entry.get("credential_type")
                                if entry and entry.get("credential_issued") else None),
        })

    in_cur = {c.get("content_pack_id") for c in curriculum}
    extra = [{
        "content_pack_id": e.get("content_pack_id"),
        "completed": e.get("completed_at") is not None,
        "completed_at": _iso(e.get("completed_at")),
        "mastery_score": _num(e.get("mastery_score")),
        "credential_issued": bool(e.get("credential_issued")),
        "credential_type": e.get("credential_type"),
        "flag": "not_in_curriculum",
    } for e in entries if isinstance(e, dict)
        and e.get("content_pack_id") is not None and e.get("content_pack_id") not in in_cur]

    total_credits = sum(_num(c.get("credits")) for c in curriculum)
    gpa = _round2((weighted_sum / weight_total) * 4) if weight_total > 0 else None
    completion_pct = _round2(round(completed / len(curriculum) * 1000) / 10) if curriculum else 0

    credentials = [
        {"content_pack_id": r["content_pack_id"], "credential_type": r["credential_type"]}
        for r in records + extra if r.get("credential_issued")
    ]

    return {
        "schema": TRANSCRIPT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "pathway": {
            "id": str(pathway.get("id")) if pathway.get("id") is not None else None,
            "user_id": pathway.get("user_id"),
            "level": level,
            "title": pathway.get("title"),
            "status": pathway.get("status"),
            "started_at": _iso(pathway.get("started_at")),
            "target_completion": _as_date_str(pathway.get("target_completion")),
            "completed_at": _iso(pathway.get("completed_at")),
        },
        "program": ({
            "typical_duration_weeks": level_row.get("typical_duration_weeks"),
            "credit_system": level_row.get("credit_system"),
            "assessment_type": level_row.get("assessment_type"),
            "mentor_model": level_row.get("mentor_model"),
            "recap_interval_days": level_row.get("recap_interval_days"),
        } if level_row else None),
        "summary": {
            "total_records": len(records),
            "completed": completed,
            "completion_pct": completion_pct,
            "credits_required": _round2(total_credits),
            "credits_earned": _round2(earned),
            "gpa": gpa,
            "credentials": credentials,
        },
        "records": records,
        "extra_entries": extra,
    }
