-- LL-04: Delivery-dial session telemetry + adaptive flip state
-- Version: 1.0
-- Created: 2026-10-09
-- Keys off LL-02 (t_48c67ccb) schema: skill_tracks(id UUID, skill_tag, goal_type),
-- skill_ladders(skill_tag, goal_type, level_index). If LL-02 renames anything,
-- this migration must be revisited before deploy (see task t_eb28e508 summary).

-- ============================================================================
-- 1. Delivery segments — one row per segment played, with the mode decision,
--    engagement signals, and the immediate retrieval outcome.
-- ============================================================================
CREATE TABLE IF NOT EXISTS delivery_segments (
    id                BIGSERIAL       NOT NULL,
    user_id           BIGINT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track_id          UUID            REFERENCES skill_tracks(id) ON DELETE CASCADE,  -- LL-02 track
    skill_tag         VARCHAR(100)    NOT NULL,          -- denormalized from track for flip lookups
    session_id        VARCHAR(100)    NOT NULL,
    segment_index     INTEGER         NOT NULL DEFAULT 0,
    segment_kind      VARCHAR(20)     NOT NULL CHECK (segment_kind IN ('intake', 'consolidation')),
    delivery_mode     VARCHAR(30)     NOT NULL,          -- explain|read|watch|predict_before_reveal|retrieval_prompt|mini_task|teach_it_back|project_step
    mode_class        VARCHAR(10)     NOT NULL CHECK (mode_class IN ('passive', 'active')),
    decided_by        VARCHAR(20)     NOT NULL DEFAULT 'track_default'  -- track_default|classifier|escalation|energy_override|user_override
        CHECK (decided_by IN ('track_default', 'classifier', 'escalation', 'energy_override', 'user_override')),
    dwell_seconds     INTEGER         NOT NULL DEFAULT 0,
    paused_seconds    INTEGER         NOT NULL DEFAULT 0,
    abandoned         BOOLEAN         NOT NULL DEFAULT FALSE,
    retrieval_outcome VARCHAR(10)     CHECK (retrieval_outcome IN ('correct', 'partial', 'incorrect', 'none') OR retrieval_outcome IS NULL),
    energy_level      SMALLINT        CHECK (energy_level IS NULL OR (energy_level BETWEEN 1 AND 5)),
    ladder_level      SMALLINT,                          -- current rung snapshot (LL-02 ladder)
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_delivery_segments PRIMARY KEY (id),
    CONSTRAINT uq_delivery_segment UNIQUE (session_id, track_id, segment_index)
);

CREATE INDEX IF NOT EXISTS idx_delivery_segments_skill ON delivery_segments (skill_tag, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_delivery_segments_track ON delivery_segments (track_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_delivery_segments_user ON delivery_segments (user_id, created_at DESC);

-- ============================================================================
-- 2. Mode escalations — the adaptive flip rule's decisions. Each row records
--    WHY a skill was escalated to active delivery, with the evidence payload,
--    and for how many sessions it holds.
-- ============================================================================
CREATE TABLE IF NOT EXISTS delivery_mode_escalations (
    id                      BIGSERIAL   NOT NULL,
    user_id                 BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track_id                UUID        REFERENCES skill_tracks(id) ON DELETE SET NULL,
    skill_tag               VARCHAR(100) NOT NULL,
    reason                  VARCHAR(30) NOT NULL CHECK (reason IN ('passive_dropout', 'failed_retrieval')),
    evidence                JSONB       NOT NULL,        -- {sessions_observed, passive_abandon_rate, failed_count, sample_segment_ids, thresholds}
    escalate_for_sessions   INTEGER     NOT NULL,        -- from config flip_rule.escalation_sessions
    sessions_consumed       INTEGER     NOT NULL DEFAULT 0,
    active                  BOOLEAN     NOT NULL DEFAULT TRUE,
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expired_at              TIMESTAMPTZ,

    CONSTRAINT pk_delivery_mode_escalations PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_escalations_active_skill ON delivery_mode_escalations (skill_tag, user_id) WHERE active;

-- ============================================================================
-- 3. Companion bridge log — narrative bridges shown between segments, so the
--    voice layer's output is attributable to the ladder state that produced it.
-- ============================================================================
CREATE TABLE IF NOT EXISTS companion_bridges (
    id            BIGSERIAL   NOT NULL,
    user_id       BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track_id      UUID        REFERENCES skill_tracks(id) ON DELETE SET NULL,
    skill_tag     VARCHAR(100) NOT NULL,
    bridge_text   TEXT        NOT NULL,
    motivation    VARCHAR(20) NOT NULL CHECK (motivation IN ('competence', 'autonomy', 'relatedness')),
    source_state  JSONB       NOT NULL,        -- ladder/mastery snapshot used to generate the string
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_companion_bridges PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_companion_bridges_track ON companion_bridges (track_id, created_at DESC);
