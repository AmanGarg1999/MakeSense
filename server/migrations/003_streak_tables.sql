-- 003_streak_tables.sql
CREATE TABLE IF NOT EXISTS streak_freezes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    consumed_at TIMESTAMPTZ,
    week_start DATE
);

CREATE TABLE IF NOT EXISTS streak_milestones (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    milestone_days INT,
    earned_at TIMESTAMPTZ DEFAULT NOW(),
    xp_awarded INT
);
