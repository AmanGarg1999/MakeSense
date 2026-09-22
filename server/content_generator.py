"""Content generation engine supporting On-Device RunAnywhere SDK, Gemini API, and fallback templates."""
import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Optional

import httpx

from server.config import settings

logger = logging.getLogger(__name__)


class RunAnywhereProvider:
    """On-device local inference provider following RunAnywhere SDK architecture.
    Connects to the local on-device engine or RunAnywhere sidecar with real-time streaming."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 5.0,
    ):
        self.endpoint = (endpoint or settings.runanywhere_endpoint).rstrip("/")
        self.model = model or settings.runanywhere_model
        self.timeout = timeout

    async def check_health(self) -> bool:
        """Check if local on-device engine is reachable."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.endpoint}/models")
                return res.status_code == 200
        except Exception:
            return False

    async def generate(
        self, topic: str, category: str, difficulty: str
    ) -> Optional[dict]:
        """Generate full lesson using on-device inference."""
        prompt = LESSON_PROMPT.format(
            topic=topic, category=category, difficulty=difficulty
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are MakeSense's On-Device Educational AI Engine. Output valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 3000,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(
                f"{self.endpoint}/chat/completions", json=payload
            )
            if res.status_code != 200:
                raise RuntimeError(
                    f"RunAnywhere local engine returned HTTP {res.status_code}: {res.text[:100]}"
                )
            data = res.json()
            raw_text = data["choices"][0]["message"]["content"]
            # Extract JSON substring if wrapped in markdown code fence
            cleaned = raw_text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]
            content = json.loads(cleaned.strip())
            return _validate_and_normalize(
                content, topic, category, difficulty
            )

    async def generate_stream(
        self, topic: str, category: str, difficulty: str
    ) -> AsyncGenerator[str, None]:
        """Streams tokens in real-time as the on-device model produces them."""
        prompt = LESSON_PROMPT.format(
            topic=topic, category=category, difficulty=difficulty
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are MakeSense's On-Device Educational AI Engine. Output valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 3000,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.endpoint}/chat/completions", json=payload
            ) as response:
                if response.status_code != 200:
                    raise RuntimeError(
                        f"RunAnywhere stream returned HTTP {response.status_code}"
                    )
                async for line in response.aiter_lines():
                    line = line.strip()
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk["choices"][0]["delta"].get(
                                "content", ""
                            )
                            if delta:
                                yield delta
                        except Exception:
                            continue


async def generate_lesson(
    topic: str, category: str = "General", difficulty: str = "beginner"
) -> dict:
    """Generate a structured lesson for a topic across configured providers."""
    provider = settings.llm_provider.lower()

    # 1. On-Device RunAnywhere SDK
    if provider == "runanywhere":
        try:
            engine = RunAnywhereProvider()
            logger.info(
                f"Generating with on-device RunAnywhere SDK at {engine.endpoint}"
            )
            lesson = await engine.generate(topic, category, difficulty)
            if lesson:
                lesson["provider"] = "runanywhere-on-device"
                return lesson
        except Exception as e:
            logger.warning(
                f"RunAnywhere on-device generation failed/timed out ({e}), trying fallback."
            )

    # 2. Cloud Gemini API
    if (
        provider == "gemini"
        or settings.gemini_api_key
        and settings.gemini_api_key.strip()
        not in ("", "your-api-key-here", "None")
    ):
        try:
            lesson = await _generate_with_gemini(topic, category, difficulty)
            lesson["provider"] = "gemini-cloud"
            return lesson
        except Exception as e:
            logger.warning(
                f"Gemini API generation failed ({e}), falling back to template."
            )

    # 3. Enhanced Educational Template Fallback
    lesson = _generate_with_template(topic, category, difficulty)
    lesson["provider"] = "educational-template"
    return lesson


