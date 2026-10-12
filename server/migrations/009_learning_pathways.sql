-- 009_learning_pathways.sql — LL-09a: multi-level learning pathways.
-- Canonical level vocabulary (LL-09b/c/d depend on it):
--   micro | certificate | undergrad | masters | phd | mba
-- Idempotent: safe to re-run (CREATE IF NOT EXISTS + ON CONFLICT DO NOTHING).

-- ============================================================================
-- 0. Shared level enum check — spelled once per table; the Python side of
--    this vocabulary lives in server/pathway_service.py:PATHWAY_LEVELS.
-- ============================================================================

-- ============================================================================
-- 1. Learning Pathways — a user's enrolment in a level-capped learning journey
-- ============================================================================
CREATE TABLE IF NOT EXISTS learning_pathways (
    id                 UUID         NOT NULL DEFAULT gen_random_uuid(),
    user_id            BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    level              VARCHAR(20)  NOT NULL
        CHECK (level IN ('micro', 'certificate', 'undergrad', 'masters', 'phd', 'mba')),
    title              VARCHAR(200),
    status             VARCHAR(20)  NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'completed', 'archived')),
    started_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    target_completion  DATE,
    completed_at       TIMESTAMPTZ,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_learning_pathways PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_pathways_user ON learning_pathways (user_id);
CREATE INDEX IF NOT EXISTS idx_pathways_user_status ON learning_pathways (user_id, status);
CREATE INDEX IF NOT EXISTS idx_pathways_level ON learning_pathways (level, status);
CREATE INDEX IF NOT EXISTS idx_pathways_target ON learning_pathways (target_completion)
    WHERE target_completion IS NOT NULL;

-- ============================================================================
-- 2. Pathway Curriculum — ordered content packs that make up a pathway
-- ============================================================================
CREATE TABLE IF NOT EXISTS pathway_curriculum (
    id               BIGSERIAL      NOT NULL,
    pathway_id       UUID           NOT NULL REFERENCES learning_pathways(id) ON DELETE CASCADE,
    content_pack_id  VARCHAR(100)   NOT NULL,           -- mspack pack id (file-based, no FK)
    sequence         INTEGER        NOT NULL,           -- 0-based order within the pathway
    required         BOOLEAN        NOT NULL DEFAULT TRUE,
    credits          NUMERIC(6,2)   NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_pathway_curriculum PRIMARY KEY (id),
    CONSTRAINT uq_curriculum_pathway_sequence UNIQUE (pathway_id, sequence),
    CONSTRAINT ck_curriculum_sequence CHECK (sequence >= 0),
    CONSTRAINT ck_curriculum_credits CHECK (credits >= 0)
);

CREATE INDEX IF NOT EXISTS idx_curriculum_pathway ON pathway_curriculum (pathway_id, sequence);
CREATE INDEX IF NOT EXISTS idx_curriculum_pack ON pathway_curriculum (content_pack_id);

-- ============================================================================
-- 3. Level Metadata — canonical per-level program characteristics (seeded)
-- ============================================================================
CREATE TABLE IF NOT EXISTS level_metadata (
    level                   VARCHAR(20) NOT NULL
        CHECK (level IN ('micro', 'certificate', 'undergrad', 'masters', 'phd', 'mba')),
    typical_duration_weeks  INTEGER     NOT NULL CHECK (typical_duration_weeks > 0),
    credit_system           TEXT        NOT NULL,
    assessment_type         TEXT        NOT NULL,
    mentor_model            TEXT        NOT NULL,
    recap_interval_days     INTEGER     NOT NULL CHECK (recap_interval_days > 0),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_level_metadata PRIMARY KEY (level)
);

-- Seed all 6 canonical levels (LL-09a). Idempotent.
INSERT INTO level_metadata (
    level, typical_duration_weeks, credit_system, assessment_type, mentor_model, recap_interval_days
) VALUES
    ('micro',       2,   'badge (no formal credit)',   'in-app practical tasks',           'AI coach',                    7),
    ('certificate', 12,  'CEU / credit-eligible',      'proctored practical + project',     'AI coach + peer cohort',      14),
    ('undergrad',   180, 'credit hours',               'exams + projects + viva',           'faculty + AI tutor',          30),
    ('masters',     104, 'graduate credit hours',      'coursework + thesis/research',      'faculty advisor',             45),
    ('phd',         208, 'research credits / dissertation', 'comprehensives + defense',     'doctoral committee',          60),
    ('mba',         104, 'credit hours',               'case studies + capstone',           'faculty + industry mentor',   30)
ON CONFLICT (level) DO NOTHING;

-- ============================================================================
-- 4. User Transcript — completion + credential record per (user, pathway, pack)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_transcript (
    id                 BIGSERIAL     NOT NULL,
    user_id            BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pathway_id         UUID          NOT NULL REFERENCES learning_pathways(id) ON DELETE CASCADE,
    content_pack_id    VARCHAR(100)  NOT NULL,
    mastery_score      REAL          NOT NULL DEFAULT 0 CHECK (mastery_score >= 0 AND mastery_score <= 1),
    completed_at       TIMESTAMPTZ,
    credential_issued  BOOLEAN       NOT NULL DEFAULT FALSE,
    credential_type    VARCHAR(50),
    recorded_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_user_transcript PRIMARY KEY (id),
    CONSTRAINT uq_transcript_user_pathway_pack UNIQUE (user_id, pathway_id, content_pack_id),
    CONSTRAINT ck_transcript_credential CHECK (
        (credential_issued = FALSE) OR (credential_type IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_transcript_user ON user_transcript (user_id);
CREATE INDEX IF NOT EXISTS idx_transcript_pathway ON user_transcript (pathway_id);
CREATE INDEX IF NOT EXISTS idx_transcript_pack ON user_transcript (user_id, content_pack_id);
CREATE INDEX IF NOT EXISTS idx_transcript_credentials ON user_transcript (credential_issued)
    WHERE credential_issued = TRUE;
