"""LL-06 §2: user-initiated recap — "take me back through X".

Generates a review digest from the stores, retrieval-first: every section asks
the user to recall/apply BEFORE showing the answer, and it is built from what
the user actually did and missed (mastery ledger + verification outcomes +
recap history), NOT a re-read of the original content.

Structure per digest:
  1. anchors   — the ladder rungs for X with the user's own can-do state
  2. prompts   — recall questions seeded from knowledge-DB items (citations)
  3. gaps      — the specific things they got wrong / lapsed on, re-asked in a
                 changed form (never the same card — vision §2.8)
  4. timeline  — what they did, when, and how it verified (provenance trail)

Citations are store ids + source URLs from the knowledge DB (``items``), so
every claim in a digest is traceable.
"""

from __future__ import annotations

import re
import time
from typing import Any, Optional

from ll07.stores import Stores

_SLUG = re.compile(r"[^a-z0-9]+")


def _norm(s: str) -> str:
    return _SLUG.sub("", s.lower())


def _matches(skill_tag: str, query: str) -> bool:
    """Loose matcher: 'guitar' hits 'guitar:strum', 'c major' hits 'g:c_g', etc."""
    q = _norm(query)
    if not q:
        return True
    t = _norm(skill_tag)
    return q in t or t in q or any(part and part in t for part in q.split())


def _can_do(skill_tag: str, ladder: Optional[list[dict]]) -> Optional[str]:
    if not ladder:
        return None
    for rung in ladder:
        if rung.get("skill") == skill_tag or _matches(str(rung.get("skill", "")), skill_tag):
            return rung.get("can_do")
    return None


