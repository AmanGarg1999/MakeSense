import logging
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

class StreakState(BaseModel):
    current_streak: int
    longest_streak: int
    last_activity_date: Optional[date]
    is_at_risk: bool
    streak_freezes_remaining: int
    next_milestone: int
    milestone_history: List[str]

async def update_streak_for_user(user_id: int, pool) -> dict:
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT current_streak, longest_streak, last_activity_date FROM users WHERE id = $1", user_id)
        if not user:
            return {}
            
        current_streak = user['current_streak'] or 0
        longest_streak = user['longest_streak'] or 0
        last_activity_date = user['last_activity_date']
        
        if last_activity_date == today:
            pass
        elif last_activity_date == yesterday:
            current_streak += 1
        elif last_activity_date is not None and last_activity_date < yesterday:
            week_start = today - timedelta(days=today.weekday())
            freeze_consumed = await conn.fetchval("""
                SELECT 1 FROM streak_freezes 
                WHERE user_id = $1 AND week_start = $2 AND consumed_at IS NOT NULL
            """, user_id, week_start)
            
            if not freeze_consumed:
                await conn.execute("""
                    INSERT INTO streak_freezes (user_id, consumed_at, week_start)
                    VALUES ($1, NOW(), $2)
                """, user_id, week_start)
                # Keep streak unchanged
            else:
                current_streak = 1
        else:
            current_streak = 1
            
        if current_streak > longest_streak:
            longest_streak = current_streak
            
        await conn.execute("""
            UPDATE users SET current_streak = $1, longest_streak = $2, last_activity_date = $3
            WHERE id = $4
        """, current_streak, longest_streak, today, user_id)
        
        milestones = [7, 14, 30, 60, 100, 365]
        milestone_awarded = None
        if current_streak in milestones:
            already_awarded = await conn.fetchval("""
                SELECT 1 FROM streak_milestones WHERE user_id = $1 AND milestone_days = $2
            """, user_id, current_streak)
            
            if not already_awarded:
                xp_awarded = 50
                await conn.execute("""
                    INSERT INTO streak_milestones (user_id, milestone_days, xp_awarded)
                    VALUES ($1, $2, $3)
                """, user_id, current_streak, xp_awarded)
                
                await conn.execute("""
                    SELECT award_engagement_points($1, $2, 'streak_bonus', NULL, NULL, $3)
                """, user_id, xp_awarded, f"{current_streak} day streak milestone!")
                milestone_awarded = current_streak
                
        # To return the full state, calculate the other fields
        is_at_risk = False
        week_start = today - timedelta(days=today.weekday())
        used_freeze = await conn.fetchval("""
            SELECT 1 FROM streak_freezes WHERE user_id = $1 AND week_start = $2 AND consumed_at IS NOT NULL
        """, user_id, week_start)
        streak_freezes_remaining = 0 if used_freeze else 1
        
        next_milestone = next((m for m in milestones if m > current_streak), 365)
        
        history = await conn.fetch("SELECT milestone_days FROM streak_milestones WHERE user_id = $1 ORDER BY milestone_days ASC", user_id)
        milestone_history = [str(r['milestone_days']) for r in history]

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "last_activity_date": today.isoformat(),
            "is_at_risk": is_at_risk,
            "streak_freezes_remaining": streak_freezes_remaining,
            "next_milestone": next_milestone,
            "milestone_history": milestone_history,
            "milestone_awarded": milestone_awarded
        }

@router.post("/streaks/{user_id}/check-in")
async def check_in(user_id: int, request: Request):
    pool = request.app.state.db_pool
    res = await update_streak_for_user(user_id, pool)
    if not res:
        raise HTTPException(404, "User not found")
    # For compatibility, ensure we return something that looks like StreakState but dictionary is fine
    return res

@router.get("/streaks/{user_id}", response_model=StreakState)
async def get_streak(user_id: int, request: Request):
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT current_streak, longest_streak, last_activity_date FROM users WHERE id = $1", user_id)
        if not user:
            raise HTTPException(404, "User not found")
            
        today = date.today()
        yesterday = today - timedelta(days=1)
        last_activity_date = user['last_activity_date']
        
        is_at_risk = False
        if last_activity_date == yesterday:
            is_at_risk = True
            
        week_start = today - timedelta(days=today.weekday())
        
        used_freeze = await conn.fetchval("""
            SELECT 1 FROM streak_freezes WHERE user_id = $1 AND week_start = $2 AND consumed_at IS NOT NULL
        """, user_id, week_start)
        
        streak_freezes_remaining = 0 if used_freeze else 1
        
        milestones = [7, 14, 30, 60, 100, 365]
        current_streak = user['current_streak'] or 0
        next_milestone = next((m for m in milestones if m > current_streak), 365)
        
        history = await conn.fetch("SELECT milestone_days FROM streak_milestones WHERE user_id = $1 ORDER BY milestone_days ASC", user_id)
        milestone_history = [str(r['milestone_days']) for r in history]
        
        return StreakState(
            current_streak=current_streak,
            longest_streak=user['longest_streak'] or 0,
            last_activity_date=last_activity_date,
            is_at_risk=is_at_risk,
            streak_freezes_remaining=streak_freezes_remaining,
            next_milestone=next_milestone,
            milestone_history=milestone_history
        )
