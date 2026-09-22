"""Interactive Learning Path & Skill Tree Generator with Mentorship Logic."""

import uuid
from typing import Dict, List, Any, Optional


def generate_pathway_options(
    topic: str,
    category: str,
    profile: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generates 3 distinct tailored educational pathway options for the learner to compare."""
    goal = profile.get("goal", "life_skill")
    baseline = profile.get("baseline", "beginner")
    modality = profile.get("modality", "hands_on")
    pace = profile.get("pace", "focus")
    pain_points = (profile.get("pain_points") or "").strip()

    base_time = 10 if pace == "micro" else (35 if pace == "sprint" else 20)

    rec_track = "project_first" if goal == "project" else (
        "deep_foundation" if (goal in ["career", "deep_theory"] or baseline == "practitioner") else "fast_track"
    )

    fast_nodes = _generate_path_nodes(topic, category, goal, baseline, modality, base_time, pain_points, "fast_track")
    deep_nodes = _generate_path_nodes(topic, category, goal, baseline, modality, base_time, pain_points, "deep_foundation")
    proj_nodes = _generate_path_nodes(topic, category, goal, baseline, modality, base_time, pain_points, "project_first")

    def _summarize_milestones(nodes):
        return [
            {
                "index": i + 1,
                "title": n["title"],
                "description": n["description"],
                "duration": f"{n['estimated_time_minutes']} min",
                "difficulty": n["difficulty"],
                "rationale": n["mentor_rationale"]
            }
            for i, n in enumerate(nodes)
        ]

    return [
        {
            "id": "fast_track",
            "title": "⚡ Fast-Track Pragmatist",
            "subtitle": "High-leverage sprint to working competence",
            "badge": "Speed & Agility" if rec_track != "fast_track" else "⭐ Recommended for Your Pace",
            "recommended": rec_track == "fast_track",
            "philosophy": (
                f"Streamlines {topic} down to the core 20% of skills that produce 80% of practical results. "
                "Cuts extraneous theory in favor of immediate functional drills."
            ),
            "estimated_total_hours": f"~{round((len(fast_nodes) * base_time) / 60, 1)} hours",
            "milestone_count": len(fast_nodes),
            "milestones": _summarize_milestones(fast_nodes),
            "skills_unlocked": [f"{topic} Fundamentals", "Core Workflows", "Practical Troubleshooting"]
        },
        {
            "id": "deep_foundation",
            "title": "🏛️ Deep Systems Architect",
            "subtitle": "First-principles mastery & production rigor",
            "badge": "Comprehensive Depth" if rec_track != "deep_foundation" else "⭐ Recommended for Career",
            "recommended": rec_track == "deep_foundation",
            "philosophy": (
                f"Deconstructs foundational mental models, edge cases, and performance constraints behind {topic}. "
                "Ensures deep structural fluency and technical resilience."
            ),
            "estimated_total_hours": f"~{round((len(deep_nodes) * (base_time + 5)) / 60, 1)} hours",
            "milestone_count": len(deep_nodes),
            "milestones": _summarize_milestones(deep_nodes),
            "skills_unlocked": [f"{topic} Architecture", "Defensive Patterns", "Optimization & Diagnostics"]
        },
        {
            "id": "project_first",
            "title": "🛠️ Applied Project-First",
            "subtitle": "Step-by-step construction of a portfolio deliverable",
            "badge": "Portfolio Builder" if rec_track != "project_first" else "⭐ Recommended for Project Goal",
            "recommended": rec_track == "project_first",
            "philosophy": (
                f"Every single milestone directly produces a verifiable module of a real-world project in {topic}. "
                "You learn concepts precisely when you need them to unblock the next feature."
            ),
            "estimated_total_hours": f"~{round((len(proj_nodes) * (base_time + 8)) / 60, 1)} hours",
            "milestone_count": len(proj_nodes),
            "milestones": _summarize_milestones(proj_nodes),
            "skills_unlocked": ["Full-Cycle Implementation", "Domain Synthesis", "Portfolio Showcase"]
        }
    ]


def curate_learning_path(
    topic: str,
    category: str,
    profile: Dict[str, Any],
    track_type: str = "fast_track",
    mentor_persona: str = "Encouraging Guide"
) -> Dict[str, Any]:
    """Curates an adaptive, personalized learning path graph (DAG) based on learner profiling."""
    goal = profile.get("goal", "life_skill")
    baseline = profile.get("baseline", "beginner")
    modality = profile.get("modality", "hands_on")
    pace = profile.get("pace", "focus")
    pain_points = (profile.get("pain_points") or "").strip()

    time_multiplier = 10 if pace == "micro" else (35 if pace == "sprint" else 20)

    # Personal mentor greeting
    mentor_notes = _generate_mentor_briefing(topic, category, goal, baseline, modality, pace, pain_points, track_type)

    # Generate customized milestone nodes with 3D constellation coordinates
    nodes = _generate_path_nodes(topic, category, goal, baseline, modality, time_multiplier, pain_points, track_type)

    system_prompt = f"You are an AI mentor with a {mentor_persona} personality. Adapt your tone and rationales to match this persona when generating the DAG."

    import random
    for n in nodes:
        if random.random() < 0.15:
            n["metadata"] = n.get("metadata", {})
            n["metadata"]["is_treasure"] = True

    track_titles = {
        "fast_track": "Fast-Track",
        "deep_foundation": "Architect",
        "project_first": "Project Builder"
    }
    track_label = track_titles.get(track_type, "Custom")

    return {
        "title": f"{track_label} Path: {topic}",
        "system_prompt": system_prompt,
        "topic": topic,
        "category": category,
        "track_type": track_type,
        "user_profile": profile,
        "mentor_notes": mentor_notes,
        "nodes": nodes
    }


def _generate_mentor_briefing(topic, category, goal, baseline, modality, pace, pain_points, track_type="fast_track") -> str:
    track_descriptions = {
        "fast_track": "This **Fast-Track Pragmatist** path zeroes in on high-leverage practical competence with zero fluff.",
        "deep_foundation": "This **Deep Systems Architect** path establishes rock-solid first-principles and production-grade edge handling.",
        "project_first": "This **Applied Project-First** path grounds your progression into building a tangible, portfolio-ready solution."
    }

    goal_phrasing = {
        "career": "accelerating your professional capability and interview readiness",
        "project": "building a functional, real-world portfolio project",
        "life_skill": "mastering sustainable, practical decision-making for daily life",
        "hobby": "developing enjoyable, creative fluency and expressive technique",
        "deep_theory": "building foundational first-principles mastery from the ground up"
    }.get(goal, "achieving comprehensive mastery")

    modality_phrasing = {
        "hands_on": "prioritizing interactive drills, runnable code, and applied exercises",
        "socratic": "focusing on conceptual mental models and guided inquiry",
        "case_study": "analyzing real-world case studies and practical scenarios",
        "fast_quiz": "leveraging rapid active-recall questions and micro-challenges"
    }.get(modality, "balanced theoretical and practical training")

    pacing_text = {
        "micro": "Bite-sized micro-milestones (~10 mins/day) designed to fit a busy schedule.",
        "focus": "Balanced focus sessions (~20 mins/day) ensuring consistent, sustainable momentum.",
        "sprint": "Immersive deep-dive sessions (~35-45 mins/day) for rapid accelerated progression."
    }.get(pace, "Standard modular progression.")

    notes = (
        f"Welcome to your curated journey in **{topic}**! {track_descriptions.get(track_type, '')}\n\n"
        f"Based on your goal of {goal_phrasing}, I've tailored this curriculum for your **{baseline}** starting point, {modality_phrasing}.\n\n"
        f"📌 **Pacing**: {pacing_text}\n"
    )

    if pain_points:
        notes += f"\n💡 **Targeted Coaching**: You noted concerns regarding *\"{pain_points}\"*. I've integrated proactive scaffolding and isolated drills to dismantle those hurdles early."

    notes += "\n\nOnly your first foundational milestone is unlocked. As you verify each milestone with interactive quizzes, I will dynamically evolve and expand the next branches of your skill tree."

    return notes


def _generate_path_nodes(topic, category, goal, baseline, modality, base_time, pain_points, track_type="fast_track") -> List[Dict[str, Any]]:
    cat_lower = category.lower()
    top_lower = topic.lower()

    n0_id = f"node_{uuid.uuid4().hex[:8]}"
    n1_id = f"node_{uuid.uuid4().hex[:8]}"
    n2_id = f"node_{uuid.uuid4().hex[:8]}"
    n3_id = f"node_{uuid.uuid4().hex[:8]}"
    n4_id = f"node_{uuid.uuid4().hex[:8]}"

    if "finance" in cat_lower or "finance" in top_lower or "budget" in top_lower or "invest" in top_lower:
        if track_type == "fast_track":
            return [
                {
                    "id": n0_id,
                    "title": "1. 50/30/20 Cash Allocation & Instant Safety Buffer",
                    "description": "Establish a lean monthly budget blueprint and your first $1,000 liquid safety cushion.",
                    "mentor_rationale": "Immediate financial peace of mind begins with an unbreakable automated safety cushion.",
                    "status": "unlocked",
                    "estimated_time_minutes": base_time,
                    "difficulty": baseline,
                    "prerequisites": [],
                    "coordinates": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "order_index": 0
                },
                {
                    "id": n1_id,
                    "title": "2. High-Yield Savings & Debt Avalanche",
                    "description": "Stop inflation leakage with 4%+ HYSA accounts and execute the highest-APR debt elimination order.",
                    "mentor_rationale": "High-interest debt destroys compounding; eliminating it provides guaranteed risk-free return.",
                    "status": "locked",
                    "estimated_time_minutes": base_time,
                    "difficulty": "beginner",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": -2.8, "y": 2.2, "z": 1.0},
                    "order_index": 1
                },
                {
                    "id": n2_id,
                    "title": "3. Automated Low-Cost Index Investing",
                    "description": "Hands-off wealth creation: Total market ETF allocations with automated recurring monthly deposits.",
                    "mentor_rationale": "Active stock picking underperforms index investing for 90% of retail investors over 10 years.",
                    "status": "locked",
                    "estimated_time_minutes": base_time,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": 2.8, "y": 2.2, "z": -1.0},
                    "order_index": 2
                },
                {
                    "id": n3_id,
                    "title": "4. Personal Wealth Operating System",
                    "description": "Synthesize a 1-page financial dashboard and set-it-and-forget-it automated money rules.",
                    "mentor_rationale": "Systems beat willpower every single time. Autopilot prevents behavioral mistakes during volatility.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "advanced",
                    "prerequisites": [n1_id, n2_id],
                    "coordinates": {"x": 0.0, "y": 5.0, "z": 0.0},
                    "order_index": 3
                }
            ]
        elif track_type == "deep_foundation":
            return [
                {
                    "id": n0_id,
                    "title": "1. Macroeconomic Liquidity & Cash Flow Geometry",
                    "description": "Deep mathematical principles of cash flow cycles, inflation impact, and emergency solvency ratios.",
                    "mentor_rationale": "Understanding the liquidity-solvency spectrum provides resilience across economic recessions.",
                    "status": "unlocked",
                    "estimated_time_minutes": base_time,
                    "difficulty": baseline,
                    "prerequisites": [],
                    "coordinates": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "order_index": 0
                },
                {
                    "id": n1_id,
                    "title": "2. Debt Amortization Mathematics & Capital Cost",
                    "description": "Cost-of-capital calculus, revolving interest structures, and comparative debt optimization models.",
                    "mentor_rationale": "Analyzing debt through cost of capital allows optimal trade-offs between investing vs prepaying debt.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": -2.8, "y": 2.2, "z": 1.0},
                    "order_index": 1
                },
                {
                    "id": n2_id,
                    "title": "3. Modern Portfolio Theory & Asset Allocation",
                    "description": "The efficient frontier, covariance matrices, and risk parity across global equity and bond classes.",
                    "mentor_rationale": "Asset allocation explains over 90% of portfolio return variance over long investment horizons.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": 2.8, "y": 2.2, "z": -1.0},
                    "order_index": 2
                },
                {
                    "id": n3_id,
                    "title": "4. Tax-Advantaged Architecture (Roth vs Traditional)",
                    "description": "Tax arbitrage, marginal bracket projections, backdoor conversions, and tax-loss harvesting rules.",
                    "mentor_rationale": "Taxes and fees are the two biggest drags on long-term compounding; optimizing both accelerates retirement by years.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "advanced",
                    "prerequisites": [n1_id, n2_id],
                    "coordinates": {"x": 0.0, "y": 4.5, "z": 0.5},
                    "order_index": 3
                },
                {
                    "id": n4_id,
                    "title": "5. Multi-Decade Wealth Preservation & Estate Structuring",
                    "description": "Synthesizing dynamic withdrawal strategies (Safe Withdrawal Rate), asset location, and generational preservation.",
                    "mentor_rationale": "The ultimate milestone: engineering a self-perpetuating wealth engine resistant to stagflation and market shocks.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 10,
                    "difficulty": "advanced",
                    "prerequisites": [n3_id],
                    "coordinates": {"x": 0.0, "y": 7.0, "z": 0.0},
                    "order_index": 4
                }
            ]
        else:
            return [
                {
                    "id": n0_id,
                    "title": "1. Build Your Live Personal Net Worth Tracker",
                    "description": "Construct a clean, automated spreadsheet model aggregating all liquid assets, liabilities, and monthly cash flow.",
                    "mentor_rationale": "You cannot optimize what you do not measure. A live dashboard is your foundational cockpit.",
                    "status": "unlocked",
                    "estimated_time_minutes": base_time,
                    "difficulty": baseline,
                    "prerequisites": [],
                    "coordinates": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "order_index": 0
                },
                {
                    "id": n1_id,
                    "title": "2. Deploy an Automated Expense Siphon System",
                    "description": "Configure multi-account banking automation that routes paychecks directly into savings, bills, and guilt-free spending.",
                    "mentor_rationale": "Automated rules prevent friction and guarantee savings before discretionary lifestyle inflation strikes.",
                    "status": "locked",
                    "estimated_time_minutes": base_time,
                    "difficulty": "beginner",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": -2.8, "y": 2.2, "z": 1.0},
                    "order_index": 1
                },
                {
                    "id": n2_id,
                    "title": "3. Construct a 3-Fund Core Portfolio",
                    "description": "Open and configure brokerage accounts to automate purchases of domestic equity, international equity, and bonds.",
                    "mentor_rationale": "Building the portfolio directly gives you immediate skin in the game with institutional diversification.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": 2.8, "y": 2.2, "z": -1.0},
                    "order_index": 2
                },
                {
                    "id": n3_id,
                    "title": "4. Implement Emergency Stress-Test Scenarios",
                    "description": "Simulate sudden job loss or medical emergency in your spreadsheet model to verify buffer resilience.",
                    "mentor_rationale": "Stress-testing your financial plan under simulated hardship proves its structural viability before real crises occur.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n1_id, n2_id],
                    "coordinates": {"x": 0.0, "y": 4.5, "z": 0.5},
                    "order_index": 3
                },
                {
                    "id": n4_id,
                    "title": "5. Capstone: The Complete Personal Financial IPS",
                    "description": "Document an Investment Policy Statement (IPS) codifying your personal financial rules, targets, and rebalancing cadence.",
                    "mentor_rationale": "A written IPS eliminates emotional panic selling during downturns and locks in long-term disciplined success.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 10,
                    "difficulty": "advanced",
                    "prerequisites": [n3_id],
                    "coordinates": {"x": 0.0, "y": 7.0, "z": 0.0},
                    "order_index": 4
                }
            ]

    elif ("music" in top_lower or "guitar" in top_lower or "song" in top_lower or "instrument" in top_lower or ("creative" in cat_lower and not any(k in top_lower for k in ["system", "code", "software", "tech", "program", "data", "api"]))):
        if track_type == "fast_track":
            return [
                {
                    "id": n0_id,
                    "title": "1. The 4 Essential Chords & Clean Frictionless Grips",
                    "description": "Ergonomics, finger placement right behind the frets, and mastering the 4 chords that power 1,000+ songs.",
                    "mentor_rationale": "Focusing on immediate playable chords builds enthusiasm and muscle memory without boring finger drills.",
                    "status": "unlocked",
                    "estimated_time_minutes": base_time,
                    "difficulty": baseline,
                    "prerequisites": [],
                    "coordinates": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "order_index": 0
                },
                {
                    "id": n1_id,
                    "title": "2. Rhythmic Strumming & The Perpetual Motion Hand",
                    "description": "Consistent down-up pendulum strumming and transitioning chords without breaking the rhythmic pulse.",
                    "mentor_rationale": "Rhythm is more important than notes. A steady beat makes simple chords sound musical and confident.",
                    "status": "locked",
                    "estimated_time_minutes": base_time,
                    "difficulty": "beginner",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": -2.8, "y": 2.2, "z": 1.0},
                    "order_index": 1
                },
                {
                    "id": n2_id,
                    "title": "3. Pivot Fingers & Rapid Transition Drills",
                    "description": "Identify common anchor fingers to double chord change speed and eradicate hesitation pause.",
                    "mentor_rationale": "Leaving common fingers anchored minimizes finger travel distance and eliminates hesitation gaps.",
                    "status": "locked",
                    "estimated_time_minutes": base_time,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": 2.8, "y": 2.2, "z": -1.0},
                    "order_index": 2
                },
                {
                    "id": n3_id,
                    "title": "4. Capstone: Performing 3 Complete Songs from Memory",
                    "description": "Play complete songs from beginning to end with intros, dynamic strumming verses, and clean outros.",
                    "mentor_rationale": "Synthesizing technique into actual music performance is the ultimate rewarding milestone of guitar study.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 10,
                    "difficulty": "intermediate",
                    "prerequisites": [n1_id, n2_id],
                    "coordinates": {"x": 0.0, "y": 5.0, "z": 0.0},
                    "order_index": 3
                }
            ]
        elif track_type == "deep_foundation":
            return [
                {
                    "id": n0_id,
                    "title": f"1. Postural Ergonomics & Neuromuscular Motor Independence",
                    "description": "Biomechanical alignment, thumb anchor vectors, minimizing wrist flexion, and isolated finger mobility.",
                    "mentor_rationale": "Tension is the enemy of velocity and longevity. Establishing relaxed posture prevents tendon strain and fatigue.",
                    "status": "unlocked",
                    "estimated_time_minutes": base_time,
                    "difficulty": baseline,
                    "prerequisites": [],
                    "coordinates": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "order_index": 0
                },
                {
                    "id": n1_id,
                    "title": "2. Interval Mechanics, Fretboard Geometry & Ear Tuning",
                    "description": "Mastering the chromatic scale, octaves, fourths/fifths intervals, and hearing pitch relationships across strings.",
                    "mentor_rationale": "Understanding the fretboard as an interval grid frees you from memorizing static shapes without comprehension.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": -2.8, "y": 2.2, "z": 1.0},
                    "order_index": 1
                },
                {
                    "id": n2_id,
                    "title": "3. The CAGED System & Triad Inversions",
                    "description": "Connect 5 movable chord shapes across the entire neck and unlock triad harmony across string sets.",
                    "mentor_rationale": "The CAGED system demystifies the entire fretboard, allowing you to voice any chord in any register instantly.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": 2.8, "y": 2.2, "z": -1.0},
                    "order_index": 2
                },
                {
                    "id": n3_id,
                    "title": "4. Major/Minor Diatonic Harmony & Modal Scales",
                    "description": "Harmonizing the major scale into chords, understanding modal flavors (Dorian, Mixolydian), and melodic contour.",
                    "mentor_rationale": "Diatonic theory allows you to anticipate chord movements in real time and compose captivating melodies.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "advanced",
                    "prerequisites": [n1_id, n2_id],
                    "coordinates": {"x": 0.0, "y": 4.5, "z": 0.5},
                    "order_index": 3
                },
                {
                    "id": n4_id,
                    "title": "5. Capstone: Expressive Improvisation & Dynamic Articulation",
                    "description": "Bending with vibrato control, slides, dynamics, and real-time improvisation over harmonic progressions.",
                    "mentor_rationale": "True artistry: speaking fluently through your instrument with touch, tone, and emotive intent.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 10,
                    "difficulty": "advanced",
                    "prerequisites": [n3_id],
                    "coordinates": {"x": 0.0, "y": 7.0, "z": 0.0},
                    "order_index": 4
                }
            ]
        else:
            return [
                {
                    "id": n0_id,
                    "title": "1. Setting Up Your Acoustic / Electric Practice Rig",
                    "description": "Tuning precisely, picking choice, amp/acoustic tone setup, and establishing clean baseline audio.",
                    "mentor_rationale": "Good tone inspires daily practice. Starting with a properly calibrated setup eliminates acoustic frustration.",
                    "status": "unlocked",
                    "estimated_time_minutes": base_time,
                    "difficulty": baseline,
                    "prerequisites": [],
                    "coordinates": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "order_index": 0
                },
                {
                    "id": n1_id,
                    "title": "2. Record Your First 4-Bar Rhythm Track",
                    "description": "Record clean chord transitions over a click track to assess timing, string buzz, and rhythmic consistency.",
                    "mentor_rationale": "Recording yourself is an objective mirror that pinpoints hesitation points with absolute clarity.",
                    "status": "locked",
                    "estimated_time_minutes": base_time,
                    "difficulty": "beginner",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": -2.8, "y": 2.2, "z": 1.0},
                    "order_index": 1
                },
                {
                    "id": n2_id,
                    "title": "3. Layering Melodic Lead Lines & Pentatonic Fills",
                    "description": "Track a supportive lead melody over your recorded rhythm progression using the minor pentatonic box.",
                    "mentor_rationale": "Layering lead over rhythm immediately teaches how individual instrumental parts interlock into a cohesive song.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": 2.8, "y": 2.2, "z": -1.0},
                    "order_index": 2
                },
                {
                    "id": n3_id,
                    "title": "4. Arranging Song Sections (Intro, Verse, Chorus, Outro)",
                    "description": "Structure dynamic contrast between high-energy chorus strumming and intimate fingerpicked verse passages.",
                    "mentor_rationale": "Arrangement turns repetitive chord loops into memorable emotional journeys.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n1_id, n2_id],
                    "coordinates": {"x": 0.0, "y": 4.5, "z": 0.5},
                    "order_index": 3
                },
                {
                    "id": n4_id,
                    "title": "5. Capstone: Your Multi-Track Portfolio Recording",
                    "description": "Produce, mix, and export a polished audio/video recording of your original arrangement or cover song.",
                    "mentor_rationale": "A finished recording is undeniable proof of your musical capability that you can share with pride.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 10,
                    "difficulty": "advanced",
                    "prerequisites": [n3_id],
                    "coordinates": {"x": 0.0, "y": 7.0, "z": 0.0},
                    "order_index": 4
                }
            ]

    # 3. Default: Technical, Engineering & General Topics
    else:
        if track_type == "fast_track":
            return [
                {
                    "id": n0_id,
                    "title": f"1. Core Mental Models & Key Abstractions of {topic}",
                    "description": f"Master the 20% of terminology, paradigms, and execution patterns that govern {topic}.",
                    "mentor_rationale": "Clear mental models eliminate memorization by letting you intuitively anticipate how components interact.",
                    "status": "unlocked",
                    "estimated_time_minutes": base_time,
                    "difficulty": baseline,
                    "prerequisites": [],
                    "coordinates": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "order_index": 0
                },
                {
                    "id": n1_id,
                    "title": "2. Working Syntax, Tooling & Core Drills",
                    "description": "Executable exercises isolating common operations, APIs, and everyday workflows.",
                    "mentor_rationale": "Hands-on repetition builds fast muscle memory and eliminates syntactic hesitation.",
                    "status": "locked",
                    "estimated_time_minutes": base_time,
                    "difficulty": "beginner",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": -2.8, "y": 2.2, "z": 1.0},
                    "order_index": 1
                },
                {
                    "id": n2_id,
                    "title": "3. Defensive Error Handling & Edge Guards",
                    "description": "Graceful degradation, boundary validations, and isolating common runtime failures.",
                    "mentor_rationale": "Junior solutions work only on the happy path; robust solutions anticipate faults cleanly.",
                    "status": "locked",
                    "estimated_time_minutes": base_time,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": 2.8, "y": 2.2, "z": -1.0},
                    "order_index": 2
                },
                {
                    "id": n3_id,
                    "title": f"4. Capstone: A Working End-to-End {topic} Implementation",
                    "description": f"Synthesize all concepts into a functional, runnable implementation of {topic}.",
                    "mentor_rationale": "Constructing a complete working artifact proves your practical readiness.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 10,
                    "difficulty": "advanced",
                    "prerequisites": [n1_id, n2_id],
                    "coordinates": {"x": 0.0, "y": 5.0, "z": 0.0},
                    "order_index": 3
                }
            ]
        elif track_type == "deep_foundation":
            return [
                {
                    "id": n0_id,
                    "title": f"1. First-Principles Mechanics & System Internals of {topic}",
                    "description": "Memory lifecycle, thread models, execution runtime, and computational complexity.",
                    "mentor_rationale": "Deep mastery means understanding the underlying abstractions beneath high-level frameworks.",
                    "status": "unlocked",
                    "estimated_time_minutes": base_time,
                    "difficulty": baseline,
                    "prerequisites": [],
                    "coordinates": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "order_index": 0
                },
                {
                    "id": n1_id,
                    "title": "2. Explicit Contracts, Interfaces & Invariants",
                    "description": "Defensive architectural boundaries, type safety, and strict state invariants.",
                    "mentor_rationale": "Explicit boundaries minimize cognitive load and eliminate subtle state corruption bugs.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": -2.8, "y": 2.2, "z": 1.0},
                    "order_index": 1
                },
                {
                    "id": n2_id,
                    "title": "3. Concurrency, Asynchrony & Resource Contention",
                    "description": "Non-blocking event loops, atomic locks, race condition avoidance, and backpressure management.",
                    "mentor_rationale": "Real-world production systems live or die by how they handle concurrent load without deadlock.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": 2.8, "y": 2.2, "z": -1.0},
                    "order_index": 2
                },
                {
                    "id": n3_id,
                    "title": "4. Profiling, Benchmarking & Cache Optimization",
                    "description": "Locality of reference, heap allocation reduction, execution profiling, and latency elimination.",
                    "mentor_rationale": "Measure, don't guess. Empirical benchmarks guide optimizations where they actually matter.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "advanced",
                    "prerequisites": [n1_id, n2_id],
                    "coordinates": {"x": 0.0, "y": 4.5, "z": 0.5},
                    "order_index": 3
                },
                {
                    "id": n4_id,
                    "title": f"5. Capstone: Resilient Distributed {topic} Architecture",
                    "description": "Build a multi-tiered architecture with telemetry, self-healing retries, and comprehensive test coverage.",
                    "mentor_rationale": "Putting it all together: a production-grade asset ready for high-traffic enterprise scrutiny.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 10,
                    "difficulty": "advanced",
                    "prerequisites": [n3_id],
                    "coordinates": {"x": 0.0, "y": 7.0, "z": 0.0},
                    "order_index": 4
                }
            ]
        else:
            return [
                {
                    "id": n0_id,
                    "title": f"1. Blueprinting & Bootstrapping the {topic} Project Skeleton",
                    "description": "Configure the repository, directory layout, dependency manifest, and running development harness.",
                    "mentor_rationale": "A clean initial architecture prevents friction and encourages daily incremental commits.",
                    "status": "unlocked",
                    "estimated_time_minutes": base_time,
                    "difficulty": baseline,
                    "prerequisites": [],
                    "coordinates": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "order_index": 0
                },
                {
                    "id": n1_id,
                    "title": "2. Implementing Core Domain Engine & Business Logic",
                    "description": "Code the pure transformation functions, data models, and primary algorithmic logic.",
                    "mentor_rationale": "Keeping core domain logic pure and decoupled from I/O makes it trivial to test and reason about.",
                    "status": "locked",
                    "estimated_time_minutes": base_time,
                    "difficulty": "beginner",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": -2.8, "y": 2.2, "z": 1.0},
                    "order_index": 1
                },
                {
                    "id": n2_id,
                    "title": "3. Integrating External I/O, Storage & API Interfaces",
                    "description": "Connect persistence layers, external network APIs, and user-facing endpoints.",
                    "mentor_rationale": "Wiring domain logic to persistent I/O transforms your theoretical code into a real usable product.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n0_id],
                    "coordinates": {"x": 2.8, "y": 2.2, "z": -1.0},
                    "order_index": 2
                },
                {
                    "id": n3_id,
                    "title": "4. Automated Test Suite & Continuous Integration Pipeline",
                    "description": "Write deterministic unit and integration tests and set up automated pipeline validation.",
                    "mentor_rationale": "A comprehensive test suite gives you the confidence to refactor and expand features without fear.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 5,
                    "difficulty": "intermediate",
                    "prerequisites": [n1_id, n2_id],
                    "coordinates": {"x": 0.0, "y": 4.5, "z": 0.5},
                    "order_index": 3
                },
                {
                    "id": n4_id,
                    "title": f"5. Capstone: Production Packaging, Deployment & Telemetry",
                    "description": "Containerize, deploy to cloud staging, and add health check observability.",
                    "mentor_rationale": "Software isn't complete until it's running in production with real observability.",
                    "status": "locked",
                    "estimated_time_minutes": base_time + 10,
                    "difficulty": "advanced",
                    "prerequisites": [n3_id],
                    "coordinates": {"x": 0.0, "y": 7.0, "z": 0.0},
                    "order_index": 4
                }
            ]


def evaluate_and_evolve_path(nodes: List[Dict[str, Any]], completed_node_id: str, quiz_score: int) -> Dict[str, Any]:
    """Updates completed node and dynamically unlocks or adapts subsequent branches."""
    unlocked_new_nodes = []
    remedial_node = None
    
    # Mark target node as completed
    for n in nodes:
        if n["id"] == completed_node_id:
            n["status"] = "completed"
            n["quiz_score"] = quiz_score

    completed_ids = {n["id"] for n in nodes if n["status"] == "completed"}

    # If user struggled (< 70%), mentor adds an adaptive reinforcement micro-node
    if quiz_score < 70:
        target_node = next((n for n in nodes if n["id"] == completed_node_id), None)
        if target_node:
            remedial_id = f"node_hint_{uuid.uuid4().hex[:6]}"
            remedial_node = {
                "id": remedial_id,
                "title": f"💡 Reinforcement: Core Concepts of {target_node['title']}",
                "description": "A targeted coaching review addressing common misconceptions before proceeding.",
                "mentor_rationale": "I noticed some friction on the assessment. No worries at all—let's solidify the core mental model with a quick guided walkthrough.",
                "status": "unlocked",
                "estimated_time_minutes": 8,
                "difficulty": "beginner",
                "prerequisites": [completed_node_id],
                "coordinates": {
                    "x": target_node["coordinates"]["x"] + 1.2,
                    "y": target_node["coordinates"]["y"] + 0.8,
                    "z": target_node["coordinates"]["z"] + 1.0
                },
                "order_index": target_node["order_index"] + 1
            }
            nodes.append(remedial_node)
            unlocked_new_nodes.append(remedial_node)

    # Check which locked nodes have ALL prerequisites satisfied
    for n in nodes:
        if n["status"] == "locked":
            prereqs = n.get("prerequisites", [])
            if prereqs and all(pid in completed_ids for pid in prereqs):
                n["status"] = "unlocked"
                unlocked_new_nodes.append(n)

    # Calculate overall path completion percentage
    total_nodes = len(nodes)
    completed_count = len([n for n in nodes if n["status"] == "completed"])
    completion_rate = int((completed_count / max(1, total_nodes)) * 100)

    return {
        "nodes": nodes,
        "unlocked_nodes": unlocked_new_nodes,
        "completion_rate": completion_rate,
        "remedial_added": remedial_node is not None
    }
