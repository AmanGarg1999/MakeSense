-- 010_content_pack_registry.sql — LL-09c: content pack registry with level metadata.
-- Stores pack manifests (Content Pack Format v1) so the Cloud API can serve
-- GET /packs?level=&prereq_satisfied= against the LL-09a pathway tables.
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS content_packs (
    pack_id        VARCHAR(100)  NOT NULL,
    version        VARCHAR(20)   NOT NULL,          -- semver, e.g. 1.0.0
    title          VARCHAR(200)  NOT NULL,
    schema_version VARCHAR(4)    NOT NULL,          -- manifest schema "0" | "1"
    manifest       JSONB         NOT NULL,          -- full pack manifest
    -- level_target denormalized for indexing; packs without level fields
    -- default to the v0 back-compat interpretation [micro, certificate].
    level_target   TEXT[]        NOT NULL DEFAULT ARRAY['micro','certificate']
        CHECK (level_target <@ ARRAY['micro','certificate','undergrad','masters','phd','mba']::text[]),
    credit_value   NUMERIC(6,2)  NOT NULL DEFAULT 0 CHECK (credit_value >= 0),
    estimated_hours NUMERIC(8,2) CHECK (estimated_hours IS NULL OR estimated_hours >= 0),
    registered_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_content_packs PRIMARY KEY (pack_id, version),
    CONSTRAINT ck_pack_id CHECK (pack_id ~ '^[a-z0-9][a-z0-9._-]{2,63}$')
);

CREATE INDEX IF NOT EXISTS idx_packs_level ON content_packs USING GIN (level_target);
CREATE INDEX IF NOT EXISTS idx_packs_pack_id ON content_packs (pack_id);