def build_digest(stores: Stores, *, user_id: str, query: str,
                 track_id: Optional[str] = None,
                 ladder: Optional[list[dict[str, Any]]] = None,
                 now: Optional[float] = None) -> dict[str, Any]:
    """Compose the retrieval-first rewind for whatever X ('query') maps to."""
    now = now if now is not None else time.time()

    # -- collect the user's history for skills matching X -------------------
    # A skill matches when the tag matches the query OR the event's track
    # belongs to that query's track (e.g. 'guitar' -> track 'guitar-hobby',
    # which covers abbreviated tags like 'g:strum').
    skills: dict[str, dict[str, Any]] = {}

    track_hits = {ev.get("track_id") for ev in
                  stores.history("mastery", user_id=user_id, limit=10**6)
                  if ev.get("track_id") and _matches(ev["track_id"], query)}

    def _hit(tag: str, ev_track: Optional[str]) -> bool:
        return _matches(tag, query) or (ev_track in track_hits if ev_track else False)

    def _slot(tag: str) -> dict[str, Any]:
        return skills.setdefault(tag, {"mastery": 0.0, "did": [], "missed": [],
                                       "verifications": [], "recaps": [],
                                       "track_id": track_id})

    for ev in stores.history("mastery", user_id=user_id, limit=10**6):
        tag = ev.get("skill_tag") or ""
        if not _hit(tag, ev.get("track_id")):
            continue
        slot = _slot(tag)
        slot["track_id"] = ev.get("track_id") or slot["track_id"]
        slot["mastery"] += float(ev.get("delta") or 0.0)
        slot["did"].append({"ts": ev["ts"], "cause": ev.get("cause"),
                            "delta": float(ev.get("delta") or 0.0),
                            "ref": ev["id"]})
        if ev.get("cause") in ("recap_lapse", "verification_lapse"):
            slot["missed"].append({"ts": ev["ts"], "kind": ev["cause"], "ref": ev["id"]})

    for ev in stores.history("verifications", user_id=user_id, limit=10**6):
        tag = ev.get("skill_tag") or ""
        if not _hit(tag, ev.get("track_id")):
            continue
        slot = _slot(tag)
        slot["verifications"].append({
            "ts": ev["ts"], "outcome": ev.get("outcome"),
            "evidence": ev.get("evidence"), "expires_at": ev.get("expires_at"),
            "ref": ev["id"],
        })
        if ev.get("outcome") in ("fail", "rejected", "provisional"):
            slot["missed"].append({"ts": ev["ts"], "kind": "verification_" + str(ev.get("outcome")),
                                   "ref": ev["id"]})

    for ev in stores.history("recaps", user_id=user_id, limit=10**6):
        tag = ev.get("skill_tag") or ""
        if not _hit(tag, ev.get("track_id")) or ev.get("outcome") is None:
            continue
        slot = _slot(tag)
        slot["recaps"].append({"ts": ev["ts"], "outcome": ev["outcome"],
                               "quality": ev.get("quality"), "ref": ev["id"]})
        if ev["outcome"] == "lapsed":
            slot["missed"].append({"ts": ev["ts"], "kind": "recap_lapse",
                                   "quality": ev.get("quality"), "ref": ev["id"]})

    if not skills:
        return {"query": query, "user_id": user_id, "sections": [],
                "citations": [], "summary": f"No recorded history for '{query}' yet — "
                                           "this belongs on the learning path, not in a recap."}

    # -- knowledge-DB items for citations ------------------------------------
    kb_by_tag: dict[str, list[dict[str, Any]]] = {}
    for tag in skills:
        kb_by_tag[tag] = stores.history("items", skill_tag=tag, limit=8)

    # -- assemble retrieval-first sections ---------------------------------
    sections: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []

    def _cite(item: dict[str, Any]) -> str:
        citations.append({"kind": "knowledge_item", "store_id": item["id"],
                          "source_url": item.get("source_url"),
                          "license": item.get("license"),
                          "quote": item.get("quote")})
        return f"[C{len(citations)}]"

    for tag, slot in sorted(skills.items()):
        # what the user is working toward (their own can-do statement)
        anchor = _can_do(tag, ladder) or f"recall what '{tag}' lets you do"

        # Q: retrieval prompt first — question BEFORE any answer
        q = {"kind": "recall_prompt", "skill_tag": tag,
             "question": f"Without looking: what's the one move that makes "
                         f"'{anchor}' work? Show it, don't describe it.",
             "effort": "active"}

        a_sources = kb_by_tag.get(tag, [])
        ans_refs = [_cite(x) for x in a_sources]
        reveal = {"kind": "reveal", "skill_tag": tag,
                  "answer_from": [{"url": x.get("source_url"), "store_id": x["id"]}
                                 for x in a_sources],
                  "note": "reveal only after attempting — source spans are cited, not restated"}
        if ans_refs:
            reveal["citations"] = ans_refs

        timeline = {"kind": "timeline", "skill_tag": tag,
                    "did": sorted(slot["did"] + slot["verifications"] + slot["recaps"],
                                  key=lambda e: e["ts"]),
                    "mastery_delta_total": round(slot["mastery"], 2)}

        section = {"skill_tag": tag, "track_id": slot["track_id"],
                   "can_do": anchor, "prompt": q, "reveal": reveal,
                   "timeline": timeline}

        # gaps: re-ask changed, never the same card (vision §2.8)
        if slot["missed"]:
            worst = sorted(slot["missed"], key=lambda m: m["ts"])[-3:]
            section["gaps"] = [{
                "kind": "gap_requestion",
                "was": m["kind"],
                "when_ts": m["ts"],
                "ref": m["ref"],
                "question": f"You stumbled on '{tag}' ({m['kind']}). New angle: "
                            f"apply it to a situation you haven't seen in your "
                            f"own log — what changes and what breaks?",
                "route": "ll04_active_mode",   # delivery flip, not repeat-card
            } for m in worst]
        sections.append(section)

    total_missed = sum(len(s.get("gaps", [])) for s in sections)
    summary = (f"Rewind on '{query}': {len(sections)} skill(s) with history, "
               f"{total_missed} gap(s) to re-question, {len(citations)} knowledge-DB "
               f"citation(s). Start with the prompts — the reveals are for after.")

    digest = {"query": query, "user_id": user_id, "generated_at": now,
              "format": "retrieval-first", "sections": sections,
              "citations": citations, "summary": summary}
    stores.append("recaps", {
        "id": f"recap:digest:{user_id}:{_norm(query) or 'all'}:{int(now * 1000) % 10**9}",
        "user_id": user_id, "track_id": track_id or (skills and next(iter(skills.values()))["track_id"]),
        "skill_tag": query, "status": "digest", "due_at": None, "bucket": None,
        "n_sections": len(sections), "n_citations": len(citations),
    }, provenance="user")
    return digest


def rewind(stores: Stores, *, user_id: str, topic: str,
           track_id: Optional[str] = None,
           ladder: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    """Natural-language entry point: 'take me back through [X]'."""
    m = re.search(r"(?:back through|rewind|revise|recap)\s+(.+)", topic, re.IGNORECASE)
    query = m.group(1).strip() if m else topic.strip()
    return build_digest(stores, user_id=user_id, query=query,
                        track_id=track_id, ladder=ladder)
