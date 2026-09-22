import json
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()

def evaluate_condition(actual, operator, expected):
    if operator == '>=':
        return actual >= expected
    elif operator == '<=':
        return actual <= expected
    elif operator == '==':
        return actual == expected
    elif operator == '>':
        return actual > expected
    elif operator == '<':
        return actual < expected
    elif operator == 'in':
        return actual in expected if isinstance(expected, list) else actual == expected
    return False

async def evaluate_user_achievements(user_id: int, pool) -> List[dict]:
    new_achievements = []
    async with pool.acquire() as conn:
        achievements = await conn.fetch("""
            SELECT * FROM achievements 
            WHERE is_active = true 
            AND id NOT IN (SELECT achievement_id FROM user_achievements WHERE user_id = $1)
        """, user_id)
        
        user_data = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if not user_data:
            return []
            
        for ach in achievements:
            criteria = ach['criteria_json']
            if isinstance(criteria, str):
                criteria = json.loads(criteria)
                
            metric = criteria.get('metric')
            operator = criteria.get('operator')
            value = criteria.get('value')
            
            earned = False
            
            if metric == 'total_xp':
                earned = evaluate_condition(user_data['total_xp'] or 0, operator, value)
            elif metric == 'current_streak':
                earned = evaluate_condition(user_data['current_streak'] or 0, operator, value)
            elif metric == 'lessons_completed':
                count = await conn.fetchval("SELECT COUNT(*) FROM quiz_attempts WHERE user_id = $1", user_id)
                earned = evaluate_condition(count, operator, value)
            elif metric == 'perfect_scores':
                count = await conn.fetchval("SELECT COUNT(*) FROM quiz_attempts WHERE user_id = $1 AND score = 100", user_id)
                earned = evaluate_condition(count, operator, value)
            elif metric == 'unique_categories':
                count = await conn.fetchval("""
                    SELECT COUNT(DISTINCT cat) 
                    FROM quiz_attempts qa
                    JOIN lessons l ON qa.lesson_id = l.id
                    JOIN topics t ON l.topic_id = t.id,
                    unnest(t.categories) as cat
                    WHERE qa.user_id = $1
                """, user_id)
                earned = evaluate_condition(count, operator, value)
            elif metric == 'quiz_time':
                if value == 'night':
                    # completed_at time between 00:00 and 05:00
                    count = await conn.fetchval("""
                        SELECT COUNT(*) FROM quiz_attempts 
                        WHERE user_id = $1 
                        AND EXTRACT(HOUR FROM completed_at) >= 0 
                        AND EXTRACT(HOUR FROM completed_at) < 5
                    """, user_id)
                    earned = count > 0
            
            if earned:
                # INSERT into user_achievements
                await conn.execute("""
                    INSERT INTO user_achievements (user_id, achievement_id, earned_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT DO NOTHING
                """, user_id, ach['id'])
                
                # Award XP
                await conn.execute("""
                    SELECT award_engagement_points($1, $2, 'achievement', $3::text, NULL, $4)
                """, user_id, ach['xp_reward'], str(ach['id']), f"Earned achievement: {ach['name']}")
                
                new_achievements.append({
                    "id": ach['id'],
                    "code": ach['code'],
                    "name": ach['name'],
                    "description": ach['description'],
                    "icon": ach['icon'],
                    "xp_reward": ach['xp_reward']
                })
                
        return new_achievements

@router.post("/achievements/{user_id}/evaluate")
async def evaluate(user_id: int, request: Request):
    pool = request.app.state.db_pool
    earned = await evaluate_user_achievements(user_id, pool)
    return {"newly_earned": earned}

@router.get("/achievements/{user_id}")
async def get_achievements(user_id: int, request: Request):
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        achievements = await conn.fetch("""
            SELECT a.*, ua.earned_at 
            FROM achievements a
            LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = $1
            WHERE a.is_active = true
            ORDER BY a.category, a.id
        """, user_id)
        
        result = []
        for row in achievements:
            earned = row['earned_at'] is not None
            if row['is_hidden'] and not earned:
                continue
                
            result.append({
                "id": row['id'],
                "code": row['code'],
                "name": row['name'],
                "description": row['description'],
                "icon": row['icon'],
                "category": row['category'],
                "xp_reward": row['xp_reward'],
                "is_earned": earned,
                "earned_at": row['earned_at'].isoformat() if row['earned_at'] else None
            })
            
        return result