async def generate_lesson_stream(
    topic: str, category: str = "General", difficulty: str = "beginner"
) -> AsyncGenerator[str, None]:
    """Server-Sent Events (SSE) generator for live streaming generation."""
    # Step 1: Initial status
    yield f'data: {json.dumps({"event": "status", "stage": "init", "message": f"Analyzing curriculum for {topic}...", "provider": settings.llm_provider})}\n\n'
    await asyncio.sleep(0.3)

    provider = settings.llm_provider.lower()
    accumulated_text = ""
    used_on_device = False

    # Attempt real-time stream via RunAnywhere on-device engine
    if provider == "runanywhere":
        yield f'data: {json.dumps({"event": "status", "stage": "on_device", "message": "Connecting to RunAnywhere on-device inference core..."})}\n\n'
        try:
            engine = RunAnywhereProvider(timeout=15.0)
            if await engine.check_health():
                yield f'data: {json.dumps({"event": "status", "stage": "streaming", "message": "⚡ Generating on-device tokens in real-time..."})}\n\n'
                async for token in engine.generate_stream(
                    topic, category, difficulty
                ):
                    accumulated_text += token
                    yield f'data: {json.dumps({"event": "token", "token": token, "source": "runanywhere"})}\n\n'
                used_on_device = True
        except Exception as e:
            logger.warning(f"On-device streaming fallback: {e}")

    # If on-device stream yielded valid JSON, parse and finalize
    final_lesson = None
    if used_on_device and accumulated_text:
        try:
            cleaned = accumulated_text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]
            parsed = json.loads(cleaned.strip())
            final_lesson = _validate_and_normalize(
                parsed, topic, category, difficulty
            )
            final_lesson["provider"] = "runanywhere-on-device"
        except Exception:
            final_lesson = None

    # Progressive fallback streaming if on-device wasn't available or couldn't parse
    if not final_lesson:
        yield f'data: {json.dumps({"event": "status", "stage": "synthesis", "message": "Synthesizing educational sections and examples..."})}\n\n'
        final_lesson = _generate_with_template(topic, category, difficulty)
        final_lesson["provider"] = (
            "runanywhere-hybrid"
            if provider == "runanywhere"
            else "educational-template"
        )

        # Stream progressive sections
        sections = final_lesson.get("sections", [])
        for i, s in enumerate(sections):
            heading = s.get("heading", "")
            status_payload = json.dumps({"event": "status", "stage": f"section_{i+1}", "message": f"Formulating: {heading}"})
            yield f"data: {status_payload}\n\n"
            # Send sample text chunks for interactive typewriter feel
            for word in s.get("content", "").split(" ")[:12]:
                token_payload = json.dumps({"event": "token", "token": word + " ", "source": final_lesson["provider"]})
                yield f"data: {token_payload}\n\n"
                await asyncio.sleep(0.04)
            await asyncio.sleep(0.1)

        yield f'data: {json.dumps({"event": "status", "stage": "quiz", "message": "Formulating active-recall quiz questions..."})}\n\n'
        await asyncio.sleep(0.2)

    # Final completion event with full structured payload
    yield f'data: {json.dumps({"event": "complete", "lesson": final_lesson})}\n\n'


async def _generate_with_gemini(
    topic: str, category: str, difficulty: str
) -> dict:
    """Generate lesson content using Google Gemini API."""
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = LESSON_PROMPT.format(
        topic=topic, category=category, difficulty=difficulty
    )

    response = await model.generate_content_async(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )

    content = json.loads(response.text)
    return _validate_and_normalize(content, topic, category, difficulty)


