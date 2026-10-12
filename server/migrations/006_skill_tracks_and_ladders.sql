-- Multi-Track State + Goal-Relative Skill Ladders Migration
-- Version: 1.0
-- Created: 2026-10-09
-- Description: Core tables for multi-skill-track state management and goal-relative skill ladders

-- ============================================================================
-- 1. Skill Track Table - User's concurrent learning tracks
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_tracks (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    user_id         BIGINT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_graph_ref VARCHAR(100)    NOT NULL,        -- reference to competency KG topic
    skill_tag       VARCHAR(100)    NOT NULL,        -- canonical skill tag from taxonomy
    goal_level      VARCHAR(20)     NOT NULL DEFAULT 'competent',  -- novice|competent|proficient|expert
    goal_type       VARCHAR(20)     NOT NULL DEFAULT 'hobby',      -- hobby|job-ready|expert
    mastery_vector  JSONB           NOT NULL DEFAULT '{}',         -- {sub_skill: {score, confidence, last_updated}}
    batch_schedule  JSONB           NOT NULL DEFAULT '{}',         -- {current_batch, next_batch_at, pace, session_count}
    coach_narrative TEXT,                                       -- companion's running narrative for this track
    status          VARCHAR(20)     NOT NULL DEFAULT 'active'      -- active|paused|done|archived
        CHECK (status IN ('active', 'paused', 'done', 'archived')),
    progress_pct    REAL            NOT NULL DEFAULT 0.0,          -- 0-100 aggregate progress
    current_ladder_rung INTEGER     NOT NULL DEFAULT 0,            -- current level index (0-based)
    started_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    paused_at       TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_skill_tracks PRIMARY KEY (id),
    CONSTRAINT uq_skill_tracks_user_skill UNIQUE (user_id, skill_tag, goal_type)
);

