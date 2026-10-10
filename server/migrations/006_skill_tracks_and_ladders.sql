-- LL-02 contract: multi-skill-track state + goal-relative skill ladders
-- Version: 1.0
-- Created: 2026-10-10
--
-- WHY THIS FILE EXISTS HERE: LL-08 (interest-drift router, future paths,
-- multi-mode learning) depends on LL-02 (t_48c67ccb). LL-02 was archived
-- without producing this migration, but LL-04's 007_delivery_telemetry.sql
-- already FKs to skill_tracks(id) and LL-04's engine already reads
-- skill_tracks(skill_tag, goal_type, status) + skill_ladders(level_index,
-- sub_skills). This file restores the SHARED DATA CONTRACT that 007 and LL-08
-- both assume, so the loop's backend can be built and verified. It is the
-- SQL contract only — LL-02's WatermelonDB UI, cross-track dashboard and CRUD
-- flow remain LL-02's scope. Merge order: 006 before 007 before 008.
--
-- Assumed by: server/migrations/007_delivery_telemetry.sql,
--             server/migrations/008_interest_drift_and_paths.sql,
--             services/event-tracker/app/{delivery_engine,interest_drift,
--                                           future_paths}.py

-- gen_random_uuid() is built in on PostgreSQL >= 13; on older servers enable
-- pgcrypto (CREATE EXTENSION pgcrypto). Left commented so an unprivileged
-- migration runner does not fail.
-- CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- 1. Skill tracks — one row per (user, skill, goal_type) journey in flight.
--    LL-02: track = skill graph ref, mastery vector, batch schedule, coach
--    narrative, status. mastery_vector shape: {"<sub_skill>": {"score": 0..1,
--    "last_seen": timestamptz}} — the same dict LL-04's engine consumes.
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_tracks (
    id                  UUID            NOT NULL DEFAULT gen_random_uuid(),
    user_id             BIGINT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_tag           VARCHAR(100)    NOT NULL,
    goal_type           VARCHAR(20)     NOT NULL CHECK (goal_type IN ('hobby', 'job-ready', 'expert')),
    title               VARCHAR(200),
    status              VARCHAR(10)     NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'paused', 'done')),
    ladder_ref          VARCHAR(200),                       -- "<skill_tag>:<goal_type>"
    current_ladder_rung INTEGER         NOT NULL DEFAULT 0,
    mastery_vector      JSONB           NOT NULL DEFAULT '{}'::jsonb,
    batch_schedule      JSONB           NOT NULL DEFAULT '{}'::jsonb,
    coach_narrative     TEXT,
    last_activity_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_skill_tracks PRIMARY KEY (id),
    CONSTRAINT uq_skill_track UNIQUE (user_id, skill_tag, goal_type)
);

CREATE INDEX IF NOT EXISTS idx_skill_tracks_user ON skill_tracks (user_id, status);
CREATE INDEX IF NOT EXISTS idx_skill_tracks_skill ON skill_tracks (skill_tag, goal_type);
CREATE INDEX IF NOT EXISTS idx_skill_tracks_activity ON skill_tracks (user_id, last_activity_at DESC);

-- ============================================================================
-- 2. Skill ladders — goal-relative levels for a skill. A topic maps to
--    DIFFERENT ladders depending on the stated goal (hobby vs job-ready).
--    sub_skills shape: [{"name": "...", "can_do_statements": ["can ..."],
--    "prerequisites": ["..."]}]
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_ladders (
    id             BIGSERIAL     NOT NULL,
    skill_tag      VARCHAR(100)  NOT NULL,
    goal_type      VARCHAR(20)   NOT NULL CHECK (goal_type IN ('hobby', 'job-ready', 'expert')),
    level_index    INTEGER       NOT NULL,        -- 0-based rung
    level_name     VARCHAR(50)   NOT NULL,        -- novice|competent|proficient|expert
    sub_skills     JSONB         NOT NULL DEFAULT '[]'::jsonb,
    prerequisites  JSONB         NOT NULL DEFAULT '[]'::jsonb,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_skill_ladders PRIMARY KEY (id),
    CONSTRAINT uq_skill_ladder UNIQUE (skill_tag, goal_type, level_index)
);

CREATE INDEX IF NOT EXISTS idx_skill_ladders_skill ON skill_ladders (skill_tag, goal_type, level_index);

-- ============================================================================
-- 3. Skill mastery — normalized companion to skill_tracks.mastery_vector so
--    per-sub-skill deltas can be queried/indexed without JSON unpacking.
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_mastery (
    id          BIGSERIAL     NOT NULL,
    user_id     BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track_id    UUID          REFERENCES skill_tracks(id) ON DELETE CASCADE,
    sub_skill   VARCHAR(150)  NOT NULL,
    score       REAL          NOT NULL DEFAULT 0 CHECK (score >= 0 AND score <= 1),
    last_seen   TIMESTAMPTZ,
    updated_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_skill_mastery PRIMARY KEY (id),
    CONSTRAINT uq_skill_mastery UNIQUE (user_id, track_id, sub_skill)
);

CREATE INDEX IF NOT EXISTS idx_skill_mastery_track ON skill_mastery (track_id);
