-- Gamification System Schema Migration
-- Version: 1.0
-- Created: 2026-09-19
-- Description: Core tables for user levels, engagement points, skill ratings, and interaction events

-- ============================================================================
-- 1. UserLevel Table - XP thresholds per level
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_levels (
    level_id          SMALLINT        NOT NULL,
    level_name        VARCHAR(50)     NOT NULL,
    xp_threshold      BIGINT          NOT NULL,
    xp_to_next        BIGINT          NOT NULL,
    badge_icon        VARCHAR(100),   -- emoji or icon identifier
    badge_color       VARCHAR(7),     -- hex color code
    description       TEXT,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_user_levels PRIMARY KEY (level_id),
    CONSTRAINT uq_user_levels_name UNIQUE (level_name),
    CONSTRAINT ck_user_levels_xp_threshold CHECK (xp_threshold >= 0),
    CONSTRAINT ck_user_levels_xp_to_next CHECK (xp_to_next > 0),
    CONSTRAINT ck_user_levels_badge_color CHECK (badge_color ~ '^#[0-9A-Fa-f]{6}$')
);

-- Index for fast level lookups by XP
CREATE INDEX IF NOT EXISTS idx_user_levels_xp_threshold ON user_levels (xp_threshold);

-- Insert default level configuration (can be customized via seeds)
INSERT INTO user_levels (level_id, level_name, xp_threshold, xp_to_next, badge_icon, badge_color, description) VALUES
    (1, 'Novice',       0,       100,  '🌱', '#8FBC8F', 'Just starting your learning journey'),
    (2, 'Explorer',     100,     250,  '🧭', '#4682B4', 'Discovering new topics'),
    (3, 'Learner',      350,     500,  '📚', '#5F9EA0', 'Building foundational knowledge'),
    (4, 'Practitioner', 850,     1000, '⚡', '#DAA520', 'Applying knowledge actively'),
    (5, 'Scholar',      1850,    2000, '🎓', '#B8860B', 'Deep understanding across domains'),
    (6, 'Expert',       3850,    3000, '💎', '#9370DB', 'Mastery in specialized areas'),
    (7, 'Master',       6850,    5000, '🏆', '#FFD700', 'Recognized authority'),
    (8, 'Grandmaster',  11850,   10000,'👑', '#FF6B6B', 'Legendary contributor')
ON CONFLICT (level_id) DO NOTHING;

-- ============================================================================
-- 2. User Table Extension - Gamification fields
-- ============================================================================
-- Assuming a base users table exists; add gamification columns
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        -- Add columns if they don't exist
        ALTER TABLE users ADD COLUMN IF NOT EXISTS current_level SMALLINT NOT NULL DEFAULT 1;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS total_xp BIGINT NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS current_streak SMALLINT NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS longest_streak SMALLINT NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity_date DATE;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS total_engagement_points BIGINT NOT NULL DEFAULT 0;

        -- Foreign key to user_levels
        ALTER TABLE users ADD CONSTRAINT fk_users_current_level
            FOREIGN KEY (current_level) REFERENCES user_levels(level_id)
            ON UPDATE CASCADE ON DELETE RESTRICT;
    END IF;
END $$;

-- ============================================================================
-- 3. EngagementPoints Ledger - Points with source tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS engagement_points (
    id                BIGSERIAL       NOT NULL,
    user_id           BIGINT          NOT NULL,
    points            INTEGER         NOT NULL,
    source_type       VARCHAR(50)     NOT NULL,
    source_id         BIGINT,         -- reference to course_id, question_id, etc.
    source_metadata   JSONB,          -- flexible context: {course_title, question_tags, etc.}
    description       TEXT,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_engagement_points PRIMARY KEY (id),
    CONSTRAINT ck_engagement_points_points CHECK (points != 0),
    CONSTRAINT ck_engagement_points_source_type CHECK (source_type IN (
        'course_completion',
        'lesson_completion',
        'question_answer_correct',
        'question_answer_incorrect',
        'streak_bonus',
        'daily_login',
        'peer_help',
        'content_contribution',
        'review_completion',
        'achievement_unlock',
        'referral_bonus',
        'manual_adjustment'
    ))
);

