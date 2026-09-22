CREATE TABLE IF NOT EXISTS spaced_repetition_items (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    lesson_id VARCHAR(50) NOT NULL,
    question TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    interval_days INT DEFAULT 0,
    ease_factor REAL DEFAULT 2.5,
    next_review_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, lesson_id, question)
);
