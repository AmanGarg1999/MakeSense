"""
Skill Ladder Service

Handles goal-relative skill ladder instantiation, track CRUD operations,
and cross-track dashboard functionality.
"""

import json
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

import asyncpg
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillLadderRung:
    """A single rung/level in a skill ladder."""
    level_index: int
    level_name: str
    sub_skills: List[Dict[str, Any]]
    prerequisites: List[str]
    evidence_types: List[str]
    xp_reward: int


@dataclass
class SkillLadder:
    """Complete skill ladder for a skill_tag + goal_type combination."""
    skill_tag: str
    goal_type: str
    rungs: List[SkillLadderRung]


@dataclass
class SkillTrack:
    """A user's active learning track."""
    id: str
    user_id: int
    skill_graph_ref: str
    skill_tag: str
    goal_level: str
    goal_type: str
    mastery_vector: Dict[str, Any]
    batch_schedule: Dict[str, Any]
    coach_narrative: Optional[str]
    status: str
    progress_pct: float
    current_ladder_rung: int
    started_at: datetime
    paused_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_activity_at: datetime


class SkillLadderService:
    """Service for managing skill ladders and tracks."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # ========================================================================
    # Skill Ladder Queries
    # ========================================================================

    async def get_ladder(self, skill_tag: str, goal_type: str) -> Optional[SkillLadder]:
        """Get the complete ladder for a skill + goal type."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT level_index, level_name, sub_skills, prerequisites, evidence_types, xp_reward
                FROM skill_ladders
                WHERE skill_tag = $1 AND goal_type = $2 AND is_active = TRUE
                ORDER BY level_index
            """, skill_tag, goal_type)

            if not rows:
                return None

            rungs = [
                SkillLadderRung(
                    level_index=row['level_index'],
                    level_name=row['level_name'],
                    sub_skills=row['sub_skills'] if isinstance(row['sub_skills'], list) else json.loads(row['sub_skills']),
                    prerequisites=row['prerequisites'] if isinstance(row['prerequisites'], list) else json.loads(row['prerequisites']),
                    evidence_types=row['evidence_types'] if isinstance(row['evidence_types'], list) else json.loads(row['evidence_types']),
                    xp_reward=row['xp_reward']
                )
                for row in rows
            ]

            return SkillLadder(skill_tag=skill_tag, goal_type=goal_type, rungs=rungs)

    async def get_ladder_rung(self, skill_tag: str, goal_type: str, level_index: int) -> Optional[SkillLadderRung]:
        """Get a specific rung of a ladder."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT level_index, level_name, sub_skills, prerequisites, evidence_types, xp_reward
                FROM skill_ladders
                WHERE skill_tag = $1 AND goal_type = $2 AND level_index = $3 AND is_active = TRUE
            """, skill_tag, goal_type, level_index)

            if not row:
                return None

            return SkillLadderRung(
                level_index=row['level_index'],
                level_name=row['level_name'],
                sub_skills=row['sub_skills'] if isinstance(row['sub_skills'], list) else json.loads(row['sub_skills']),
                prerequisites=row['prerequisites'] if isinstance(row['prerequisites'], list) else json.loads(row['prerequisites']),
                evidence_types=row['evidence_types'] if isinstance(row['evidence_types'], list) else json.loads(row['evidence_types']),
                xp_reward=row['xp_reward']
            )

    async def list_available_ladders(self, skill_tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all available ladder configurations."""
        async with self.pool.acquire() as conn:
            if skill_tag:
                rows = await conn.fetch("""
                    SELECT DISTINCT skill_tag, goal_type, COUNT(*) as rung_count,
                           MAX(level_index) as max_level,
                           SUM(xp_reward) as total_xp
                    FROM skill_ladders
                    WHERE skill_tag = $1 AND is_active = TRUE
                    GROUP BY skill_tag, goal_type
                    ORDER BY goal_type
                """, skill_tag)
            else:
                rows = await conn.fetch("""
                    SELECT DISTINCT skill_tag, goal_type, COUNT(*) as rung_count,
                           MAX(level_index) as max_level,
                           SUM(xp_reward) as total_xp
                    FROM skill_ladders
                    WHERE is_active = TRUE
                    GROUP BY skill_tag, goal_type
                    ORDER BY skill_tag, goal_type
                """)

            return [dict(row) for row in rows]

    async def instantiate_ladder_for_track(self, skill_tag: str, goal_type: str) -> Dict[str, Any]:
        """
        Instantiate a ladder for a new track - returns mastery vector template
        and initial batch schedule.
        """
        ladder = await self.get_ladder(skill_tag, goal_type)
        if not ladder:
            raise ValueError(f"No ladder found for {skill_tag} / {goal_type}")

        # Build initial mastery vector from ladder sub-skills
        mastery_vector = {}
        for rung in ladder.rungs:
            for sub_skill in rung.sub_skills:
                skill_name = sub_skill['name']
                mastery_vector[skill_name] = {
                    'score': 0,
                    'confidence': 0.0,
                    'level_index': rung.level_index,
                    'level_name': rung.level_name,
                    'evidence_count': 0,
                    'last_updated': None,
                    'can_do_statements': sub_skill.get('can_do_statements', [])
                }

        # Initial batch schedule
        batch_schedule = {
            'current_batch': 0,
            'pace': 'focus',  # micro|focus|sprint
            'session_count': 0,
            'next_batch_at': None,
            'target_sessions_per_week': 3,
            'preferred_days': [1, 3, 5],  # Mon, Wed, Fri
            'session_length_minutes': 20
        }

        return {
            'mastery_vector': mastery_vector,
            'batch_schedule': batch_schedule,
            'ladder': [asdict(rung) for rung in ladder.rungs],
            'total_rungs': len(ladder.rungs)
        }

    # ========================================================================
    # Track CRUD Operations
    # ========================================================================

    async def create_track(
        self,
        user_id: int,
        skill_graph_ref: str,
        skill_tag: str,
        goal_level: str,
        goal_type: str
    ) -> Optional[SkillTrack]:
        """Create a new skill track for a user."""
        # Verify ladder exists
        ladder = await self.get_ladder(skill_tag, goal_type)
        if not ladder:
            raise ValueError(f"No ladder found for {skill_tag} / {goal_type}")

        # Instantiate ladder data
        ladder_data = await self.instantiate_ladder_for_track(skill_tag, goal_type)

        track_id = str(uuid.uuid4())
        now = datetime.utcnow()

        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO skill_tracks (
                    id, user_id, skill_graph_ref, skill_tag, goal_level, goal_type,
                    mastery_vector, batch_schedule, coach_narrative, status,
                    progress_pct, current_ladder_rung, started_at, last_activity_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                track_id, user_id, skill_graph_ref, skill_tag, goal_level, goal_type,
                json.dumps(ladder_data['mastery_vector']),
                json.dumps(ladder_data['batch_schedule']),
                f"Welcome to your {goal_type} track for {skill_tag}! Starting at {goal_level} level.",
                'active',
                0.0,
                0,
                now,
                now
            )

        return await self.get_track(track_id)

    async def get_track(self, track_id: str) -> Optional[SkillTrack]:
        """Get a track by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, user_id, skill_graph_ref, skill_tag, goal_level, goal_type,
                       mastery_vector, batch_schedule, coach_narrative, status,
                       progress_pct, current_ladder_rung, started_at, paused_at,
                       completed_at, last_activity_at
                FROM skill_tracks
                WHERE id = $1
            """, track_id)

            if not row:
                return None

            return self._row_to_track(row)

    async def get_user_tracks(self, user_id: int, status: Optional[str] = None) -> List[SkillTrack]:
        """Get all tracks for a user, optionally filtered by status."""
        async with self.pool.acquire() as conn:
            if status:
                rows = await conn.fetch("""
                    SELECT * FROM skill_tracks
                    WHERE user_id = $1 AND status = $2
                    ORDER BY last_activity_at DESC
                """, user_id, status)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM skill_tracks
                    WHERE user_id = $1 AND status != 'archived'
                    ORDER BY last_activity_at DESC
                """, user_id)

            return [self._row_to_track(row) for row in rows]

    async def update_track(
        self,
        track_id: str,
        mastery_vector: Optional[Dict] = None,
        batch_schedule: Optional[Dict] = None,
        coach_narrative: Optional[str] = None,
        status: Optional[str] = None,
        progress_pct: Optional[float] = None,
        current_ladder_rung: Optional[int] = None
    ) -> Optional[SkillTrack]:
        """Update a track's fields."""
        updates = []
        params = [track_id]
        param_idx = 2

        if mastery_vector is not None:
            updates.append(f"mastery_vector = ${param_idx}")
            params.append(json.dumps(mastery_vector))
            param_idx += 1

        if batch_schedule is not None:
            updates.append(f"batch_schedule = ${param_idx}")
            params.append(json.dumps(batch_schedule))
            param_idx += 1

        if coach_narrative is not None:
            updates.append(f"coach_narrative = ${param_idx}")
            params.append(coach_narrative)
            param_idx += 1

        if status is not None:
            updates.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1
            if status == 'paused':
                updates.append(f"paused_at = ${param_idx}")
                params.append(datetime.utcnow())
                param_idx += 1
            elif status == 'done':
                updates.append(f"completed_at = ${param_idx}")
                params.append(datetime.utcnow())
                param_idx += 1

        if progress_pct is not None:
            updates.append(f"progress_pct = ${param_idx}")
            params.append(progress_pct)
            param_idx += 1

        if current_ladder_rung is not None:
            updates.append(f"current_ladder_rung = ${param_idx}")
            params.append(current_ladder_rung)
            param_idx += 1

        if not updates:
            return await self.get_track(track_id)

        updates.append(f"last_activity_at = ${param_idx}")
        params.append(datetime.utcnow())  # type: ignore[arg-type]
        param_idx += 1

        updates.append("updated_at = NOW()")

        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE skill_tracks SET {', '.join(updates)} WHERE id = $1",
                *params
            )

        return await self.get_track(track_id)

    async def advance_ladder_rung(self, track_id: str, new_rung: int) -> Optional[SkillTrack]:
        """Advance track to a new ladder rung (after verification)."""
        track = await self.get_track(track_id)
        if not track:
            return None

        ladder = await self.get_ladder(track.skill_tag, track.goal_type)
        if not ladder or new_rung >= len(ladder.rungs):
            raise ValueError(f"Invalid rung index {new_rung}")

        # Update progress based on rung completion
        progress_pct = ((new_rung + 1) / len(ladder.rungs)) * 100

        # Generate coach narrative for new rung
        new_rung_data = ladder.rungs[new_rung]
        coach_narrative = (
            f"Congratulations! You've reached {new_rung_data.level_name} in {track.skill_tag}. "
            f"Next up: {new_rung_data.sub_skills[0]['name'] if new_rung_data.sub_skills else 'new challenges'}."
        )

        return await self.update_track(
            track_id,
            current_ladder_rung=new_rung,
            progress_pct=progress_pct,
            coach_narrative=coach_narrative
        )

    async def record_session(
        self,
        track_id: str,
        user_id: int,
        session_type: str,
        duration_seconds: int,
        nodes_completed: int = 0,
        mastery_deltas: Optional[Dict] = None,
        energy_level: Optional[int] = None,
        focus_quality: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a learning session for pacing analytics."""
        session_id = None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO track_sessions (
                    track_id, user_id, session_type, duration_seconds,
                    nodes_completed, mastery_deltas, energy_level, focus_quality, notes
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """,
                track_id, user_id, session_type, duration_seconds,
                nodes_completed, json.dumps(mastery_deltas or {}),
                energy_level, focus_quality, notes
            )
            session_id = row['id']

            # Update track's last_activity_at
            await conn.execute(
                "UPDATE skill_tracks SET last_activity_at = NOW() WHERE id = $1",
                track_id
            )

        return {'session_id': session_id}

    async def get_cross_track_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Get the cross-track dashboard view with all tracks and pacing suggestions."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM user_tracks_dashboard
                WHERE user_id = $1
                ORDER BY last_activity_at DESC
            """, user_id)

            tracks = [dict(row) for row in rows]

            # Get pacing suggestions
            suggestions = await conn.fetch("""
                SELECT * FROM track_pacing_suggestions
                WHERE user_id = $1 AND status = 'pending'
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY confidence DESC
            """, user_id)

            return {
                'tracks': tracks,
                'pacing_suggestions': [dict(s) for s in suggestions],
                'total_active_tracks': len([t for t in tracks if t['status'] == 'active']),
                'total_paused_tracks': len([t for t in tracks if t['status'] == 'paused'])
            }

    async def generate_pacing_suggestions(self, user_id: int) -> List[Dict[str, Any]]:
        """Generate companion-mediated pacing suggestions based on track activity."""
        tracks = await self.get_user_tracks(user_id, status='active')
        if len(tracks) < 2:
            return []  # No pacing needed for single track

        suggestions = []
        now = datetime.utcnow()

        # Check for overwhelm: too many active tracks with low recent activity
        active_count = len(tracks)
        if active_count > 3:
            # Find least active track
            least_active = min(tracks, key=lambda t: t.last_activity_at)
            days_inactive = (now - least_active.last_activity_at).days
            if days_inactive > 7:
                suggestions.append({
                    'suggestion_type': 'pause_track',
                    'target_track_id': least_active.id,
                    'rationale': f"You have {active_count} active tracks and haven't touched '{least_active.skill_tag}' in {days_inactive} days. Consider pausing it to focus on your other tracks.",
                    'confidence': 0.8,
                    'metadata': {'days_inactive': days_inactive, 'active_track_count': active_count}
                })

        # Check for focus week opportunity: one track significantly ahead
        for track in tracks:
            other_tracks = [t for t in tracks if t.id != track.id]
            if not other_tracks:
                continue

            avg_other_progress = sum(t.progress_pct for t in other_tracks) / len(other_tracks)
            if track.progress_pct > avg_other_progress + 30:
                suggestions.append({
                    'suggestion_type': 'focus_week',
                    'target_track_id': track.id,
                    'rationale': f"Your {track.skill_tag} track is {track.progress_pct:.0f}% complete — well ahead of your other tracks (avg {avg_other_progress:.0f}%). A focus week could push it to the next level.",
                    'confidence': 0.7,
                    'metadata': {'track_progress': track.progress_pct, 'avg_other_progress': avg_other_progress}
                })

        # Check for interleaving: tracks with complementary skills
        # (Simplified: if user has both technical and creative tracks)
        skill_tags = [t.skill_tag for t in tracks]
        technical_skills = {'python', 'javascript', 'programming', 'web_development', 'data_science', 'machine_learning'}
        creative_skills = {'guitar', 'music', 'drawing', 'writing', 'photography', 'design'}

        has_technical = any(s in technical_skills for s in skill_tags)
        has_creative = any(s in creative_skills for s in skill_tags)

        if has_technical and has_creative:
            tech_track = next(t for t in tracks if t.skill_tag in technical_skills)
            creative_track = next(t for t in tracks if t.skill_tag in creative_skills)
            suggestions.append({
                'suggestion_type': 'interleave',
                'target_track_id': tech_track.id,
                'related_track_id': creative_track.id,
                'rationale': f"Interleave {tech_track.skill_tag} and {creative_track.skill_tag} sessions — cross-domain analogies (like recursion as guitar patterns) boost retention.",
                'confidence': 0.6,
                'metadata': {'track_a': tech_track.skill_tag, 'track_b': creative_track.skill_tag}
            })

        # Persist suggestions
        async with self.pool.acquire() as conn:
            for sugg in suggestions:
                await conn.execute("""
                    INSERT INTO track_pacing_suggestions (
                        user_id, suggestion_type, target_track_id, related_track_id,
                        rationale, confidence, metadata, expires_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT DO NOTHING
                """,
                    user_id,
                    sugg['suggestion_type'],
                    sugg['target_track_id'],
                    sugg.get('related_track_id'),
                    sugg['rationale'],
                    sugg['confidence'],
                    json.dumps(sugg['metadata']),
                    now + timedelta(days=7)
                )

        return suggestions

    # ========================================================================
    # Verification Checkpoints
    # ========================================================================

    async def create_verification_checkpoint(
        self,
        track_id: str,
        user_id: int,
        level_index: int
    ) -> Dict[str, Any]:
        """Create a verification checkpoint for a ladder rung."""
        track = await self.get_track(track_id)
        if not track:
            raise ValueError("Track not found")

        ladder_rung = await self.get_ladder_rung(track.skill_tag, track.goal_type, level_index)
        if not ladder_rung:
            raise ValueError(f"Ladder rung {level_index} not found")

        async with self.pool.acquire() as conn:
            # Set expiry based on evidence type (longer for performance-based)
            expiry_days = 365 if 'artifact' in ladder_rung.evidence_types else 180
            if 'oral_defense' in ladder_rung.evidence_types or 'transfer_test' in ladder_rung.evidence_types:
                expiry_days = 730  # 2 years for highest level

            expires_at = datetime.utcnow() + timedelta(days=expiry_days)

            await conn.execute("""
                INSERT INTO track_verification_checkpoints (
                    track_id, user_id, ladder_id, level_index, status, expires_at
                ) VALUES ($1, $2,
                    (SELECT id FROM skill_ladders WHERE skill_tag = $3 AND goal_type = $4 AND level_index = $5),
                    $5, 'pending', $6
                )
            """, track_id, user_id, track.skill_tag, track.goal_type, level_index, expires_at)

        return {
            'track_id': track_id,
            'level_index': level_index,
            'level_name': ladder_rung.level_name,
            'evidence_types': ladder_rung.evidence_types,
            'expires_at': expires_at.isoformat(),
            'status': 'pending'
        }

    async def submit_verification_evidence(
        self,
        track_id: str,
        level_index: int,
        evidence: List[Dict[str, Any]],
        rubric_scores: Dict[str, Any],
        verifier: str = 'model'
    ) -> Dict[str, Any]:
        """Submit evidence for a verification checkpoint."""
        async with self.pool.acquire() as conn:
            # Update checkpoint
            overall_score = sum(s.get('score', 0) for s in rubric_scores.values()) / max(1, len(rubric_scores))
            passed = overall_score >= 70  # 70% threshold

            await conn.execute("""
                UPDATE track_verification_checkpoints
                SET status = $1, evidence_refs = $2, rubric_scores = $3,
                    verifier = $4, verified_at = $5, updated_at = NOW()
                WHERE track_id = $6 AND level_index = $7
            """,
                'verified' if passed else 'failed',
                json.dumps(evidence),
                json.dumps(rubric_scores),
                verifier,
                datetime.utcnow() if passed else None,
                track_id,
                level_index
            )

            if passed:
                # Advance track to next rung
                track = await self.advance_ladder_rung(track_id, level_index + 1)

                # Create next checkpoint if not at max
                if track and level_index + 1 < 4:
                    await self.create_verification_checkpoint(track_id, track.user_id, level_index + 1)

                return {
                    'passed': True,
                    'overall_score': overall_score,
                    'next_rung': level_index + 1,
                    'track_progress': track.progress_pct if track else None
                }
            else:
                return {
                    'passed': False,
                    'overall_score': overall_score,
                    'feedback': 'Evidence did not meet the rubric threshold. Review the criteria and try again.'
                }

    def _row_to_track(self, row) -> SkillTrack:
        """Convert database row to SkillTrack object."""
        return SkillTrack(
            id=row['id'],
            user_id=row['user_id'],
            skill_graph_ref=row['skill_graph_ref'],
            skill_tag=row['skill_tag'],
            goal_level=row['goal_level'],
            goal_type=row['goal_type'],
            mastery_vector=row['mastery_vector'] if isinstance(row['mastery_vector'], dict) else json.loads(row['mastery_vector']),
            batch_schedule=row['batch_schedule'] if isinstance(row['batch_schedule'], dict) else json.loads(row['batch_schedule']),
            coach_narrative=row['coach_narrative'],
            status=row['status'],
            progress_pct=row['progress_pct'],
            current_ladder_rung=row['current_ladder_rung'],
            started_at=row['started_at'],
            paused_at=row['paused_at'],
            completed_at=row['completed_at'],
            last_activity_at=row['last_activity_at']
        )


async def create_skill_ladder_service(dsn: str) -> SkillLadderService:
    """Factory function to create service with connection pool."""
    pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    return SkillLadderService(pool)