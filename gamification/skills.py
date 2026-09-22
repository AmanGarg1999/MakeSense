"""
Gamification Skill Rating System

Implements Bayesian skill inference for user proficiency tracking.
Used by nightly cron job and real-time answer processing.
"""

from dataclasses import dataclass
from typing import Optional
import json
import asyncpg
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillRatingConfig:
    """Configuration for Bayesian skill rating."""
    prior_weight: float = 10.0          # Equivalent to 10 "average" evidences
    global_average: float = 50.0        # Global mean proficiency (0-100)
    min_evidence_for_ranking: int = 3   # Minimum evidence to appear on leaderboards
    confidence_scaling: float = 1.0     # Confidence multiplier


@dataclass
class SkillEvidence:
    """Single piece of evidence for skill rating."""
    skill_tag: str
    score: float                        # 0-100 score for this evidence
    weight: float = 1.0                 # Evidence weight (difficulty, recency, etc.)
    source_type: str = "question_answer"
    source_id: Optional[int] = None
    metadata: Optional[dict] = None


class SkillRatingEngine:
    """
    Bayesian skill rating engine.

    Uses conjugate prior (Beta-Binomial approximation) for proficiency estimation:
    - Prior: Beta(alpha=prior_weight * global_avg/100, beta=prior_weight * (1-global_avg/100))
    - Evidence: Each observation adds to alpha/beta based on score/weight
    - Posterior mean: (alpha + sum(score*weight)) / (alpha + beta + sum(weights))
    """

    def __init__(self, pool: asyncpg.Pool, config: Optional[SkillRatingConfig] = None):
        self.pool = pool
        self.config = config or SkillRatingConfig()

    async def update_skill_rating(
        self,
        user_id: int,
        skill_tag: str,
        evidence_score: float,
        evidence_weight: float = 1.0
    ) -> dict:
        """
        Update a single skill rating with new evidence.

        Returns updated rating info.
        """
        async with self.pool.acquire() as conn:
            # Get current rating
            current = await conn.fetchrow("""
                SELECT proficiency_score, evidence_count, confidence
                FROM user_skill_ratings
                WHERE user_id = $1 AND skill_tag = $2
            """, user_id, skill_tag)

            prior_weight = self.config.prior_weight
            global_avg = self.config.global_average

            if current is None:
                # First evidence for this skill
                new_count = 1
                new_score = evidence_score
                new_confidence = evidence_weight / (prior_weight + evidence_weight)
            else:
                # Bayesian update
                current_score = current['proficiency_score']
                current_count = current['evidence_count']

                new_count = current_count + 1
                # Weighted average with prior
                numerator = (prior_weight * global_avg +
                           current_score * current_count +
                           evidence_score * evidence_weight)
                denominator = prior_weight + current_count + evidence_weight
                new_score = numerator / denominator
                new_confidence = (current_count + evidence_weight) / denominator

            # Upsert
            await conn.execute("""
                INSERT INTO user_skill_ratings (user_id, skill_tag, proficiency_score, evidence_count, confidence, last_updated)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (user_id, skill_tag) DO UPDATE SET
                    proficiency_score = $3,
                    evidence_count = $4,
                    confidence = $5,
                    last_updated = NOW()
            """, user_id, skill_tag, round(new_score), new_count, new_confidence)

            return {
                'user_id': user_id,
                'skill_tag': skill_tag,
                'proficiency_score': round(new_score),
                'evidence_count': new_count,
                'confidence': round(new_confidence, 4)
            }

    async def batch_update_skills(
        self,
        user_id: int,
        evidence_list: list[SkillEvidence]
    ) -> list[dict]:
        """
        Update multiple skills in a single transaction.

        More efficient than individual calls.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                results = []
                for evidence in evidence_list:
                    current = await conn.fetchrow("""
                        SELECT proficiency_score, evidence_count, confidence
                        FROM user_skill_ratings
                        WHERE user_id = $1 AND skill_tag = $2
                    """, user_id, evidence.skill_tag)

                    prior_weight = self.config.prior_weight
                    global_avg = self.config.global_average

                    if current is None:
                        new_count = 1
                        new_score = evidence.score
                        new_confidence = evidence.weight / (prior_weight + evidence.weight)
                    else:
                        current_score = current['proficiency_score']
                        current_count = current['evidence_count']

                        new_count = current_count + 1
                        numerator = (prior_weight * global_avg +
                                   current_score * current_count +
                                   evidence.score * evidence.weight)
                        denominator = prior_weight + current_count + evidence.weight
                        new_score = numerator / denominator
                        new_confidence = (current_count + evidence.weight) / denominator

                    await conn.execute("""
                        INSERT INTO user_skill_ratings (user_id, skill_tag, proficiency_score, evidence_count, confidence, last_updated)
                        VALUES ($1, $2, $3, $4, $5, NOW())
                        ON CONFLICT (user_id, skill_tag) DO UPDATE SET
                            proficiency_score = $3,
                            evidence_count = $4,
                            confidence = $5,
                            last_updated = NOW()
                    """, user_id, evidence.skill_tag, round(new_score), new_count, new_confidence)

                    results.append({
                        'user_id': user_id,
                        'skill_tag': evidence.skill_tag,
                        'proficiency_score': round(new_score),
                        'evidence_count': new_count,
                        'confidence': round(new_confidence, 4)
                    })

                return results

    async def get_user_skills(
        self,
        user_id: int,
        min_evidence: int = 0,
        limit: int = 50
    ) -> list[dict]:
        """Get all skills for a user, ordered by proficiency."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT skill_tag, proficiency_score, evidence_count, confidence, last_updated
                FROM user_skill_ratings
                WHERE user_id = $1 AND evidence_count >= $2
                ORDER BY proficiency_score DESC, evidence_count DESC
                LIMIT $3
            """, user_id, min_evidence, limit)

            return [dict(row) for row in rows]

    async def get_top_users_for_skill(
        self,
        skill_tag: str,
        limit: int = 10,
        min_evidence: int = 3
    ) -> list[dict]:
        """Get leaderboard for a specific skill."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, proficiency_score, evidence_count, confidence
                FROM user_skill_ratings
                WHERE skill_tag = $1 AND evidence_count >= $2
                ORDER BY proficiency_score DESC, evidence_count DESC
                LIMIT $3
            """, skill_tag, min_evidence, limit)

            return [dict(row) for row in rows]

    async def get_skill_distribution(self, skill_tag: str) -> dict:
        """Get statistics for a skill across all users."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_users,
                    AVG(proficiency_score)::numeric(5,2) as avg_score,
                    MIN(proficiency_score) as min_score,
                    MAX(proficiency_score) as max_score,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY proficiency_score) as median_score,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY proficiency_score) as p25_score,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY proficiency_score) as p75_score,
                    AVG(evidence_count)::numeric(5,2) as avg_evidence,
                    AVG(confidence)::numeric(5,4) as avg_confidence
                FROM user_skill_ratings
                WHERE skill_tag = $1
            """, skill_tag)

            return dict(row) if row else {}

    async def recalculate_all_skills(self, batch_size: int = 1000) -> dict:
        """
        Full recalculation of all skill ratings from raw evidence.

        Used for:
        - Initial population from historical data
        - Correction after algorithm changes
        - Periodic reconciliation

        Returns summary statistics.
        """
        async with self.pool.acquire() as conn:
            # Get all evidence from engagement_points
            # This assumes engagement_points has skill_tags in source_metadata
            evidence_rows = await conn.fetch("""
                SELECT
                    ep.user_id,
                    ep.source_metadata->>'skill_tag' as skill_tag,
                    CASE
                        WHEN ep.source_type = 'question_answer_correct' THEN 100
                        WHEN ep.source_type = 'question_answer_incorrect' THEN 0
                        WHEN ep.source_type = 'course_completion' THEN 80
                        WHEN ep.source_type = 'lesson_completion' THEN 60
                        ELSE 50
                    END as base_score,
                    COALESCE((ep.source_metadata->>'difficulty')::float, 1.0) as weight,
                    ep.created_at
                FROM engagement_points ep
                WHERE ep.source_metadata ? 'skill_tag'
                AND ep.points > 0
                ORDER BY ep.user_id, ep.created_at
            """)

            # Group by user+skill and recalculate
            from collections import defaultdict
            user_skill_evidence = defaultdict(list)

            for row in evidence_rows:
                if row['skill_tag']:
                    user_skill_evidence[(row['user_id'], row['skill_tag'])].append({
                        'score': row['base_score'],
                        'weight': row['weight']
                    })

            updated = 0
            for (user_id, skill_tag), evidences in user_skill_evidence.items():
                # Recalculate from scratch using all evidence
                prior_weight = self.config.prior_weight
                global_avg = self.config.global_average

                total_weight = sum(e['weight'] for e in evidences)
                weighted_sum = sum(e['score'] * e['weight'] for e in evidences)

                new_score = (prior_weight * global_avg + weighted_sum) / (prior_weight + total_weight)
                new_count = len(evidences)
                new_confidence = total_weight / (prior_weight + total_weight)

                await conn.execute("""
                    INSERT INTO user_skill_ratings (user_id, skill_tag, proficiency_score, evidence_count, confidence, last_updated)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (user_id, skill_tag) DO UPDATE SET
                        proficiency_score = $3,
                        evidence_count = $4,
                        confidence = $5,
                        last_updated = NOW()
                """, user_id, skill_tag, round(new_score), new_count, new_confidence)
                updated += 1

            return {
                'total_user_skill_pairs': len(user_skill_evidence),
                'updated': updated,
                'evidence_processed': len(evidence_rows)
            }


async def create_skill_rating_engine(
    dsn: str,
    config: Optional[SkillRatingConfig] = None
) -> SkillRatingEngine:
    """Factory function to create engine with connection pool."""
    pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    return SkillRatingEngine(pool, config)


# ============================================================================
# Nightly Job Script
# ============================================================================

async def nightly_skill_recalculation(dsn: str) -> dict:
    """
    Nightly cron job to recalculate all skill ratings from raw evidence.

    This ensures:
    - Ratings stay consistent with raw data
    - New skills from taxonomy are picked up
    - Algorithm changes are applied retroactively
    - Confidence intervals are recalculated
    """
    engine = await create_skill_rating_engine(dsn)

    try:
        logger.info("Starting nightly skill recalculation...")
        result = await engine.recalculate_all_skills()
        logger.info(f"Nightly recalculation complete: {result}")
        return result
    finally:
        await engine.pool.close()


async def update_skill_taxonomy_from_content(dsn: str) -> dict:
    """
    Sync skill_taxonomy from content metadata.

    Reads distinct skill tags from courses/questions and ensures
    they exist in skill_taxonomy table.
    """
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)

    try:
        async with pool.acquire() as conn:
            # Get distinct skill tags from content (assuming content tables exist)
            # TODO: Query skill tags from lessons table instead of hypothetical content_skills table
            # For now, return existing taxonomy without content-driven updates
            logger.info("Syncing skill_taxonomy from content metadata is currently a no-op.")
            skill_tags = []

            inserted = 0
            updated = 0

            for row in skill_tags:
                result = await conn.execute("""
                    INSERT INTO skill_taxonomy (skill_tag, display_name, category, difficulty, is_active)
                    VALUES ($1, $2, $3, $4, TRUE)
                    ON CONFLICT (skill_tag) DO UPDATE SET
                        category = $3,
                        difficulty = $4,
                        is_active = TRUE,
                        updated_at = NOW()
                """, row['skill_tag'], row['skill_tag'].replace('-', ' ').title(),
                    row['category'], row['difficulty'])

                if 'INSERT' in result:
                    inserted += 1
                else:
                    updated += 1

            return {'inserted': inserted, 'updated': updated}
    finally:
        await pool.close()


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import asyncio
    import os
    import sys

    async def main():
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            print("DATABASE_URL environment variable required", file=sys.stderr)
            sys.exit(1)

        if len(sys.argv) > 1 and sys.argv[1] == "recalculate":
            result = await nightly_skill_recalculation(dsn)
            print(json.dumps(result, indent=2))
        elif len(sys.argv) > 1 and sys.argv[1] == "sync-taxonomy":
            result = await update_skill_taxonomy_from_content(dsn)
            print(json.dumps(result, indent=2))
        else:
            print("Usage: python -m gamification.skills [recalculate|sync-taxonomy]")
            sys.exit(1)

    asyncio.run(main())