-- Indexes for skill_tracks
CREATE INDEX IF NOT EXISTS idx_skill_tracks_user ON skill_tracks (user_id);
CREATE INDEX IF NOT EXISTS idx_skill_tracks_status ON skill_tracks (user_id, status);
CREATE INDEX IF NOT EXISTS idx_skill_tracks_activity ON skill_tracks (last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_tracks_skill_tag ON skill_tracks (skill_tag);

-- ============================================================================
-- 2. Skill Ladder Table - Goal-relative ladder definitions
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_ladders (
    id              BIGSERIAL       NOT NULL,
    skill_tag       VARCHAR(100)    NOT NULL,        -- canonical skill from taxonomy
    goal_type       VARCHAR(20)     NOT NULL,        -- hobby|job-ready|expert
    level_index     SMALLINT        NOT NULL,        -- 0=novice, 1=competent, 2=proficient, 3=expert
    level_name      VARCHAR(50)     NOT NULL,        -- e.g., "Novice", "Competent", "Proficient", "Expert"
    sub_skills      JSONB           NOT NULL,        -- [{name, description, prerequisites[], can_do_statements[]}]
    prerequisites   JSONB           NOT NULL DEFAULT '[]',  -- array of skill_tags required before this level
    evidence_types  JSONB           NOT NULL DEFAULT '[]',  -- ['quiz', 'project', 'artifact', 'oral_defense', 'transfer_test']
    xp_reward       INTEGER         NOT NULL DEFAULT 0,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_skill_ladders PRIMARY KEY (id),
    CONSTRAINT uq_skill_ladders_unique UNIQUE (skill_tag, goal_type, level_index),
    CONSTRAINT ck_skill_ladders_level CHECK (level_index BETWEEN 0 AND 3),
    CONSTRAINT ck_skill_ladders_goal CHECK (goal_type IN ('hobby', 'job-ready', 'expert'))
);

-- Indexes for skill_ladders
CREATE INDEX IF NOT EXISTS idx_skill_ladders_skill_goal ON skill_ladders (skill_tag, goal_type);
CREATE INDEX IF NOT EXISTS idx_skill_ladders_active ON skill_ladders (is_active) WHERE is_active;

-- ============================================================================
-- 3. Track Session Log - Session-level activity for pacing suggestions
-- ============================================================================
CREATE TABLE IF NOT EXISTS track_sessions (
    id              BIGSERIAL       NOT NULL,
    track_id        UUID            NOT NULL REFERENCES skill_tracks(id) ON DELETE CASCADE,
    user_id         BIGINT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_type    VARCHAR(30)     NOT NULL,  -- 'learning', 'practice', 'verification', 'recap', 'diagnostic'
    duration_seconds INTEGER        NOT NULL DEFAULT 0,
    nodes_completed INTEGER         NOT NULL DEFAULT 0,
    mastery_deltas  JSONB           NOT NULL DEFAULT '{}',  -- {sub_skill: delta}
    energy_level    SMALLINT,                        -- 1-5 self-reported energy
    focus_quality   SMALLINT,                        -- 1-5 self-reported focus
    notes           TEXT,
    started_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,

    CONSTRAINT pk_track_sessions PRIMARY KEY (id),
    CONSTRAINT ck_track_sessions_duration CHECK (duration_seconds >= 0),
    CONSTRAINT ck_track_sessions_energy CHECK (energy_level IS NULL OR (energy_level BETWEEN 1 AND 5)),
    CONSTRAINT ck_track_sessions_focus CHECK (focus_quality IS NULL OR (focus_quality BETWEEN 1 AND 5))
);

CREATE INDEX IF NOT EXISTS idx_track_sessions_track ON track_sessions (track_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_track_sessions_user ON track_sessions (user_id, started_at DESC);

-- ============================================================================
-- 4. Cross-Track Pacing Suggestions - Companion-mediated suggestions
-- ============================================================================
CREATE TABLE IF NOT EXISTS track_pacing_suggestions (
    id              BIGSERIAL       NOT NULL,
    user_id         BIGINT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    suggestion_type VARCHAR(30)     NOT NULL,  -- 'focus_week', 'interleave', 'pause_track', 'reduce_pace', 'increase_pace'
    target_track_id UUID            REFERENCES skill_tracks(id) ON DELETE SET NULL,
    related_track_id UUID           REFERENCES skill_tracks(id) ON DELETE SET NULL,
    rationale       TEXT            NOT NULL,
    confidence      REAL            NOT NULL DEFAULT 0.5,  -- 0.0-1.0
    status          VARCHAR(20)     NOT NULL DEFAULT 'pending',  -- pending|accepted|dismissed|expired
    metadata        JSONB           NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,

    CONSTRAINT pk_track_pacing_suggestions PRIMARY KEY (id),
    CONSTRAINT ck_track_pacing_confidence CHECK (confidence BETWEEN 0.0 AND 1.0),
    CONSTRAINT ck_track_pacing_status CHECK (status IN ('pending', 'accepted', 'dismissed', 'expired'))
);

CREATE INDEX IF NOT EXISTS idx_track_pacing_user ON track_pacing_suggestions (user_id, status);
CREATE INDEX IF NOT EXISTS idx_track_pacing_target ON track_pacing_suggestions (target_track_id);

-- ============================================================================
-- 5. Track Verification Checkpoints - Verification state per ladder rung
-- ============================================================================
CREATE TABLE IF NOT EXISTS track_verification_checkpoints (
    id              BIGSERIAL       NOT NULL,
    track_id        UUID            NOT NULL REFERENCES skill_tracks(id) ON DELETE CASCADE,
    user_id         BIGINT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ladder_id       BIGINT          NOT NULL REFERENCES skill_ladders(id) ON DELETE CASCADE,
    level_index     SMALLINT        NOT NULL,
    status          VARCHAR(20)     NOT NULL DEFAULT 'pending',  -- pending|in_progress|verified|failed|expired
    evidence_refs   JSONB           NOT NULL DEFAULT '[]',       -- [{type, uri, rubric_score, verifier, timestamp}]
    rubric_scores   JSONB           NOT NULL DEFAULT '{}',       -- {criterion: {score, confidence, rationale}}
    verifier        VARCHAR(20)     NOT NULL DEFAULT 'model',    -- model|human|peer
    verified_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,                                 -- mastery expiry date
    recheck_count   INTEGER         NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_track_verification_checkpoints PRIMARY KEY (id),
    CONSTRAINT uq_track_checkpoints_unique UNIQUE (track_id, level_index),
    CONSTRAINT ck_track_checkpoints_status CHECK (status IN ('pending', 'in_progress', 'verified', 'failed', 'expired')),
    CONSTRAINT ck_track_checkpoints_verifier CHECK (verifier IN ('model', 'human', 'peer'))
);

CREATE INDEX IF NOT EXISTS idx_track_checkpoints_track ON track_verification_checkpoints (track_id, level_index);
CREATE INDEX IF NOT EXISTS idx_track_checkpoints_status ON track_verification_checkpoints (status);
CREATE INDEX IF NOT EXISTS idx_track_checkpoints_expires ON track_verification_checkpoints (expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================================
-- 6. Trigger: Auto-update updated_at timestamps
-- ============================================================================
-- Helper function (idempotent; some dev DBs already have it from earlier migrations)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_skill_tracks_updated ON skill_tracks;
CREATE TRIGGER trg_skill_tracks_updated
    BEFORE UPDATE ON skill_tracks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_skill_ladders_updated ON skill_ladders;
CREATE TRIGGER trg_skill_ladders_updated
    BEFORE UPDATE ON skill_ladders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_track_checkpoints_updated ON track_verification_checkpoints;
CREATE TRIGGER trg_track_checkpoints_updated
    BEFORE UPDATE ON track_verification_checkpoints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 7. View: Cross-Track Dashboard Summary
-- ============================================================================
CREATE OR REPLACE VIEW user_tracks_dashboard AS
SELECT
    st.id AS track_id,
    st.user_id,
    st.skill_tag,
    st.skill_graph_ref,
    st.goal_level,
    st.goal_type,
    st.status,
    st.progress_pct,
    st.current_ladder_rung,
    st.coach_narrative,
    st.started_at,
    st.last_activity_at,
    st.paused_at,
    st.completed_at,
    -- Current ladder rung details
    sl.level_name AS current_level_name,
    sl.sub_skills AS current_sub_skills,
    sl.evidence_types AS current_evidence_types,
    -- Next ladder rung (if not at max)
    CASE
        WHEN st.current_ladder_rung < 3 THEN
            (SELECT jsonb_build_object(
                'level_index', sl2.level_index,
                'level_name', sl2.level_name,
                'sub_skills', sl2.sub_skills,
                'evidence_types', sl2.evidence_types
            ) FROM skill_ladders sl2
             WHERE sl2.skill_tag = st.skill_tag
               AND sl2.goal_type = st.goal_type
               AND sl2.level_index = st.current_ladder_rung + 1
               AND sl2.is_active = TRUE
             LIMIT 1)
        ELSE NULL
    END AS next_rung,
    -- Session stats (last 7 days)
    (
        SELECT jsonb_build_object(
            'total_sessions', COUNT(*),
            'total_minutes', ROUND(SUM(duration_seconds) / 60.0),
            'avg_energy', ROUND(AVG(energy_level)::numeric, 1),
            'avg_focus', ROUND(AVG(focus_quality)::numeric, 1)
        )
        FROM track_sessions ts
        WHERE ts.track_id = st.id
          AND ts.started_at >= NOW() - INTERVAL '7 days'
    ) AS recent_activity,
    -- Pending verification
    (
        SELECT jsonb_build_object(
            'level_index', tvc.level_index,
            'status', tvc.status,
            'expires_at', tvc.expires_at
        )
        FROM track_verification_checkpoints tvc
        WHERE tvc.track_id = st.id
          AND tvc.status IN ('pending', 'in_progress')
        ORDER BY tvc.level_index
        LIMIT 1
    ) AS pending_verification
FROM skill_tracks st
LEFT JOIN skill_ladders sl
    ON sl.skill_tag = st.skill_tag
   AND sl.goal_type = st.goal_type
   AND sl.level_index = st.current_ladder_rung
   AND sl.is_active = TRUE
WHERE st.status != 'archived';

-- ============================================================================
-- 8. Seed Default Skill Ladders (from competency KG)
-- ============================================================================
-- Note: These are template ladders. Real ladders should be generated from the
-- competency KG (mk-008) and knowledge DB for each skill_tag + goal_type combo.
-- The migration from KG exports happens via application logic (see ladder service).

-- Example: Personal Finance ladders
INSERT INTO skill_ladders (skill_tag, goal_type, level_index, level_name, sub_skills, prerequisites, evidence_types, xp_reward) VALUES
-- Hobby track
('personal_finance', 'hobby', 0, 'Novice',
 '[{"name": "Budgeting Basics", "description": "Create and maintain a simple monthly budget", "prerequisites": [], "can_do_statements": ["I can list all income sources", "I can categorize expenses", "I can track spending for a month"]}, {"name": "Emergency Fund", "description": "Build a $1,000 starter emergency fund", "prerequisites": ["Budgeting Basics"], "can_do_statements": ["I can calculate my monthly essential expenses", "I have a separate savings account", "I have $1,000 saved for emergencies"]}]'::jsonb,
 '[]'::jsonb,
 '["quiz", "artifact"]'::jsonb,
 100
),
('personal_finance', 'hobby', 1, 'Competent',
 '[{"name": "Debt Management", "description": "Systematically eliminate high-interest debt", "prerequisites": ["Emergency Fund"], "can_do_statements": ["I can list all debts with interest rates", "I can execute a debt avalanche plan", "I have zero credit card debt"]}, {"name": "Basic Investing", "description": "Start automated index fund investing", "prerequisites": ["Emergency Fund"], "can_do_statements": ["I can explain ETF vs mutual fund", "I have a brokerage account", "I have automated monthly investments"]}]'::jsonb,
 '["personal_finance:hobby:0"]'::jsonb,
 '["quiz", "project", "artifact"]'::jsonb,
 250
),
('personal_finance', 'hobby', 2, 'Proficient',
 '[{"name": "Tax Optimization", "description": "Leverage tax-advantaged accounts effectively", "prerequisites": ["Basic Investing"], "can_do_statements": ["I max out my 401(k) match", "I contribute to an IRA", "I understand Roth vs Traditional"]}, {"name": "Wealth Protection", "description": "Insurance and estate basics", "prerequisites": ["Basic Investing"], "can_do_statements": ["I have adequate term life insurance", "I have a basic will", "I understand disability insurance"]}]'::jsonb,
 '["personal_finance:hobby:1"]'::jsonb,
 '["project", "artifact", "oral_defense"]'::jsonb,
 500
),
('personal_finance', 'hobby', 3, 'Expert',
 '[{"name": "Advanced Portfolio Construction", "description": "Multi-asset allocation with rebalancing", "prerequisites": ["Tax Optimization", "Wealth Protection"], "can_do_statements": ["I can design an IPS", "I rebalance quarterly", "I use tax-loss harvesting"]}, {"name": "Financial Independence Planning", "description": "Design a sustainable withdrawal strategy", "prerequisites": ["Advanced Portfolio Construction"], "can_do_statements": ["I know my FI number", "I have a withdrawal strategy", "I stress-test my plan"]}]'::jsonb,
 '["personal_finance:hobby:2"]'::jsonb,
 '["artifact", "oral_defense", "transfer_test"]'::jsonb,
 1000
),

-- Job-ready track (more rigorous)
('personal_finance', 'job-ready', 0, 'Novice',
 '[{"name": "Financial Literacy Foundations", "description": "Core concepts: time value of money, compounding, risk/return", "prerequisites": [], "can_do_statements": ["I can calculate compound interest", "I understand inflation impact", "I can explain risk-return tradeoff"]}, {"name": "Budgeting & Cash Flow Management", "description": "Professional-grade budgeting with forecasting", "prerequisites": ["Financial Literacy Foundations"], "can_do_statements": ["I can build a 12-month cash flow forecast", "I use zero-based budgeting", "I track variance vs plan"]}]'::jsonb,
 '[]'::jsonb,
 '["quiz", "project"]'::jsonb,
 150
),
('personal_finance', 'job-ready', 1, 'Competent',
 '[{"name": "Debt & Credit Optimization", "description": "Credit scoring, debt restructuring, leverage strategies", "prerequisites": ["Budgeting & Cash Flow Management"], "can_do_statements": ["I can read a credit report", "I optimize credit utilization", "I understand good vs bad debt"]}, {"name": "Investment Fundamentals", "description": "Asset classes, diversification, portfolio construction", "prerequisites": ["Financial Literacy Foundations"], "can_do_statements": ["I can build a 3-fund portfolio", "I understand correlation", "I can calculate expected returns"]}]'::jsonb,
 '["personal_finance:job-ready:0"]'::jsonb,
 '["quiz", "project", "artifact"]'::jsonb,
 300
),
('personal_finance', 'job-ready', 2, 'Proficient',
 '[{"name": "Tax-Efficient Investing", "description": "Advanced tax strategies: asset location, TLH, Roth conversions", "prerequisites": ["Investment Fundamentals"], "can_do_statements": ["I optimize asset location", "I execute tax-loss harvesting", "I model Roth conversion ladders"]}, {"name": "Risk Management & Insurance", "description": "Comprehensive insurance planning", "prerequisites": ["Investment Fundamentals"], "can_do_statements": ["I can calculate insurance needs", "I understand policy riders", "I review coverage annually"]}]'::jsonb,
 '["personal_finance:job-ready:1"]'::jsonb,
 '["project", "artifact", "oral_defense"]'::jsonb,
 600
),
('personal_finance', 'job-ready', 3, 'Expert',
 '[{"name": "Comprehensive Financial Planning", "description": "Integrate all domains into a cohesive financial plan", "prerequisites": ["Tax-Efficient Investing", "Risk Management & Insurance"], "can_do_statements": ["I can write a full financial plan", "I model Monte Carlo simulations", "I coordinate with CPAs/attorneys"]}, {"name": "Client Advisory Competency", "description": "Communicate complex concepts and guide behavior change", "prerequisites": ["Comprehensive Financial Planning"], "can_do_statements": ["I can explain concepts to non-experts", "I use behavioral coaching techniques", "I document recommendations per fiduciary standard"]}]'::jsonb,
 '["personal_finance:job-ready:2"]'::jsonb,
 '["artifact", "oral_defense", "transfer_test"]'::jsonb,
 1200
),

-- Expert track (deepest)
('personal_finance', 'expert', 0, 'Novice',
 '[{"name": "Quantitative Finance Foundations", "description": "Stochastic calculus, option pricing, risk metrics", "prerequisites": [], "can_do_statements": ["I can derive Black-Scholes", "I understand Greeks", "I can calculate VaR"]}, {"name": "Advanced Econometrics", "description": "Time series, factor models, regime detection", "prerequisites": ["Quantitative Finance Foundations"], "can_do_statements": ["I can estimate GARCH models", "I understand cointegration", "I build factor models"]}]'::jsonb,
 '[]'::jsonb,
 '["quiz", "project"]'::jsonb,
 200
),
('personal_finance', 'expert', 1, 'Competent',
 '[{"name": "Portfolio Optimization Theory", "description": "Mean-variance, Black-Litterman, risk parity", "prerequisites": ["Quantitative Finance Foundations"], "can_do_statements": ["I can implement Black-Litterman", "I understand risk budgeting", "I can optimize with constraints"]}, {"name": "Fixed Income Mathematics", "description": "Yield curves, duration, convexity, credit modeling", "prerequisites": ["Quantitative Finance Foundations"], "can_do_statements": ["I can bootstrap a yield curve", "I calculate key rate durations", "I model credit spreads"]}]'::jsonb,
 '["personal_finance:expert:0"]'::jsonb,
 '["quiz", "project", "artifact"]'::jsonb,
 400
),
('personal_finance', 'expert', 2, 'Proficient',
 '[{"name": "Alternative Investments", "description": "Private equity, hedge funds, real assets, crypto", "prerequisites": ["Portfolio Optimization Theory"], "can_do_statements": ["I model PE fund cash flows", "I understand HF strategies", "I evaluate crypto protocols"]}, {"name": "Institutional Risk Management", "description": "Enterprise risk, regulatory capital, stress testing", "prerequisites": ["Fixed Income Mathematics"], "can_do_statements": ["I run CCAR-style stress tests", "I calculate RWA", "I design risk limits frameworks"]}]'::jsonb,
 '["personal_finance:expert:1"]'::jsonb,
 '["project", "artifact", "oral_defense"]'::jsonb,
 800
),
('personal_finance', 'expert', 3, 'Expert',
 '[{"name": "Quantitative Research & Alpha Generation", "description": "Signal research, backtesting, execution, portfolio construction", "prerequisites": ["Alternative Investments", "Institutional Risk Management"], "can_do_statements": ["I can design alpha signals", "I avoid backtest overfitting", "I build production trading systems"]}, {"name": "Thought Leadership & Innovation", "description": "Publish research, develop new methodologies, mentor", "prerequisites": ["Quantitative Research & Alpha Generation"], "can_do_statements": ["I have peer-reviewed publications", "I speak at conferences", "I mentor junior quants"]}]'::jsonb,
 '["personal_finance:expert:2"]'::jsonb,
 '["artifact", "oral_defense", "transfer_test"]'::jsonb,
 1500
)
ON CONFLICT (skill_tag, goal_type, level_index) DO UPDATE SET
    level_name = EXCLUDED.level_name,
    sub_skills = EXCLUDED.sub_skills,
    prerequisites = EXCLUDED.prerequisites,
    evidence_types = EXCLUDED.evidence_types,
    xp_reward = EXCLUDED.xp_reward,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- Guitar ladders
INSERT INTO skill_ladders (skill_tag, goal_type, level_index, level_name, sub_skills, prerequisites, evidence_types, xp_reward) VALUES
('guitar', 'hobby', 0, 'Novice',
 '[{"name": "Basic Chords & Strumming", "description": "Learn 8 essential open chords and basic rhythms", "prerequisites": [], "can_do_statements": ["I can play G, C, D, Em, Am, A, E, Dm cleanly", "I can strum basic 4/4 patterns", "I can switch between chords without stopping"]}, {"name": "Song Repertoire", "description": "Play 5 complete songs from memory", "prerequisites": ["Basic Chords & Strumming"], "can_do_statements": ["I know 5 songs by heart", "I can play along with recordings", "I can sing while playing"]}]'::jsonb,
 '[]'::jsonb,
 '["quiz", "artifact"]'::jsonb,
 100
),
('guitar', 'hobby', 1, 'Competent',
 '[{"name": "Barre Chords & Fretboard Navigation", "description": "Major/minor barre chords and finding notes", "prerequisites": ["Basic Chords & Strumming"], "can_do_statements": ["I can play F, Bm, and all barre shapes", "I can find any note on the fretboard", "I understand the CAGED system basics"]}, {"name": "Fingerpicking Patterns", "description": "Travis picking, arpeggios, classical basics", "prerequisites": ["Basic Chords & Strumming"], "can_do_statements": ["I can play 3 fingerpicking patterns", "I can do basic Travis picking", "I can play simple classical pieces"]}]'::jsonb,
 '["guitar:hobby:0"]'::jsonb,
 '["quiz", "project", "artifact"]'::jsonb,
 250
),
('guitar', 'hobby', 2, 'Proficient',
 '[{"name": "Improvisation & Scales", "description": "Pentatonic, major/minor scales, basic soloing", "prerequisites": ["Barre Chords & Fretboard Navigation"], "can_do_statements": ["I can improvise over 12-bar blues", "I know 5 pentatonic positions", "I can play major scale in 3 keys"]}, {"name": "Music Theory for Guitar", "description": "Chord construction, harmony, song analysis", "prerequisites": ["Barre Chords & Fretboard Navigation"], "can_do_statements": ["I can build any chord from formula", "I understand diatonic harmony", "I can analyze chord progressions"]}]'::jsonb,
 '["guitar:hobby:1"]'::jsonb,
 '["project", "artifact", "oral_defense"]'::jsonb,
 500
),
('guitar', 'hobby', 3, 'Expert',
 '[{"name": "Advanced Techniques", "description": "Sweep picking, tapping, hybrid picking, harmonics", "prerequisites": ["Improvisation & Scales"], "can_do_statements": ["I can sweep pick arpeggios", "I use tapping in solos", "I incorporate pinch harmonics"]}, {"name": "Composition & Arrangement", "description": "Write original music, arrange for band", "prerequisites": ["Music Theory for Guitar"], "can_do_statements": ["I have composed 3 original songs", "I can arrange for multiple instruments", "I understand production basics"]}]'::jsonb,
 '["guitar:hobby:2"]'::jsonb,
 '["artifact", "oral_defense", "transfer_test"]'::jsonb,
 1000
)

ON CONFLICT (skill_tag, goal_type, level_index) DO UPDATE SET
    level_name = EXCLUDED.level_name,
    sub_skills = EXCLUDED.sub_skills,
    prerequisites = EXCLUDED.prerequisites,
    evidence_types = EXCLUDED.evidence_types,
    xp_reward = EXCLUDED.xp_reward,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();