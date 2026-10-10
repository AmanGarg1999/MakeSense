-- LL-08: interest-drift router, future-path suggestions, multi-mode learning
-- Version: 1.0
-- Created: 2026-10-10
-- Depends on: 006 (skill_tracks/skill_ladders — LL-02 contract), 007 (delivery
-- telemetry — LL-04). Interest signals are DERIVED from delivery_segments plus
-- explicit signals (searches, track starts/abandons) captured here.

-- ============================================================================
-- 1. Interest signals — the raw, append-only stream the rolling profile is
--    built from. One row per observable interest event. `kind` says which
--    source it came from (config/interest_drift.json signal_weights).
-- ============================================================================
CREATE TABLE IF NOT EXISTS interest_signals (
    id           BIGSERIAL     NOT NULL,
    user_id      BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ts           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    kind         VARCHAR(20)   NOT NULL
                     CHECK (kind IN ('session', 'content', 'search', 'track_start', 'track_abandon')),
    domain       VARCHAR(100)  NOT NULL,        -- interest domain / skill_tag the signal points at
    track_id     UUID          REFERENCES skill_tracks(id) ON DELETE SET NULL,
    weight       REAL          NOT NULL DEFAULT 1.0,
    source       VARCHAR(50),                   -- e.g. delivery_segment|search_box|track_crud|content_view
    meta         JSONB         NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT pk_interest_signals PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_interest_signals_user_ts ON interest_signals (user_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_interest_signals_domain ON interest_signals (user_id, domain, ts DESC);

-- ============================================================================
-- 2. Rolling interest profile — one row per (user, domain); upserted by the
--    router. confidence is the gated 0..1 score from profile.* config.
-- ============================================================================
CREATE TABLE IF NOT EXISTS interest_profile (
    id            BIGSERIAL     NOT NULL,
    user_id       BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain        VARCHAR(100)  NOT NULL,
    weight        REAL          NOT NULL DEFAULT 0,
    share         REAL          NOT NULL DEFAULT 0,
    confidence    REAL          NOT NULL DEFAULT 0,
    signal_count  INTEGER       NOT NULL DEFAULT 0,
    sources       JSONB         NOT NULL DEFAULT '[]'::jsonb,
    latest_ts     TIMESTAMPTZ,
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_interest_profile PRIMARY KEY (id),
    CONSTRAINT uq_interest_profile UNIQUE (user_id, domain)
);

-- ============================================================================
-- 3. Drift events — change points detected in the profile (windowed share
--    shift). direction=rising feeds side-quest offers; direction=falling on a
--    stated-goal track feeds goal-protection (explicit ask), never an
--    automatic goal change.
-- ============================================================================
CREATE TABLE IF NOT EXISTS drift_events (
    id              BIGSERIAL     NOT NULL,
    user_id         BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain          VARCHAR(100)  NOT NULL,
    direction       VARCHAR(10)   NOT NULL CHECK (direction IN ('rising', 'falling')),
    baseline_share  REAL          NOT NULL,
    recent_share    REAL          NOT NULL,
    delta           REAL          NOT NULL,
    confidence      REAL          NOT NULL,
    is_goal_track   BOOLEAN       NOT NULL DEFAULT FALSE,
    evidence        JSONB         NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_drift_events PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_drift_events_user ON drift_events (user_id, created_at DESC);

-- ============================================================================
-- 4. Quest offers — drifting interests converted into OPTIONAL side quests
--    (LL-07 consumes these). status: open|accepted|dismissed|converted. The
--    stated goal is untouched by construction.
-- ============================================================================
CREATE TABLE IF NOT EXISTS quest_offers (
    id             BIGSERIAL     NOT NULL,
    user_id        BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain         VARCHAR(100)  NOT NULL,
    offer_text     TEXT          NOT NULL,
    confidence     REAL          NOT NULL,
    delta          REAL          NOT NULL,
    evidence       JSONB         NOT NULL DEFAULT '{}'::jsonb,
    status         VARCHAR(12)   NOT NULL DEFAULT 'open'
                      CHECK (status IN ('open', 'accepted', 'dismissed', 'converted')),
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    cooldown_until TIMESTAMPTZ,

    CONSTRAINT pk_quest_offers PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_quest_offers_open ON quest_offers (user_id, status) WHERE status = 'open';

-- ============================================================================
-- 5. Future-path suggestions — output of the mk-031 extension. kind:
--    next_level|adjacent|consolidate|cross_track. why_now + evidence are the
--    grounded narrative and the user's own numbers behind it.
-- ============================================================================
CREATE TABLE IF NOT EXISTS future_path_suggestions (
    id                BIGSERIAL     NOT NULL,
    user_id           BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind              VARCHAR(20)   NOT NULL
                         CHECK (kind IN ('next_level', 'adjacent', 'consolidate', 'cross_track')),
    from_track_id     UUID          REFERENCES skill_tracks(id) ON DELETE SET NULL,
    suggested_skill   VARCHAR(100)  NOT NULL,
    suggested_level   INTEGER,
    title             TEXT          NOT NULL,
    why_now           TEXT          NOT NULL,
    priority          REAL          NOT NULL DEFAULT 0,
    evidence          JSONB         NOT NULL DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_future_path_suggestions PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_future_paths_user ON future_path_suggestions (user_id, created_at DESC);

-- ============================================================================
-- 6. Learning-mode selection — per-track mode choice. All modes share the one
--    verification_endpoint (LL-05); decided_by records who chose it.
-- ============================================================================
CREATE TABLE IF NOT EXISTS learning_mode_selection (
    id                    BIGSERIAL     NOT NULL,
    user_id               BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track_id              UUID          REFERENCES skill_tracks(id) ON DELETE CASCADE,
    skill_tag             VARCHAR(100)  NOT NULL,
    mode                  VARCHAR(20)   NOT NULL
                             CHECK (mode IN ('guided', 'project_together', 'explore_explain', 'drill_verify')),
    decided_by            VARCHAR(20)   NOT NULL
                             CHECK (decided_by IN ('user_override', 'level_default', 'goal_default')),
    reason                TEXT,
    verification_endpoint VARCHAR(200)  NOT NULL,
    updated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_learning_mode_selection PRIMARY KEY (id),
    CONSTRAINT uq_learning_mode UNIQUE (user_id, track_id)
);

-- ============================================================================
-- 7. Project curricula — reverse-derived plans generated by project_together
--    mode. plan holds the ordered steps, each carrying cited content ids.
-- ============================================================================
CREATE TABLE IF NOT EXISTS project_curricula (
    id           BIGSERIAL     NOT NULL,
    user_id      BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track_id     UUID          REFERENCES skill_tracks(id) ON DELETE SET NULL,
    skill_tag    VARCHAR(100)  NOT NULL,
    artifact     JSONB         NOT NULL,        -- the chosen end-state artifact
    plan         JSONB         NOT NULL,        -- ordered steps w/ citations
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_project_curricula PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_project_curricula_user ON project_curricula (user_id, created_at DESC);