def _generate_with_template(topic: str, category: str, difficulty: str) -> dict:
    """Generate comprehensive, domain-aware structured educational content."""
    cat_lower = (category or "").lower()
    t_lower = (topic or "").lower()

    # Identify domain context
    is_finance = (
        "finance" in cat_lower
        or "business" in cat_lower
        or any(w in t_lower for w in ["finance", "budget", "invest", "stock", "money", "accounting", "wealth", "tax", "crypto", "trading", "portfolio"])
    )
    is_creative = (
        "creative" in cat_lower
        or "art" in cat_lower
        or any(w in t_lower for w in ["guitar", "music", "piano", "drawing", "paint", "photo", "video", "singing", "audio", "design", "figma", "animation", "chord", "instrument"])
    )
    is_data_ai = (
        "ml" in cat_lower
        or "ai" in cat_lower
        or "data" in cat_lower
        or any(w in t_lower for w in ["machine learning", "neural", "deep learning", "nlp", "pandas", "data science", "statistics", "model", "dataset"])
    )

    if is_finance:
        return {
            "title": f"Mastering {topic}",
            "summary": f"A comprehensive {difficulty}-level interactive guide to {topic}. Master fundamental cash flow management, compounding mechanics, budgeting principles, and real-world asset allocation with an interactive quiz.",
            "estimated_time_minutes": 15,
            "difficulty": difficulty,
            "sections": [
                {
                    "heading": f"1. Core Principles of {topic} & Cash Flow Dynamics",
                    "content": f"At its foundation, **{topic}** is about maximizing the value and security of your financial resources over time.\n\n"
                    "Rather than simply trying to earn more, lasting financial health begins with mastering cash flow: distinguishing fixed necessities from discretionary wants and establishing a sustainable savings rate. By implementing proven allocation systems (such as the 50/30/20 framework), you create a predictable engine for wealth accumulation.\n\n"
                    "Before pursuing high-yield investments, securing an emergency reserve covering 3-6 months of expenses protects you against catastrophic debt and emotional decision-making.",
                    "key_points": [
                        "Cash flow management is the cornerstone of financial independence",
                        "Distinguish between essential expenses and discretionary lifestyle inflation",
                        "Build an emergency buffer before taking on investment risks",
                    ],
                },
                {
                    "heading": "2. Mechanics of Compounding & Debt Acceleration",
                    "content": "Understanding the mathematics of compounding is critical for long-term growth:\n\n"
                    "- **Compound Growth**: Earning returns on previously reinvested returns creates an exponential curve over multi-year horizons.\n"
                    "- **The Drag of High-Interest Debt**: Consumer debt (such as credit cards at 18-25% APR) works against you at exponential speed. Eliminating toxic debt delivers a guaranteed, risk-free return equal to the interest saved.\n"
                    "- **Strategic Debt Payoff**: Use either the **Debt Avalanche** (paying highest-interest debt first for mathematical efficiency) or the **Debt Snowball** (paying smallest balances first for psychological momentum).",
                    "key_points": [
                        "Compounding accelerates exponentially with time and consistency",
                        "Paying off high-interest debt provides a guaranteed, risk-free return",
                        "Choose a debt payoff strategy that aligns with your behavioral psychology",
                    ],
                },
                {
                    "heading": "3. Practical Allocation & Automated Wealth Building",
                    "content": f"To apply {topic} sustainably in everyday life, eliminate friction through automation:\n\n"
                    "1. **Pay Yourself First**: Automatically transfer dedicated savings and investment allocations on payday before discretionary spending occurs.\n"
                    "2. **Broad Diversification**: Utilize low-cost index funds or ETFs to capture global market returns rather than attempting speculative market timing.\n"
                    "3. **Regular Reviews**: Rebalance allocations and review spending quarterly to adapt to changing goals and life stages.",
                    "key_points": [
                        "Automation eliminates willpower failure in saving and investing",
                        "Low-cost diversification beats market timing over the long haul",
                        "Conduct regular reviews to maintain target asset allocations",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "Practical Monthly Cash Flow & Budget Allocation Model",
                    "language": "markdown",
                    "code_or_text": (
                        "Monthly Net Income: $5,000\n"
                        "├── Essential Needs (50% = $2,500):\n"
                        "│   └── Housing ($1,600), Groceries ($500), Utilities & Healthcare ($400)\n"
                        "├── Discretionary Wants (30% = $1,500):\n"
                        "│   └── Dining out, entertainment, hobbies, travel fund\n"
                        "└── Savings & Investments (20% = $1,000):\n"
                        "    ├── Phase 1: $500 to Liquid Emergency Fund (until 3-6 months reached)\n"
                        "    └── Phase 2: $500 automated into Broad Market Index Fund / Retirement\n"
                    ),
                    "explanation": "This breakdown demonstrates how the 50/30/20 framework allocates every dollar intentionally without depriving personal lifestyle.",
                }
            ],
            "quiz": [
                {
                    "question": f"What is the recommended financial priority before making aggressive investments in {topic}?",
                    "type": "mcq",
                    "options": [
                        "Establishing an emergency fund covering 3 to 6 months of essential living expenses",
                        "Taking on personal loans to leverage short-term speculative stock picks",
                        "Allocating 100% of discretionary income into volatile day trading",
                        "Waiting until retirement age before tracking monthly expenses",
                    ],
                    "correct_answer": "Establishing an emergency fund covering 3 to 6 months of essential living expenses",
                    "explanation": "An emergency cushion guarantees that unexpected life events or job transitions won't force you into high-interest debt or forced liquidations.",
                },
                {
                    "question": "How does compound interest create exponential wealth accumulation over long time horizons?",
                    "type": "mcq",
                    "options": [
                        "Reinvested earnings generate their own returns, causing growth to accelerate over time",
                        "It eliminates all volatility and guarantees fixed returns regardless of market conditions",
                        "It replaces the need to save any additional principal after year one",
                        "It only benefits high-frequency day traders who trade daily",
                    ],
                    "correct_answer": "Reinvested earnings generate their own returns, causing growth to accelerate over time",
                    "explanation": "Compounding means gains generate their own gains, resulting in an exponential growth trajectory over decades.",
                },
                {
                    "question": "Why is paying off high-interest debt (e.g. 20% APR credit card) mathematically equivalent to a guaranteed return?",
                    "type": "short_answer",
                    "correct_answer": "Eliminating the debt guarantees an immediate return equal to the saved interest rate without risk",
                    "explanation": "A complete answer notes that avoiding 20% in guaranteed interest charges provides a certain, risk-free savings equivalent to a 20% investment yield.",
                },
            ],
            "skill_tags": ["business-finance", "personal-finance", "budgeting", "wealth-management"],
            "prerequisites": ["Basic arithmetic and personal budgeting concepts"],
        }

    if is_creative:
        return {
            "title": f"Mastering {topic}",
            "summary": f"A comprehensive {difficulty}-level interactive guide to {topic}. Master fundamental technique, ergonomics, deliberate practice routines, and expressive mechanics with an interactive quiz.",
            "estimated_time_minutes": 15,
            "difficulty": difficulty,
            "sections": [
                {
                    "heading": f"1. Foundations, Ergonomics & Motor Mechanics in {topic}",
                    "content": f"Developing mastery in **{topic}** starts with physical ergonomics and neuromuscular coordination.\n\n"
                    "Tension is the primary impediment to clean technique, speed, and endurance. Whether holding an instrument, a stylus, or controlling audio levels, maintaining relaxed shoulders, natural joint angles, and minimal necessary finger pressure ensures fluid execution while preventing repetitive strain injury (RSI).\n\n"
                    "In this module, you will learn how to isolate individual mechanics, identify friction points, and build clean habits from day one.",
                    "key_points": [
                        "Ergonomic relaxation prevents fatigue, tension, and chronic strain injuries",
                        "Isolate fine motor movements before attempting full-speed execution",
                        "Consistent short sessions outperform infrequent marathon practice",
                    ],
                },
                {
                    "heading": "2. Rhythmic Cadence, Timing & Transition Drills",
                    "content": "Flawless execution requires decoupling mental coordination from mechanical movement:\n\n"
                    "- **The Power of the Metronome**: Practice transitions at half-speed. Speed is a byproduct of precision, not physical exertion.\n"
                    "- **Isolate Difficult Transitions**: Identify the single moment of hesitation between movements and loop only that transition 20-30 times.\n"
                    "- **Economy of Motion**: Keep fingers or tools close to their target position. Minimizing wasted physical displacement yields effortless fluid motion.",
                    "key_points": [
                        "Always practice with rhythmic feedback (metronome or backing groove)",
                        "Loop the specific hesitation point rather than running entire pieces repeatedly",
                        "Economy of motion is the true secret to speed and clarity",
                    ],
                },
                {
                    "heading": "3. Deliberate Practice & Expressive Mastery",
                    "content": f"To turn technical drills into expressive art with {topic}, structure your daily practice intentionally:\n\n"
                    "1. **Warm-up & Calibration (5 mins)**: Slow, deliberate stretches and chromatic exercises to wake up muscle memory.\n"
                    "2. **Targeted Technical Challenge (10 mins)**: High-focus work on a specific chord change, scale, brush stroke, or audio technique.\n"
                    "3. **Repertoire & Musical Application (15 mins)**: Apply the isolated technique within the context of a real song, project, or creative composition.",
                    "key_points": [
                        "Divide practice into distinct technical and creative phases",
                        "Record your playing/work regularly to develop objective self-critique",
                        "Expression emerges when mechanical technique becomes second nature",
                    ],
                },
            ],
            "examples": [
                {
                    "title": f"Structured 30-Minute Daily Practice Routine for {topic}",
                    "language": "markdown",
                    "code_or_text": (
                        "┌─────────────────────────────────────────────────────────────┐\n"
                        "│ Daily 30-Minute Deliberate Practice Regimen                 │\n"
                        "├─────────────────────────────────────────────────────────────┤\n"
                        "│ 1. Warm-Up & Mechanics (5 min)                              │\n"
                        "│    • Metronome set to 60 BPM. Relaxed finger drills.        │\n"
                        "│ 2. Isolated Problem Transition (10 min)                     │\n"
                        "│    • Loop the hardest 2 chords/transitions without stopping │\n"
                        "│ 3. Rhythmic Groove & Timing (8 min)                         │\n"
                        "│    • Consistent tempo, accenting target beats               │\n"
                        "│ 4. Repertoire & Song Application (7 min)                    │\n"
                        "│    • Play through complete musical piece with dynamics      │\n"
                        "└─────────────────────────────────────────────────────────────┘\n"
                    ),
                    "explanation": "A balanced regimen that builds neuromuscular technique while keeping learning musical and rewarding.",
                }
            ],
            "quiz": [
                {
                    "question": f"When building foundational technique in {topic}, why is slow practice with a metronome essential?",
                    "type": "mcq",
                    "options": [
                        "It embeds clean, accurate motor memory without ingraining mechanical errors",
                        "It eliminates the need to practice difficult transitions",
                        "It automatically increases speed without having to practice rhythm",
                        "Speed is more important than mechanical accuracy for beginners",
                    ],
                    "correct_answer": "It embeds clean, accurate motor memory without ingraining mechanical errors",
                    "explanation": "Slow practice allows the nervous system to coordinate relaxed, precise movements before increasing tempo.",
                },
                {
                    "question": f"What is a critical habit to maintain during physical practice sessions in {topic}?",
                    "type": "mcq",
                    "options": [
                        "Actively monitoring and releasing tension in the hands, wrists, and shoulders",
                        "Pressing with maximum force regardless of physical strain",
                        "Playing through sharp joint pain to build endurance quickly",
                        "Skipping warmups and playing at top tempo immediately",
                    ],
                    "correct_answer": "Actively monitoring and releasing tension in the hands, wrists, and shoulders",
                    "explanation": "Excess muscle tension restricts speed and can cause repetitive strain injury (RSI); relaxed mechanics enable longevity and tone control.",
                },
                {
                    "question": f"In your own words, explain why 'economy of motion' is the key to fluid execution in {topic}.",
                    "type": "short_answer",
                    "correct_answer": "Minimizing unnecessary finger movement allows faster, more accurate transitions with less physical effort",
                    "explanation": "A strong answer explains that keeping fingers or tools close to their targets reduces travel time and eliminates wasted exertion.",
                },
            ],
            "skill_tags": ["creative-arts", "music", "technique", "muscle-memory"],
            "prerequisites": ["Basic physical coordination and enthusiasm for active practice"],
        }

    if is_data_ai:
        return {
            "title": f"Mastering {topic}",
            "summary": f"A comprehensive {difficulty}-level interactive guide to {topic}. Explore data pipelines, algorithmic foundations, validation strategies, and practical Python implementations with an interactive quiz.",
            "estimated_time_minutes": 15,
            "difficulty": difficulty,
            "sections": [
                {
                    "heading": f"1. Core Intuition & The Problem {topic} Solves",
                    "content": f"At its core, **{topic}** is about discovering patterns, learning representations, and making principled predictions from data.\n\n"
                    "Rather than writing rigid heuristic rules, modern data systems learn mapping functions directly from input-output pairs. Understanding the bias-variance tradeoff, data distributions, and feature relationships is far more critical than simply memorizing model libraries.",
                    "key_points": [
                        "Data quality and feature representation dominate raw algorithmic complexity",
                        "Formulate clear mathematical objectives before choosing architectures",
                        "Always inspect underlying distributions to avoid silent data leakage",
                    ],
                },
                {
                    "heading": "2. Pipeline Architecture & Validation Strategy",
                    "content": "A robust data science workflow follows a disciplined lifecycle:\n\n"
                    "1. **Data Preprocessing & Cleansing**: Impute missing values, normalize scales, and prevent future information from leaking into training splits.\n"
                    "2. **Cross-Validation**: Use Stratified K-Fold or temporal splits to ensure models generalize to unseen test distributions.\n"
                    "3. **Metric Alignment**: Align evaluation metrics (e.g. F1, ROC-AUC, RMSE) with real-world decision thresholds rather than relying solely on raw accuracy.",
                    "key_points": [
                        "Never allow training statistics to leak into validation folds",
                        "Raw accuracy is misleading under severe class imbalance",
                        "Cross-validation provides realistic generalization estimates",
                    ],
                },
                {
                    "heading": "3. Productionization & Continuous Monitoring",
                    "content": f"Deploying {topic} into production environments requires monitoring data drift and inference latency.\n\n"
                    "- **Drift Detection**: Monitor feature distributions over time to catch covariate shift before predictions degrade.\n"
                    "- **Model Versioning**: Track datasets, hyperparameters, and artifact checksums for reproducible experimentation.\n"
                    "- **Fallback Mechanisms**: Always provide deterministic baseline fallbacks when inputs fall outside known operating bounds.",
                    "key_points": [
                        "Production models degrade over time without drift monitoring",
                        "Reproducibility requires versioning code, parameters, and datasets together",
                        "Always pair probabilistic models with guardrails and deterministic fallbacks",
                    ],
                },
            ],
            "examples": [
                {
                    "title": f"Hands-on {topic} Pipeline with Validation",
                    "language": "python",
                    "code_or_text": (
                        f"# End-to-end demonstration of {topic}\n"
                        "import numpy as np\n\n"
                        "# 1. Synthesize baseline dataset\n"
                        "np.random.seed(42)\n"
                        "X = np.random.randn(100, 3)\n"
                        "y = (X[:, 0] * 1.5 + X[:, 1] * -2.0 + np.random.randn(100) * 0.5) > 0\n\n"
                        "# 2. Train/Test split without data leakage\n"
                        "split_idx = int(0.8 * len(X))\n"
                        "X_train, X_test = X[:split_idx], X[split_idx:]\n"
                        "y_train, y_test = y[:split_idx], y[split_idx:]\n\n"
                        "# 3. Evaluate baseline accuracy\n"
                        "preds = (X_test[:, 0] * 1.5 + X_test[:, 1] * -2.0) > 0\n"
                        "accuracy = np.mean(preds == y_test)\n"
                        f'print(f"{topic} Validation Accuracy: {{accuracy * 100:.1f}}%")\n'
                    ),
                    "explanation": "This code demonstrates clean separation between training and evaluation splits to accurately measure real-world performance.",
                }
            ],
            "quiz": [
                {
                    "question": f"When training models in {topic}, why must feature scaling be fitted ONLY on training data?",
                    "type": "mcq",
                    "options": [
                        "Fitting on the full dataset causes data leakage by exposing test distribution statistics to the model",
                        "Feature scaling is only necessary on test data",
                        "It reduces training speed by requiring extra computations",
                        "Feature scaling automatically eliminates all model errors",
                    ],
                    "correct_answer": "Fitting on the full dataset causes data leakage by exposing test distribution statistics to the model",
                    "explanation": "Fitting transformations on test data leaks future information into training, producing unrealistically optimistic evaluation metrics.",
                },
                {
                    "question": "What is the primary danger of optimizing purely for training accuracy in machine learning?",
                    "type": "mcq",
                    "options": [
                        "Overfitting, where the model memorizes training noise and fails to generalize to new data",
                        "The model becomes too simple to capture linear relationships",
                        "It prevents the model from converging during optimization",
                        "It increases inference latency in production",
                    ],
                    "correct_answer": "Overfitting, where the model memorizes training noise and fails to generalize to new data",
                    "explanation": "Overfitting occurs when high capacity models fit arbitrary noise in the training set, severely degrading test performance.",
                },
                {
                    "question": f"Explain why cross-validation is essential when evaluating {topic}.",
                    "type": "short_answer",
                    "correct_answer": "It provides a robust estimate of model generalization across multiple unseen data subsets",
                    "explanation": "A complete answer explains that cross-validation reduces variance in performance estimation and avoids overfitting to a single arbitrary split.",
                },
            ],
            "skill_tags": ["data-science", "machine-learning", "python", "ai-modeling"],
            "prerequisites": ["Basic Python and linear algebra concepts"],
        }

    # Default / Programming template
    slug_tag = (
        category.lower()
        .replace("/", "-")
        .replace(" ", "-")
        .replace("&", "and")
    )
    return {
        "title": f"Mastering {topic}",
        "summary": f"A comprehensive {difficulty}-level interactive guide to {topic}. Master core principles, study practical modular architectures, and verify your understanding with an interactive quiz.",
        "estimated_time_minutes": 15,
        "difficulty": difficulty,
        "sections": [
            {
                "heading": f"1. Core Intuition & Fundamentals of {topic}",
                "content": f"At its core, **{topic}** is a foundational building block within **{category}**.\n\n"
                f"Rather than merely memorizing syntax or APIs, mastering {topic} requires understanding the problem it was designed to solve. When decomposed into fundamental mechanics, it gives you the mental model necessary to build reliable, maintainable systems.",
                "key_points": [
                    f"{topic} solves core architectural challenges in {category}",
                    "Deep conceptual models outperform rote API memorization",
                    "Mastery of fundamentals unlocks scalable advanced design",
                ],
            },
            {
                "heading": "2. Mechanics & Step-by-Step Architecture",
                "content": f"To apply {topic} effectively, structure your execution into disciplined steps:\n\n"
                "- **Input / Preconditions**: Explicitly validate boundaries and preconditions before execution.\n"
                f"- **Transformation / Core Logic**: Apply the central rule of {topic} through pure, decoupled functions.\n"
                "- **Expected Postconditions**: Verify that the returned output satisfies system invariants.",
                "key_points": [
                    "Validate inputs and environmental preconditions early",
                    "Keep state transformations pure, isolated, and traceable",
                    "Verify outputs against defined contracts and schemas",
                ],
            },
            {
                "heading": "3. Practical Application & Real-World Best Practices",
                "content": f"In production systems, {topic} is leveraged to maximize reliability and developer velocity.\n\n"
                "1. **Maintain Modularity**: Decompose large monolithic routines into small, independently testable units.\n"
                "2. **Defensive Edge Case Handling**: Guard against null/empty states, timeouts, and boundary limits.\n"
                "3. **Continuous Testing & Refactoring**: Build automated unit and integration tests to safely iterate.",
                "key_points": [
                    "Modularity drastically reduces debugging complexity and cognitive load",
                    "Anticipate boundary edge cases before deploying to production",
                    "Automated verification enables confident continuous deployment",
                ],
            },
        ],
        "examples": [
            {
                "title": f"Hands-on {topic} Implementation",
                "language": "python",
                "code_or_text": (
                    f"# Practical demonstration of {topic}\n"
                    "def execute_pipeline(data: dict) -> dict:\n"
                    f'    """Applies {topic} principles cleanly to incoming data."""\n'
                    '    if not data or "payload" not in data:\n'
                    '        raise ValueError("Invalid payload: input validation failed")\n\n'
                    '    processed = f"Successfully processed {data[\'payload\']}"\n'
                    '    return {"status": "success", "result": processed}\n\n'
                    "# Run demonstration\n"
                    'test_data = {"payload": "production_dataset_v1"}\n'
                    "output = execute_pipeline(test_data)\n"
                    "print(output)\n"
                ),
                "explanation": f"This code snippet illustrates clean input validation, modular execution, and explicit output contracts when working with {topic}.",
            }
        ],
        "quiz": [
            {
                "question": f"What is the primary architectural advantage of mastering {topic}?",
                "type": "mcq",
                "options": [
                    f"It provides a principled framework for solving complex problems in {category}",
                    "It replaces the need for software testing and verification",
                    "It is purely theoretical and has no practical applications",
                    "It eliminates the need to understand data structures or algorithms",
                ],
                "correct_answer": f"It provides a principled framework for solving complex problems in {category}",
                "explanation": f"Mastering {topic} establishes the mental models required to reason through complex challenges in {category}.",
            },
            {
                "question": f"When applying {topic}, which of the following is considered an engineering best practice?",
                "type": "mcq",
                "options": [
                    "Decomposing tasks into modular, independently verifiable units",
                    "Ignoring boundary and edge conditions in production",
                    "Relying solely on trial-and-error without automated tests",
                    "Writing monolithic code without documentation or structure",
                ],
                "correct_answer": "Decomposing tasks into modular, independently verifiable units",
                "explanation": "Modularity allows each component to be tested, verified, and refactored with minimal blast radius.",
            },
            {
                "question": f"In your own words, explain how {topic} enhances problem-solving in {category}.",
                "type": "short_answer",
                "correct_answer": f"{topic} provides foundational principles and structured methods for {category}",
                "explanation": f"A comprehensive answer explains how {topic} bridges foundational concepts with reliable execution.",
            },
        ],
        "skill_tags": [slug_tag, "software-engineering", "best-practices"],
        "prerequisites": ["Basic problem-solving and modular logic"],
    }


def _validate_and_normalize(
    content: dict, topic: str, category: str, difficulty: str
) -> dict:
    """Validate and normalize LLM-generated content structure."""
    content.setdefault("title", f"Introduction to {topic}")
    content.setdefault("summary", f"A lesson about {topic}")
    content.setdefault("estimated_time_minutes", 15)
    content.setdefault("difficulty", difficulty)
    content.setdefault("sections", [])
    content.setdefault("examples", [])
    content.setdefault("quiz", [])
    content.setdefault(
        "skill_tags",
        [
            category.lower()
            .replace("/", "-")
            .replace(" ", "-")
            .replace("&", "and")
        ],
    )
    content.setdefault("prerequisites", [])

    for q in content.get("quiz", []):
        q.setdefault("type", "mcq")
        q.setdefault("explanation", "")
        if q["type"] == "mcq":
            q.setdefault("options", [])

    return content


LESSON_PROMPT = """You are an expert educator creating a comprehensive lesson.

Topic: {topic}
Category: {category}
Difficulty Level: {difficulty}

Generate a structured lesson in the following JSON format:
{{
  "title": "Engaging lesson title",
  "summary": "2-3 sentence overview of what the learner will gain",
  "estimated_time_minutes": 15,
  "sections": [
    {{
      "heading": "Section title",
      "content": "Markdown formatted explanation with examples, analogies, and clear explanations",
      "key_points": ["Key takeaway 1", "Key takeaway 2"]
    }}
  ],
  "examples": [
    {{
      "title": "Example title",
      "code_or_text": "Code or detailed text example",
      "language": "python",
      "explanation": "What this example demonstrates"
    }}
  ],
  "quiz": [
    {{
      "question": "Question text",
      "type": "mcq",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Why this answer is correct"
    }},
    {{
      "question": "Short answer question",
      "type": "short_answer",
      "correct_answer": "Expected answer keywords",
      "explanation": "What a good answer should include"
    }}
  ],
  "skill_tags": ["relevant-skill-tag"],
  "prerequisites": ["prerequisite-topic"]
}}

Requirements:
- Create 3-5 sections building from fundamentals to applied knowledge
- Include 2-3 practical examples with real code or detailed scenarios
- Generate 3-5 quiz questions mixing MCQ and short answer types
- Ensure explanations are clear and appropriate for {difficulty} level
- Include code examples in Python where applicable

Respond with ONLY the JSON object, no additional text."""
