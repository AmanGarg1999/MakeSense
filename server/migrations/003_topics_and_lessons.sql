-- Topics and Lessons tables for the content pipeline
-- Extends the gamification schema with content management

CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    email TEXT,
    email_hash TEXT,  -- SHA-256 hash for privacy-safe lookup
    raw_topics TEXT[] NOT NULL,
    categories TEXT[],
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'error')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_topics_email_hash ON topics(email_hash);
CREATE INDEX IF NOT EXISTS idx_topics_status ON topics(status);

CREATE TABLE IF NOT EXISTS lessons (
    id TEXT PRIMARY KEY,
    topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    difficulty TEXT DEFAULT 'beginner' CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    estimated_time_minutes INT DEFAULT 15,
    skill_tags TEXT[] DEFAULT '{}',
    prerequisites TEXT[] DEFAULT '{}',
    status TEXT DEFAULT 'generated' CHECK (status IN ('generating', 'generated', 'error')),
    feedback_up INT DEFAULT 0,
    feedback_down INT DEFAULT 0,
    view_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lessons_topic_id ON lessons(topic_id);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    lesson_id TEXT REFERENCES lessons(id) ON DELETE CASCADE,
    answers JSONB NOT NULL DEFAULT '[]'::jsonb,
    score FLOAT NOT NULL DEFAULT 0,
    total_questions INT NOT NULL DEFAULT 0,
    correct_answers INT NOT NULL DEFAULT 0,
    xp_earned INT NOT NULL DEFAULT 0,
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    user_id BIGINT,
    lesson_id TEXT REFERENCES lessons(id) ON DELETE CASCADE,
    topic TEXT,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('up', 'down')),
    comment TEXT,
    user_identifier TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_lesson_id ON feedback(lesson_id);

-- Trigger to update topics.updated_at
CREATE OR REPLACE FUNCTION update_topics_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_topics_updated_at ON topics;
CREATE TRIGGER trigger_topics_updated_at
    BEFORE UPDATE ON topics
    FOR EACH ROW
    EXECUTE FUNCTION update_topics_updated_at();
