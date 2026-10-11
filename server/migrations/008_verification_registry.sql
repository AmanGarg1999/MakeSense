-- 008_verification_registry.sql — LL-05 append-only verification registry.
-- Mirrors packages/assessment/registry.py (SQLite dev store).
-- Append-only: triggers reject UPDATE and DELETE at the storage layer.
-- Feeds the LL-06 recap schedule (due_events) and the expiry engine.

CREATE TABLE IF NOT EXISTS verification_registry (
    event_id         TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL,
    skill_tag        TEXT NOT NULL,
    level_index      INTEGER NOT NULL CHECK (level_index BETWEEN 0 AND 3),
    track_id         TEXT,
    verdict          TEXT NOT NULL CHECK (verdict IN ('verified','provisional','reinforced','rejected')),
    primary_evidence TEXT CHECK (primary_evidence IN ('E1','E2','E3','E4','E5','E6','E7','E8')),
    corroborating    JSONB NOT NULL DEFAULT '[]',
    evidence_refs    JSONB NOT NULL DEFAULT '[]',
    submission_id    TEXT,
    rubric_ref       TEXT,                 -- rubric_id@version (prompt-versioned scoring)
    prompt_version   TEXT,
    scoring          JSONB,                -- full scoring_result (rationale per criterion)
    verifier         JSONB NOT NULL,       -- {"kind":"model|human|hybrid|deterministic",...}
    escalation_rung  TEXT CHECK (escalation_rung IN ('artifact','defense','in_session','provisional_flag')),
    verified_at      TIMESTAMPTZ NOT NULL,
    expires_at       TIMESTAMPTZ,          -- decay-clock due date (expiry engine)
    recheck_of       TEXT REFERENCES verification_registry(event_id),
    supersedes       TEXT REFERENCES verification_registry(event_id),
    notes            TEXT,
    recorded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_registry_rung
    ON verification_registry (user_id, skill_tag, level_index, verified_at DESC);
CREATE INDEX IF NOT EXISTS idx_registry_due
    ON verification_registry (expires_at) WHERE expires_at IS NOT NULL;

-- Append-only enforcement.
CREATE OR REPLACE FUNCTION registry_reject_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'verification_registry is append-only (% forbidden)', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS registry_no_update ON verification_registry;
CREATE TRIGGER registry_no_update BEFORE UPDATE ON verification_registry
    FOR EACH ROW EXECUTE FUNCTION registry_reject_mutation();

DROP TRIGGER IF EXISTS registry_no_delete ON verification_registry;
CREATE TRIGGER registry_no_delete BEFORE DELETE ON verification_registry
    FOR EACH ROW EXECUTE FUNCTION registry_reject_mutation();

-- Latest event per rung (derived current status — never stored by UPDATE).
CREATE OR REPLACE VIEW verification_registry_latest AS
SELECT DISTINCT ON (user_id, skill_tag, level_index) *
FROM verification_registry
ORDER BY user_id, skill_tag, level_index, verified_at DESC, recorded_at DESC;
