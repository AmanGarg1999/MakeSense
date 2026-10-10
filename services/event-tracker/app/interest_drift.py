"""LL-08 interest-drift router.

Turns the raw interest-signal stream (session telemetry from LL-04, content
interactions, and explicit signals — searches, track starts, abandoned tracks)
into a rolling interest profile with a confidence score and change-point
detection, then converts drift into *optional* side-quest offers and
example-domain choices.

Hard rule (vision non-negotiable #5): drifting interests NEVER silently derail a
stated goal. The stated goal is the main path; a goal change requires an
explicit ask — the one place the loop does ask.

All thresholds come from config/interest_drift.json. All functions are pure and
deterministic given `now`, so the behaviour is unit-testable without a clock or
database.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from app.interest_config import load_config

_EPS = 1e-9


# ---------------------------------------------------------------------------
# time + signal plumbing
# ---------------------------------------------------------------------------


def _parse_ts(ts: Any) -> float:
    """Coerce a timestamp (epoch seconds, ISO-8601 string, or datetime) to epoch seconds."""
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, datetime):
        dt = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    if isinstance(ts, str):
        s = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
    raise TypeError(f"unsupported timestamp: {ts!r}")


def _decay(age_seconds: float, half_life_seconds: float) -> float:
    if age_seconds < 0:
        return 0.0
    return 0.5 ** (age_seconds / half_life_seconds)


def signal_contribution(signal: dict[str, Any], now: float, cfg: dict) -> float:
    """Decayed weight this signal contributes to its domain at time `now`."""
    sw = cfg["signal_weights"]
    half_life = cfg["time"]["half_life_days"] * cfg["time"]["day_seconds"]
    base = float(signal.get("weight", sw.get(signal.get("kind", "session"), 1.0)))
    # explicit per-signal weight, else the kind's configured weight
    if "weight" not in signal:
        base = float(sw.get(signal.get("kind", "session"), 1.0))
    age = now - _parse_ts(signal["ts"])
    return base * _decay(age, half_life)


def _confidence(weight: float, signal_count: int, sources: set[str], cfg: dict) -> float:
    p = cfg["profile"]
    base = 1.0 - math.exp(-weight / max(_EPS, p["confidence_weight_scale"]))
    src_factor = min(1.0, len(sources) / max(1, p["confidence_min_sources"]))
    cnt_factor = min(1.0, signal_count / max(1, p["confidence_min_signals"]))
    return round(min(p["confidence_cap"], base * src_factor * cnt_factor), 4)


# ---------------------------------------------------------------------------
# rolling profile
# ---------------------------------------------------------------------------


@dataclass
class DomainInterest:
    domain: str
    weight: float
    share: float
    confidence: float
    signal_count: int
    sources: list[str]
    latest_ts: Optional[float] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "weight": round(self.weight, 4),
            "share": round(self.share, 4),
            "confidence": self.confidence,
            "signal_count": self.signal_count,
            "sources": sorted(self.sources),
            "latest_ts": self.latest_ts,
        }


def build_interest_profile(signals: Iterable[dict[str, Any]], cfg: Optional[dict] = None,
                           now: Optional[float] = None) -> dict[str, DomainInterest]:
    """Rolling, time-decayed interest weight + confidence per domain."""
    cfg = cfg or load_config()
    now = _now(now)
    weights: dict[str, float] = {}
    counts: dict[str, int] = {}
    sources: dict[str, set[str]] = {}
    latest: dict[str, float] = {}

    for s in signals:
        dom = s.get("domain")
        if not dom:
            continue
        w = signal_contribution(s, now, cfg)
        if w <= 0:
            continue
        weights[dom] = weights.get(dom, 0.0) + w
        counts[dom] = counts.get(dom, 0) + 1
        sources.setdefault(dom, set()).add(str(s.get("kind", "session")))
        ts = _parse_ts(s["ts"])
        latest[dom] = max(latest.get(dom, ts), ts)

    total = sum(weights.values()) or _EPS
    profile: dict[str, DomainInterest] = {}
    min_w = cfg["profile"]["min_domain_weight"]
    for dom, w in weights.items():
        if w < min_w:
            continue
        profile[dom] = DomainInterest(
            domain=dom, weight=w, share=w / total,
            confidence=_confidence(w, counts[dom], sources[dom], cfg),
            signal_count=counts[dom], sources=sorted(sources[dom]),
            latest_ts=latest.get(dom),
        )
    return profile


# ---------------------------------------------------------------------------
# change-point detection (windowed share shift)
# ---------------------------------------------------------------------------


@dataclass
class DriftEvent:
    domain: str
    direction: str            # 'rising' | 'falling'
    baseline_share: float
    recent_share: float
    delta: float
    confidence: float
    is_goal_track: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain, "direction": self.direction,
            "baseline_share": round(self.baseline_share, 4),
            "recent_share": round(self.recent_share, 4),
            "delta": round(self.delta, 4), "confidence": self.confidence,
            "is_goal_track": self.is_goal_track, "evidence": self.evidence,
        }


def _bucket_series(signals: Iterable[dict[str, Any]], cfg: dict, now: float):
    """Return ({domain: [bucket_weights]}, [total_per_bucket]); oldest bucket first."""
    cp = cfg["change_point"]
    bucket_s = cp["bucket_seconds"]
    n = cp["baseline_buckets"] + cp["recent_buckets"]
    series: dict[str, list[float]] = {}
    totals = [0.0] * n
    for s in signals:
        dom = s.get("domain")
        if not dom:
            continue
        age = now - _parse_ts(s["ts"])
        if age < 0:
            continue
        idx = n - 1 - int(age // bucket_s)
        if idx < 0:
            continue  # older than the detection window
        w = signal_contribution(s, now, cfg)
        series.setdefault(dom, [0.0] * n)[idx] += w
        totals[idx] += w
    return series, totals, n


def detect_change_points(signals: Iterable[dict[str, Any]], profile: dict[str, DomainInterest],
                         cfg: Optional[dict] = None, now: Optional[float] = None,
                         goal_domains: Optional[set[str]] = None) -> list[DriftEvent]:
    cfg = cfg or load_config()
    now = _now(now)
    goal_domains = goal_domains or set()
    cp = cfg["change_point"]
    series, totals, n = _bucket_series(signals, cfg, now)
    b = cp["baseline_buckets"]
    base_total = sum(totals[:b]) or _EPS
    recent_total = sum(totals[b:]) or _EPS

    events: list[DriftEvent] = []
    for dom, buckets in series.items():
        recent_w = sum(buckets[b:])
        base_w = sum(buckets[:b])
        if recent_w < cp["min_domain_weight"] and base_w < cp["min_domain_weight"]:
            continue
        base_share = base_w / base_total
        recent_share = recent_w / recent_total
        delta = recent_share - base_share
        interest = profile.get(dom)
        conf = interest.confidence if interest else 0.0
        if abs(delta) < cp["min_share_delta"]:
            continue
        if conf < cp["min_confidence"]:
            continue
        events.append(DriftEvent(
            domain=dom, direction="rising" if delta > 0 else "falling",
            baseline_share=base_share, recent_share=recent_share, delta=delta,
            confidence=conf, is_goal_track=dom in goal_domains,
            evidence={
                "bucket_seconds": cp["bucket_seconds"],
                "baseline_buckets": cp["baseline_buckets"],
                "recent_buckets": cp["recent_buckets"],
                "bucket_shares": [round(x / (totals[i] or _EPS), 4) for i, x in enumerate(buckets)],
                "recent_weight": round(recent_w, 4),
                "baseline_weight": round(base_w, 4),
                "thresholds": {"min_share_delta": cp["min_share_delta"],
                               "min_domain_weight": cp["min_domain_weight"],
                               "min_confidence": cp["min_confidence"]},
            }))
    events.sort(key=lambda e: abs(e.delta), reverse=True)
    return events


# ---------------------------------------------------------------------------
# router: drift -> offers, goal protected
# ---------------------------------------------------------------------------


@dataclass
class QuestOffer:
    domain: str
    offer_text: str
    confidence: float
    delta: float
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"domain": self.domain, "offer_text": self.offer_text,
                "confidence": self.confidence, "delta": round(self.delta, 4),
                "evidence": self.evidence}


@dataclass
class ExampleDomainSuggestion:
    skill_tag: str
    example_domain: str
    reason: str
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {"skill_tag": self.skill_tag, "example_domain": self.example_domain,
                "reason": self.reason, "confidence": self.confidence}


@dataclass
class GoalProtection:
    goal_intact: bool
    requires_explicit_ask: bool
    question: Optional[str] = None
    reason: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {"goal_intact": self.goal_intact,
                "requires_explicit_ask": self.requires_explicit_ask,
                "question": self.question, "reason": self.reason}


@dataclass
class DriftReport:
    profile: dict[str, DomainInterest]
    drift_events: list[DriftEvent]
    quest_offers: list[QuestOffer]
    example_domain_suggestions: list[ExampleDomainSuggestion]
    goal_protection: GoalProtection

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile": {d: i.as_dict() for d, i in self.profile.items()},
            "drift_events": [e.as_dict() for e in self.drift_events],
            "quest_offers": [o.as_dict() for o in self.quest_offers],
            "example_domain_suggestions": [s.as_dict() for s in self.example_domain_suggestions],
            "goal_protection": self.goal_protection.as_dict(),
        }


def route_interests(signals: Iterable[dict[str, Any]],
                    goal_tracks: list[dict[str, Any]],
                    cfg: Optional[dict] = None,
                    now: Optional[float] = None,
                    active_track_domains: Optional[set[str]] = None) -> DriftReport:
    """Full pipeline: signals -> profile -> change points -> offers + protection.

    goal_tracks: [{"track_id": ..., "domain": "<skill_tag>", "stalled": bool?}].
    The stated goal is treated as immutable here; the only goal-change path is
    GoalProtection.requires_explicit_ask (surfaced as a question).
    """
    cfg = cfg or load_config()
    now = _now(now)
    signals = list(signals)
    goal_domains = {t["domain"] for t in goal_tracks}
    active_track_domains = active_track_domains if active_track_domains is not None \
        else set(goal_domains)

    profile = build_interest_profile(signals, cfg, now)
    events = detect_change_points(signals, profile, cfg, now, goal_domains)
    drift_cfg = cfg["drift"]

    # --- quest offers: rising interest that is NOT an active track -----------
    offers: list[QuestOffer] = []
    for ev in events:
        if ev.direction != "rising":
            continue
        if ev.domain in active_track_domains:
            continue  # already a track — it is not a *side* quest
        if ev.confidence < drift_cfg["quest_offer_min_confidence"]:
            continue
        if ev.delta < drift_cfg["quest_offer_min_delta"]:
            continue
        pct_recent = round(ev.recent_share * 100)
        pct_base = round(ev.baseline_share * 100)
        goal = ", ".join(sorted(goal_domains)) or "your current goal"
        offers.append(QuestOffer(
            domain=ev.domain, confidence=ev.confidence, delta=ev.delta,
            offer_text=(f"You keep coming back to {ev.domain}: it is now "
                        f"~{pct_recent}% of your recent learning signals, up from "
                        f"~{pct_base}%. That's a side quest, not a detour — {goal} "
                        f"stays your main line. Want to pick it up as an optional "
                        f"quest?"),
            evidence={"recent_share": round(ev.recent_share, 4),
                      "baseline_share": round(ev.baseline_share, 4),
                      "delta": round(ev.delta, 4),
                      "confidence": ev.confidence,
                      "change_point": ev.evidence},
        ))
    offers = offers[:drift_cfg["max_offers"]]

    # --- example-domain choices: an established track teaches another skill --
    examples: list[ExampleDomainSuggestion] = []
    for g in goal_tracks:
        for dom, interest in profile.items():
            if dom == g["domain"] or dom not in active_track_domains:
                continue
            if interest.confidence < drift_cfg["example_domain_min_confidence"]:
                continue
            examples.append(ExampleDomainSuggestion(
                skill_tag=g["domain"], example_domain=dom,
                confidence=interest.confidence,
                reason=(f"Use your {dom} track ({round(interest.share * 100)}% of "
                        f"learning signals, confidence {interest.confidence}) as the "
                        f"example domain when teaching {g['domain']}.")))
    # dedupe (skill, example)
    seen = set()
    uniq_examples = []
    for e in examples:
        key = (e.skill_tag, e.example_domain)
        if key in seen:
            continue
        seen.add(key)
        uniq_examples.append(e)
    examples = uniq_examples

    # --- goal protection: NEVER auto-change; ask explicitly when warranted ---
    falling_goal = any(e.direction == "falling" and e.is_goal_track for e in events)
    stalled_goal = any(t.get("stalled") for t in goal_tracks)
    top_rising = next((e for e in events if e.direction == "rising"
                       and e.domain not in active_track_domains), None)
    requires_ask = False
    question = None
    reason = None
    ask_on = set(cfg["goal_protection"]["explicit_ask_on"])
    if falling_goal and "goal_track_falling" in ask_on and top_rising:
        requires_ask = True
        reason = "goal_track_falling"
    elif stalled_goal and "goal_track_stalled" in ask_on and top_rising:
        requires_ask = True
        reason = "goal_track_stalled"
    if requires_ask:
        assert top_rising is not None  # requires_ask is only set when one exists
        question = cfg["goal_protection"]["goal_change_question"].format(
            goal=", ".join(sorted(goal_domains)) or "your stated goal",
            drift_domain=top_rising.domain)

    goal_protection = GoalProtection(
        goal_intact=True, requires_explicit_ask=requires_ask,
        question=question, reason=reason)

    return DriftReport(profile, events, offers, examples, goal_protection)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _now(now: Optional[float]) -> float:
    if now is None:
        return datetime.now(timezone.utc).timestamp()
    return _parse_ts(now)


def signals_from_delivery_segments(segments: Iterable[dict[str, Any]],
                                   weights: Optional[dict[str, float]] = None) -> list[dict[str, Any]]:
    """Derive interest signals from LL-04 delivery_segments rows.

    A completed segment is a positive `session` signal for its skill; an
    abandoned segment is a (weaker) signal that the interest is not holding.
    Column names match server/migrations/007_delivery_telemetry.sql.
    """
    out: list[dict[str, Any]] = []
    for s in segments:
        skill = s.get("skill_tag")
        if not skill:
            continue
        out.append({
            "ts": s.get("created_at") or s.get("ts"),
            "kind": "session",
            "domain": skill,
            "track_id": s.get("track_id"),
            "source": "delivery_segment",
            "meta": {"abandoned": bool(s.get("abandoned")),
                     "retrieval_outcome": s.get("retrieval_outcome")},
        })
    return out