-- Indexes for leaderboard and analytics queries
CREATE INDEX IF NOT EXISTS idx_engagement_points_user_created ON engagement_points (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_engagement_points_source_type ON engagement_points (source_type);
CREATE INDEX IF NOT EXISTS idx_engagement_points_user_source ON engagement_points (user_id, source_type);
CREATE INDEX IF NOT EXISTS idx_engagement_points_created_at ON engagement_points (created_at DESC);

-- Partial index for positive points only (leaderboards)
CREATE INDEX IF NOT EXISTS idx_engagement_points_positive ON engagement_points (user_id, created_at DESC)
    WHERE points > 0;

-- ============================================================================
-- 4. UserSkillRating Table - Skill proficiency per user
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_skill_ratings (
    id                BIGSERIAL       NOT NULL,
    user_id           BIGINT          NOT NULL,
    skill_tag         VARCHAR(100)    NOT NULL,
    proficiency_score SMALLINT        NOT NULL,  -- 0-100
    evidence_count    INTEGER         NOT NULL DEFAULT 0,
    confidence        REAL            NOT NULL DEFAULT 0.0,  -- 0.0-1.0 Bayesian confidence
    last_updated      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_user_skill_ratings PRIMARY KEY (id),
    CONSTRAINT uq_user_skill_ratings UNIQUE (user_id, skill_tag),
    CONSTRAINT ck_user_skill_ratings_score CHECK (proficiency_score BETWEEN 0 AND 100),
    CONSTRAINT ck_user_skill_ratings_evidence CHECK (evidence_count >= 0),
    CONSTRAINT ck_user_skill_ratings_confidence CHECK (confidence BETWEEN 0.0 AND 1.0)
);

-- Indexes for skill queries
CREATE INDEX IF NOT EXISTS idx_user_skill_ratings_user ON user_skill_ratings (user_id);
CREATE INDEX IF NOT EXISTS idx_user_skill_ratings_tag ON user_skill_ratings (skill_tag);
CREATE INDEX IF NOT EXISTS idx_user_skill_ratings_score ON user_skill_ratings (user_id, proficiency_score DESC);
CREATE INDEX IF NOT EXISTS idx_user_skill_ratings_updated ON user_skill_ratings (last_updated DESC);

-- ============================================================================
-- 5. UserInteractionEvent Table - Raw event logging
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_interaction_events (
    id                BIGSERIAL       NOT NULL,
    user_id           BIGINT          NOT NULL,
    session_id        UUID            NOT NULL DEFAULT gen_random_uuid(),
    event_type        VARCHAR(50)     NOT NULL,
    event_category    VARCHAR(30)     NOT NULL,  -- 'learning', 'social', 'navigation', 'system'
    metadata          JSONB           NOT NULL DEFAULT '{}',
    duration_ms       INTEGER,        -- optional: time spent on action
    page_url          TEXT,           -- current page/context
    referrer_url      TEXT,
    user_agent        TEXT,
    ip_hash           VARCHAR(64),    -- hashed for privacy
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_user_interaction_events PRIMARY KEY (id),
    CONSTRAINT ck_user_interaction_events_category CHECK (event_category IN (
        'learning',
        'social',
        'navigation',
        'system',
        'assessment'
    )),
    CONSTRAINT ck_user_interaction_events_duration CHECK (duration_ms IS NULL OR duration_ms >= 0)
);

-- Partition by month for performance (PostgreSQL 11+)
-- Note: Requires manual partition creation or pg_partman
-- Example partition for 2026-09:
-- CREATE TABLE user_interaction_events_2026_09 PARTITION OF user_interaction_events
--     FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');

-- Indexes for analytics and debugging
CREATE INDEX IF NOT EXISTS idx_user_interaction_events_user_time ON user_interaction_events (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_interaction_events_type ON user_interaction_events (event_type);
CREATE INDEX IF NOT EXISTS idx_user_interaction_events_category ON user_interaction_events (event_category);
CREATE INDEX IF NOT EXISTS idx_user_interaction_events_session ON user_interaction_events (session_id);
CREATE INDEX IF NOT EXISTS idx_user_interaction_events_created ON user_interaction_events (created_at DESC);

-- GIN index for JSONB metadata queries
CREATE INDEX IF NOT EXISTS idx_user_interaction_events_metadata ON user_interaction_events USING GIN (metadata);

-- ============================================================================
-- 6. Skill Taxonomy Table - Canonical skill definitions
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_taxonomy (
    id                BIGSERIAL       NOT NULL,
    skill_tag         VARCHAR(100)    NOT NULL,
    display_name      VARCHAR(100)    NOT NULL,
    description       TEXT,
    category          VARCHAR(50),    -- e.g., 'mathematics', 'programming', 'language'
    parent_tag        VARCHAR(100),   -- for hierarchical skills
    difficulty        SMALLINT        NOT NULL DEFAULT 1,  -- 1-5
    is_active         BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_skill_taxonomy PRIMARY KEY (id),
    CONSTRAINT uq_skill_taxonomy_tag UNIQUE (skill_tag),
    CONSTRAINT ck_skill_taxonomy_difficulty CHECK (difficulty BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS idx_skill_taxonomy_category ON skill_taxonomy (category);
CREATE INDEX IF NOT EXISTS idx_skill_taxonomy_parent ON skill_taxonomy (parent_tag);
CREATE INDEX IF NOT EXISTS idx_skill_taxonomy_active ON skill_taxonomy (is_active) WHERE is_active;

-- Self-referential foreign key for hierarchy
ALTER TABLE skill_taxonomy ADD CONSTRAINT fk_skill_taxonomy_parent
    FOREIGN KEY (parent_tag) REFERENCES skill_taxonomy(skill_tag)
    ON UPDATE CASCADE ON DELETE SET NULL;

-- ============================================================================
-- 7. Achievement/Badge Table - Gamification milestones
-- ============================================================================
CREATE TABLE IF NOT EXISTS achievements (
    id                BIGSERIAL       NOT NULL,
    code              VARCHAR(50)     NOT NULL,
    name              VARCHAR(100)    NOT NULL,
    description       TEXT,
    icon              VARCHAR(100),   -- emoji or icon identifier
    category          VARCHAR(30),    -- 'progress', 'social', 'mastery', 'streak', 'special'
    criteria_json     JSONB           NOT NULL,  -- {metric: 'total_xp', operator: '>=', value: 1000}
    xp_reward         INTEGER         NOT NULL DEFAULT 0,
    is_hidden         BOOLEAN         NOT NULL DEFAULT FALSE,
    is_active         BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_achievements PRIMARY KEY (id),
    CONSTRAINT uq_achievements_code UNIQUE (code),
    CONSTRAINT ck_achievements_xp_reward CHECK (xp_reward >= 0)
);

CREATE INDEX IF NOT EXISTS idx_achievements_category ON achievements (category);
CREATE INDEX IF NOT EXISTS idx_achievements_active ON achievements (is_active) WHERE is_active;

-- ============================================================================
-- 8. UserAchievement Table - Earned achievements
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_achievements (
    id                BIGSERIAL       NOT NULL,
    user_id           BIGINT          NOT NULL,
    achievement_id    BIGINT          NOT NULL,
    earned_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    metadata          JSONB           DEFAULT '{}',  -- context at time of earning

    CONSTRAINT pk_user_achievements PRIMARY KEY (id),
    CONSTRAINT uq_user_achievements UNIQUE (user_id, achievement_id),
    CONSTRAINT fk_user_achievements_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_achievements_achievement FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements (user_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_earned ON user_achievements (earned_at DESC);

-- ============================================================================
-- 9. Helper Views for Common Queries
-- ============================================================================

-- View: User gamification summary
CREATE OR REPLACE VIEW user_gamification_summary AS
SELECT
    u.id AS user_id,
    u.current_level,
    ul.level_name,
    u.total_xp,
    ul.xp_threshold AS level_xp_start,
    (ul.xp_threshold + ul.xp_to_next) AS level_xp_end,
    u.total_engagement_points,
    u.current_streak,
    u.longest_streak,
    u.last_activity_date,
    COALESCE(skill_stats.skill_count, 0) AS skills_tracked,
    COALESCE(skill_stats.top_skill_tag, '') AS top_skill_tag,
    COALESCE(skill_stats.top_skill_score, 0) AS top_skill_score,
    COALESCE(achievement_stats.achievements_earned, 0) AS achievements_earned
FROM users u
JOIN user_levels ul ON u.current_level = ul.level_id
LEFT JOIN LATERAL (
    SELECT
        COUNT(*) AS skill_count,
        (SELECT usr.skill_tag FROM user_skill_ratings usr WHERE usr.user_id = u.id ORDER BY usr.proficiency_score DESC LIMIT 1) AS top_skill_tag,
        MAX(proficiency_score) AS top_skill_score
    FROM user_skill_ratings
    WHERE user_id = u.id
) skill_stats ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS achievements_earned
    FROM user_achievements
    WHERE user_id = u.id
) achievement_stats ON TRUE;

-- View: Leaderboard (top users by XP)
CREATE OR REPLACE VIEW leaderboard_xp AS
SELECT
    u.id AS user_id,
    u.current_level,
    ul.level_name,
    u.total_xp,
    u.total_engagement_points,
    u.current_streak,
    ROW_NUMBER() OVER (ORDER BY u.total_xp DESC) AS rank
FROM users u
JOIN user_levels ul ON u.current_level = ul.level_id
WHERE u.total_xp > 0
ORDER BY u.total_xp DESC;

-- View: Skill leaderboard (top users per skill)
CREATE OR REPLACE VIEW leaderboard_skill AS
SELECT
    usr.skill_tag,
    usr.user_id,
    usr.proficiency_score,
    usr.evidence_count,
    ROW_NUMBER() OVER (PARTITION BY usr.skill_tag ORDER BY usr.proficiency_score DESC, usr.evidence_count DESC) AS rank
FROM user_skill_ratings usr
WHERE usr.proficiency_score > 0 AND usr.evidence_count >= 3
ORDER BY usr.skill_tag, usr.proficiency_score DESC;

-- ============================================================================
-- 10. Functions for Gamification Logic
-- ============================================================================

-- Function: Calculate user level from XP
CREATE OR REPLACE FUNCTION calculate_user_level(p_total_xp BIGINT)
RETURNS SMALLINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_level SMALLINT;
BEGIN
    SELECT level_id INTO v_level
    FROM user_levels
    WHERE xp_threshold <= p_total_xp
    ORDER BY xp_threshold DESC
    LIMIT 1;

    RETURN COALESCE(v_level, 1);
END;
$$;

-- Function: Award engagement points (atomic)
CREATE OR REPLACE FUNCTION award_engagement_points(
    p_user_id BIGINT,
    p_points INTEGER,
    p_source_type VARCHAR,
    p_source_id BIGINT DEFAULT NULL,
    p_source_metadata JSONB DEFAULT '{}',
    p_description TEXT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_new_xp BIGINT;
    v_new_level SMALLINT;
    v_point_id BIGINT;
BEGIN
    -- Insert point record
    INSERT INTO engagement_points (user_id, points, source_type, source_id, source_metadata, description)
    VALUES (p_user_id, p_points, p_source_type, p_source_id, p_source_metadata, p_description)
    RETURNING id INTO v_point_id;

    -- Update user totals atomically
    UPDATE users
    SET
        total_xp = total_xp + p_points,
        total_engagement_points = total_engagement_points + p_points,
        current_level = calculate_user_level(total_xp + p_points),
        last_activity_date = CURRENT_DATE
    WHERE id = p_user_id
    RETURNING total_xp, current_level INTO v_new_xp, v_new_level;

    -- Check for level up and award bonus
    IF v_new_level > (SELECT current_level FROM users WHERE id = p_user_id) THEN
        -- Level up bonus: 10% of XP to next level
        INSERT INTO engagement_points (user_id, points, source_type, source_metadata, description)
        VALUES (p_user_id, (SELECT xp_to_next FROM user_levels WHERE level_id = v_new_level) / 10,
                'achievement_unlock',
                jsonb_build_object('level_reached', v_new_level),
                'Level up bonus: reached ' || (SELECT level_name FROM user_levels WHERE level_id = v_new_level));
    END IF;

    RETURN v_point_id;
END;
$$;

-- Function: Update skill rating (Bayesian average)
CREATE OR REPLACE FUNCTION update_skill_rating(
    p_user_id BIGINT,
    p_skill_tag VARCHAR,
    p_new_evidence_score SMALLINT,  -- 0-100 score for this evidence
    p_evidence_weight REAL DEFAULT 1.0  -- weight of this evidence (e.g., question difficulty)
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_prior_weight CONSTANT REAL := 10.0;  -- equivalent to 10 "average" evidences
    v_global_avg CONSTANT REAL := 50.0;    -- global average proficiency
    v_current_score REAL;
    v_current_count INTEGER;
    v_new_score REAL;
    v_new_count INTEGER;
    v_new_confidence REAL;
BEGIN
    -- Get current rating
    SELECT proficiency_score, evidence_count
    INTO v_current_score, v_current_count
    FROM user_skill_ratings
    WHERE user_id = p_user_id AND skill_tag = p_skill_tag;

    IF v_current_score IS NULL THEN
        -- First evidence for this skill
        v_new_score := p_new_evidence_score;
        v_new_count := 1;
        v_new_confidence := 1.0 / (1.0 + v_prior_weight);
    ELSE
        -- Bayesian update
        v_new_count := v_current_count + 1;
        v_new_score := (v_prior_weight * v_global_avg + v_current_score * v_current_count + p_new_evidence_score * p_evidence_weight)
                       / (v_prior_weight + v_current_count + p_evidence_weight);
        v_new_confidence := (v_current_count + p_evidence_weight) / (v_prior_weight + v_current_count + p_evidence_weight);
    END IF;

    -- Upsert
    INSERT INTO user_skill_ratings (user_id, skill_tag, proficiency_score, evidence_count, confidence, last_updated)
    VALUES (p_user_id, p_skill_tag, ROUND(v_new_score)::SMALLINT, v_new_count, v_new_confidence, NOW())
    ON CONFLICT (user_id, skill_tag) DO UPDATE SET
        proficiency_score = ROUND(v_new_score)::SMALLINT,
        evidence_count = v_new_count,
        confidence = v_new_confidence,
        last_updated = NOW();
END;
$$;

-- Function: Record interaction event
CREATE OR REPLACE FUNCTION record_interaction_event(
    p_user_id BIGINT,
    p_event_type VARCHAR,
    p_event_category VARCHAR,
    p_metadata JSONB DEFAULT '{}',
    p_duration_ms INTEGER DEFAULT NULL,
    p_page_url TEXT DEFAULT NULL,
    p_referrer_url TEXT DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_event_id BIGINT;
    v_ip_hash VARCHAR(64);
BEGIN
    -- Hash IP for privacy (placeholder - actual IP would come from request context)
    v_ip_hash := md5(random()::text || clock_timestamp()::text);

    INSERT INTO user_interaction_events (user_id, event_type, event_category, metadata, duration_ms, page_url, referrer_url, user_agent, ip_hash)
    VALUES (p_user_id, p_event_type, p_event_category, p_metadata, p_duration_ms, p_page_url, p_referrer_url, p_user_agent, v_ip_hash)
    RETURNING id INTO v_event_id;

    RETURN v_event_id;
END;
$$;

-- ============================================================================
-- 11. Triggers for Automatic Updates
-- ============================================================================

-- Trigger: Update user last_activity_date on interaction
CREATE OR REPLACE FUNCTION update_user_last_activity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE users
    SET last_activity_date = CURRENT_DATE
    WHERE id = NEW.user_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_update_last_activity ON user_interaction_events;
CREATE TRIGGER trg_update_last_activity
    AFTER INSERT ON user_interaction_events
    FOR EACH ROW EXECUTE FUNCTION update_user_last_activity();

-- Trigger: Auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_user_levels_updated ON user_levels;
CREATE TRIGGER trg_user_levels_updated
    BEFORE UPDATE ON user_levels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_skill_taxonomy_updated ON skill_taxonomy;
CREATE TRIGGER trg_skill_taxonomy_updated
    BEFORE UPDATE ON skill_taxonomy
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_achievements_updated ON achievements;
CREATE TRIGGER trg_achievements_updated
    BEFORE UPDATE ON achievements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 12. Row Level Security (Optional - Enable if using RLS)
-- ============================================================================
-- ALTER TABLE engagement_points ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_skill_ratings ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_interaction_events ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_achievements ENABLE ROW LEVEL SECURITY;
--
-- CREATE POLICY engagement_points_user_policy ON engagement_points
--     USING (user_id = current_setting('app.current_user_id')::BIGINT);
-- CREATE POLICY user_skill_ratings_user_policy ON user_skill_ratings
--     USING (user_id = current_setting('app.current_user_id')::BIGINT);
-- CREATE POLICY user_interaction_events_user_policy ON user_interaction_events
--     USING (user_id = current_setting('app.current_user_id')::BIGINT);
-- CREATE POLICY user_achievements_user_policy ON user_achievements
--     USING (user_id = current_setting('app.current_user_id')::BIGINT);

-- ============================================================================
-- Migration Complete
-- ============================================================================
-- Run verification:
-- SELECT * FROM user_levels ORDER BY level_id;
-- SELECT * FROM skill_taxonomy WHERE is_active ORDER BY category, skill_tag;
-- SELECT * FROM achievements WHERE is_active ORDER BY category, xp_reward;