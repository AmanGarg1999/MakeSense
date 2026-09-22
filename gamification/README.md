# Gamification System - Data Model Documentation

## Overview

This document describes the complete data schema for the MakeSense gamification system, including user levels, engagement points, skill ratings, interaction events, achievements, and supporting infrastructure.

---

## Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ ENGAGEMENT_POINTS : "earns"
    USERS ||--o{ USER_SKILL_RATINGS : "has"
    USERS ||--o{ USER_INTERACTION_EVENTS : "generates"
    USERS ||--o{ USER_ACHIEVEMENTS : "unlocks"
    USERS }|--|| USER_LEVELS : "at_level"
    USER_ACHIEVEMENTS }|--|| ACHIEVEMENTS : "is"
    USER_SKILL_RATINGS }|--|| SKILL_TAXONOMY : "maps_to"
    SKILL_TAXONOMY ||--o{ SKILL_TAXONOMY : "parent_of"

    USERS {
        BIGINT id PK
        SMALLINT current_level FK
        BIGINT total_xp
        BIGINT total_engagement_points
        SMALLINT current_streak
        SMALLINT longest_streak
        DATE last_activity_date
    }

    USER_LEVELS {
        SMALLINT level_id PK
        VARCHAR level_name
        BIGINT xp_threshold
        BIGINT xp_to_next
        VARCHAR badge_icon
        VARCHAR badge_color
        TEXT description
    }

    ENGAGEMENT_POINTS {
        BIGINT id PK
        BIGINT user_id FK
        INTEGER points
        VARCHAR source_type
        BIGINT source_id
        JSONB source_metadata
        TEXT description
        TIMESTAMPTZ created_at
    }

    USER_SKILL_RATINGS {
        BIGINT id PK
        BIGINT user_id FK
        VARCHAR skill_tag FK
        SMALLINT proficiency_score (0-100)
        INTEGER evidence_count
        REAL confidence (0.0-1.0)
        TIMESTAMPTZ last_updated
    }

    USER_INTERACTION_EVENTS {
        BIGINT id PK
        BIGINT user_id FK
        UUID session_id
        VARCHAR event_type
        VARCHAR event_category
        JSONB metadata
        INTEGER duration_ms
        TEXT page_url
        TEXT referrer_url
        TEXT user_agent
        VARCHAR ip_hash
        TIMESTAMPTZ created_at
    }

    SKILL_TAXONOMY {
        BIGINT id PK
        VARCHAR skill_tag PK
        VARCHAR display_name
        TEXT description
        VARCHAR category
        VARCHAR parent_tag FK
        SMALLINT difficulty (1-5)
        BOOLEAN is_active
    }

    ACHIEVEMENTS {
        BIGINT id PK
        VARCHAR code UK
        VARCHAR name
        TEXT description
        VARCHAR icon
        VARCHAR category
        JSONB criteria_json
        INTEGER xp_reward
        BOOLEAN is_hidden
        BOOLEAN is_active
    }

    USER_ACHIEVEMENTS {
        BIGINT id PK
        BIGINT user_id FK
        BIGINT achievement_id FK
        TIMESTAMPTZ earned_at
        JSONB metadata
    }
```

---

## Table Specifications

### 1. `user_levels` - Level Definitions

Defines the XP thresholds, names, and visual representation for each user level.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `level_id` | SMALLINT | PK, NOT NULL | Level identifier (1-8+) |
| `level_name` | VARCHAR(50) | UNIQUE, NOT NULL | Display name (Novice, Explorer, etc.) |
| `xp_threshold` | BIGINT | NOT NULL, ≥0 | Minimum XP to reach this level |
| `xp_to_next` | BIGINT | NOT NULL, >0 | XP needed to reach next level |
| `badge_icon` | VARCHAR(100) | | Emoji or icon identifier |
| `badge_color` | VARCHAR(7) | CHECK (hex) | Hex color for badge |
| `description` | TEXT | | Level description |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update |

**Default Levels:**
| Level | Name | XP Threshold | XP to Next | Icon | Color |
|-------|------|--------------|------------|------|-------|
| 1 | Novice | 0 | 100 | 🌱 | #8FBC8F |
| 2 | Explorer | 100 | 250 | 🧭 | #4682B4 |
| 3 | Learner | 350 | 500 | 📚 | #5F9EA0 |
| 4 | Practitioner | 850 | 1000 | ⚡ | #DAA520 |
| 5 | Scholar | 1850 | 2000 | 🎓 | #B8860B |
| 6 | Expert | 3850 | 3000 | 💎 | #9370DB |
| 7 | Master | 6850 | 5000 | 🏆 | #FFD700 |
| 8 | Grandmaster | 11850 | 10000 | 👑 | #FF6B6B |

**Indexes:** `idx_user_levels_xp_threshold` for fast level lookup by XP

---

### 2. `users` - Gamification Extensions

Extends the base users table with gamification fields.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `current_level` | SMALLINT | NOT NULL DEFAULT 1, FK→user_levels | Current user level |
| `total_xp` | BIGINT | NOT NULL DEFAULT 0 | Lifetime XP earned |
| `total_engagement_points` | BIGINT | NOT NULL DEFAULT 0 | Total points from all sources |
| `current_streak` | SMALLINT | NOT NULL DEFAULT 0 | Current daily login streak |
| `longest_streak` | SMALLINT | NOT NULL DEFAULT 0 | Longest streak achieved |
| `last_activity_date` | DATE | | Last activity date for streak calc |
| `total_engagement_points` | BIGINT | NOT NULL DEFAULT 0 | Sum of all positive points |

**Foreign Key:** `fk_users_current_level` → `user_levels(level_id)`

---

### 3. `engagement_points` - Points Ledger

Immutable ledger of all point transactions with full audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGSERIAL | PK | Unique transaction ID |
| `user_id` | BIGINT | NOT NULL, FK→users | User earning/spending points |
| `points` | INTEGER | NOT NULL, ≠0 | Points awarded (positive) or deducted (negative) |
| `source_type` | VARCHAR(50) | NOT NULL, CHECK | Source category (see below) |
| `source_id` | BIGINT | | Reference to course, question, etc. |
| `source_metadata` | JSONB | | Flexible context data |
| `description` | TEXT | | Human-readable description |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Transaction timestamp |

**Source Types (CHECK constraint):**
- `course_completion` - Completed a full course
- `lesson_completion` - Completed a lesson/module
- `question_answer_correct` - Answered question correctly
- `question_answer_incorrect` - Answered incorrectly (small penalty or zero)
- `streak_bonus` - Daily/weekly streak milestone
- `daily_login` - Daily login bonus
- `peer_help` - Helped another user
- `content_contribution` - Created/contributed content
- `review_completion` - Completed a review
- `achievement_unlock` - Unlocked an achievement
- `referral_bonus` - Referred a new user
- `manual_adjustment` - Admin adjustment

**Indexes:**
- `idx_engagement_points_user_created` - User timeline queries
- `idx_engagement_points_source_type` - Analytics by source
- `idx_engagement_points_user_source` - User-specific source breakdown
- `idx_engagement_points_created_at` - Global time-series
- `idx_engagement_points_positive` - Leaderboard queries (partial, points > 0)

---

### 4. `user_skill_ratings` - Skill Proficiency

Tracks user proficiency per skill tag using Bayesian averaging.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGSERIAL | PK | Unique rating record |
| `user_id` | BIGINT | NOT NULL, FK→users | User being rated |
| `skill_tag` | VARCHAR(100) | NOT NULL, UNIQUE(user_id,skill_tag) | Skill identifier |
| `proficiency_score` | SMALLINT | NOT NULL, 0-100 | Current proficiency (0-100) |
| `evidence_count` | INTEGER | NOT NULL DEFAULT 0, ≥0 | Number of evidence points |
| `confidence` | REAL | NOT NULL DEFAULT 0.0, 0.0-1.0 | Bayesian confidence |
| `last_updated` | TIMESTAMPTZ | DEFAULT NOW() | Last recalculation |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | First evidence |

**Unique Constraint:** `(user_id, skill_tag)` - one rating per skill per user

**Indexes:**
- `idx_user_skill_ratings_user` - All skills for a user
- `idx_user_skill_ratings_tag` - All users for a skill
- `idx_user_skill_ratings_score` - Top skills for user (DESC)
- `idx_user_skill_ratings_updated` - Recently updated skills

---

### 5. `user_interaction_events` - Raw Event Log

Immutable event stream for analytics, debugging, and ML feature extraction.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGSERIAL | PK | Event ID |
| `user_id` | BIGINT | NOT NULL, FK→users | User generating event |
| `session_id` | UUID | NOT NULL DEFAULT gen_random_uuid() | Session identifier |
| `event_type` | VARCHAR(50) | NOT NULL | Specific action (page_view, answer_submit, etc.) |
| `event_category` | VARCHAR(30) | NOT NULL, CHECK | High-level category |
| `metadata` | JSONB | NOT NULL DEFAULT '{}' | Flexible event data |
| `duration_ms` | INTEGER | ≥0 | Time spent (optional) |
| `page_url` | TEXT | | Current page |
| `referrer_url` | TEXT | | Previous page |
| `user_agent` | TEXT | | Browser/client info |
| `ip_hash` | VARCHAR(64) | | Hashed IP for privacy |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Event timestamp |

**Event Categories:**
- `learning` - Course/lesson interactions
- `social` - Comments, helps, shares
- `navigation` - Page views, menu clicks
- `system` - Login, settings, errors
- `assessment` - Quizzes, tests, practice

**Indexes:**
- `idx_user_interaction_events_user_time` - User session analysis
- `idx_user_interaction_events_type` - Event type frequency
- `idx_user_interaction_events_category` - Category analytics
- `idx_user_interaction_events_session` - Session reconstruction
- `idx_user_interaction_events_created` - Time-series queries
- `idx_user_interaction_events_metadata` - JSONB queries (GIN)

**Partitioning:** Recommended monthly partitioning for performance

---

### 6. `skill_taxonomy` - Canonical Skill Definitions

Defines the universe of trackable skills with hierarchy and metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGSERIAL | PK | Internal ID |
| `skill_tag` | VARCHAR(100) | UNIQUE, NOT NULL | Canonical tag (e.g., "python-basics") |
| `display_name` | VARCHAR(100) | NOT NULL | Human-readable name |
| `description` | TEXT | | Detailed description |
| `category` | VARCHAR(50) | | Top-level category |
| `parent_tag` | VARCHAR(100) | FK→skill_taxonomy.skill_tag | Parent skill for hierarchy |
| `difficulty` | SMALLINT | NOT NULL DEFAULT 1, 1-5 | Difficulty rating |
| `is_active` | BOOLEAN | NOT NULL DEFAULT TRUE | Available for rating |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Indexes:**
- `idx_skill_taxonomy_category` - Browse by category
- `idx_skill_taxonomy_parent` - Hierarchy traversal
- `idx_skill_taxonomy_active` - Active skills only (partial)

**Self-referential FK:** `fk_skill_taxonomy_parent` for skill hierarchies

---

### 7. `achievements` - Badge/Milestone Definitions

Defines unlockable achievements with criteria and rewards.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGSERIAL | PK | Achievement ID |
| `code` | VARCHAR(50) | UNIQUE, NOT NULL | Machine-readable code |
| `name` | VARCHAR(100) | NOT NULL | Display name |
| `description` | TEXT | | Full description |
| `icon` | VARCHAR(100) | | Emoji/icon |
| `category` | VARCHAR(30) | | progress, social, mastery, streak, special |
| `criteria_json` | JSONB | NOT NULL | Unlock criteria (see below) |
| `xp_reward` | INTEGER | NOT NULL DEFAULT 0, ≥0 | XP awarded on unlock |
| `is_hidden` | BOOLEAN | NOT NULL DEFAULT FALSE | Secret achievement |
| `is_active` | BOOLEAN | NOT NULL DEFAULT TRUE | Currently earnable |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | |

**Criteria JSON Structure:**
```json
{
  "metric": "total_xp",
  "operator": ">=",
  "value": 1000,
  "timeframe_days": null  // optional: rolling window
}
```
Supported metrics: `total_xp`, `current_streak`, `longest_streak`, `skills_tracked`, `questions_answered`, `courses_completed`, `achievements_earned`, `helpful_votes_received`

**Indexes:**
- `idx_achievements_category` - Browse by category
- `idx_achievements_active` - Active achievements (partial)

---

### 8. `user_achievements` - Earned Achievements

Junction table tracking which users earned which achievements.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BIGSERIAL | PK | |
| `user_id` | BIGINT | NOT NULL, FK→users | |
| `achievement_id` | BIGINT | NOT NULL, FK→achievements | |
| `earned_at` | TIMESTAMPTZ | DEFAULT NOW() | When unlocked |
| `metadata` | JSONB | DEFAULT '{}' | Context at earn time |

**Unique Constraint:** `(user_id, achievement_id)` - earn once per achievement

**Indexes:**
- `idx_user_achievements_user` - User's achievements
- `idx_user_achievements_earned` - Recent unlocks

---

## Database Views

### `user_gamification_summary`
Aggregated per-user gamification state for dashboards and profiles.

```sql
SELECT * FROM user_gamification_summary WHERE user_id = 123;
```

### `leaderboard_xp`
Global XP leaderboard with ranks.

```sql
SELECT * FROM leaderboard_xp LIMIT 100;
```

### `leaderboard_skill`
Per-skill leaderboards (top users by proficiency).

```sql
SELECT * FROM leaderboard_skill WHERE skill_tag = 'python-basics' LIMIT 10;
```

---

## Core Functions

### `calculate_user_level(total_xp BIGINT) → SMALLINT`
Determines level from XP total using `user_levels` thresholds.

### `award_engagement_points(user_id, points, source_type, source_id, metadata, description) → BIGINT`
Atomic point awarding:
1. Inserts ledger entry
2. Updates user totals (XP, engagement points)
3. Recalculates level
4. Awards level-up bonus if applicable
5. Returns point transaction ID

### `update_skill_rating(user_id, skill_tag, evidence_score, evidence_weight) → VOID`
Bayesian proficiency update:
- Prior: 10 "average" evidences at global mean (50)
- Posterior: `(prior_weight * global_avg + sum(evidence * weight)) / (prior_weight + sum(weights))`
- Confidence: `evidence_weight_sum / (prior_weight + evidence_weight_sum)`

### `record_interaction_event(user_id, event_type, event_category, metadata, duration_ms, page_url, referrer_url, user_agent) → BIGINT`
Logs raw interaction event with privacy-preserving IP hashing.

---

## Triggers

| Trigger | Table | Timing | Action |
|---------|-------|--------|--------|
| `trg_update_last_activity` | `user_interaction_events` | AFTER INSERT | Updates `users.last_activity_date` |
| `trg_user_levels_updated` | `user_levels` | BEFORE UPDATE | Auto-sets `updated_at` |
| `trg_skill_taxonomy_updated` | `skill_taxonomy` | BEFORE UPDATE | Auto-sets `updated_at` |
| `trg_achievements_updated` | `achievements` | BEFORE UPDATE | Auto-sets `updated_at` |

---

## Migration Strategy

### Phase 1: Core Schema (This Migration)
```bash
# Apply migration
psql -d makesense -f gamification/migrations/001_gamification_schema.sql
```

### Phase 2: Seed Data (Separate Migration)
```sql
-- 002_seed_data.sql
INSERT INTO skill_taxonomy (skill_tag, display_name, category, difficulty) VALUES
    ('algebra-basics', 'Algebra Basics', 'mathematics', 2),
    ('geometry-fundamentals', 'Geometry Fundamentals', 'mathematics', 2),
    ('python-basics', 'Python Basics', 'programming', 2),
    ('data-structures', 'Data Structures', 'programming', 3),
    ('english-grammar', 'English Grammar', 'language', 2),
    ('scientific-method', 'Scientific Method', 'science', 2);

INSERT INTO achievements (code, name, description, icon, category, criteria_json, xp_reward) VALUES
    ('first_steps', 'First Steps', 'Complete your first lesson', '👶', 'progress',
     '{"metric": "lessons_completed", "operator": ">=", "value": 1}', 50),
    ('week_warrior', 'Week Warrior', '7-day login streak', '📅', 'streak',
     '{"metric": "current_streak", "operator": ">=", "value": 7}', 200),
    ('helpful_peer', 'Helpful Peer', 'Help 10 other users', '𤝣', 'social',
     '{"metric": "helpful_votes_received", "operator": ">=", "value": 10}', 300);
```

### Phase 3: Partition Maintenance (Ongoing)
```sql
-- Monthly partition creation (automate via pg_partman or cron)
CREATE TABLE user_interaction_events_2026_10 PARTITION OF user_interaction_events
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');

-- Drop old partitions after retention period (e.g., 13 months)
DROP TABLE user_interaction_events_2025_09;
```

### Phase 4: RLS Policies (When Multi-tenant)
Enable Row Level Security when deploying multi-tenant:
```sql
ALTER TABLE engagement_points ENABLE ROW LEVEL SECURITY;
-- ... policies as shown in migration
```

---

## Query Patterns & Performance

### Leaderboard Queries (Optimized)
```sql
-- Top 100 by XP (uses leaderboard_xp view / idx_engagement_points_positive)
SELECT * FROM leaderboard_xp LIMIT 100;

-- Top 10 by skill (uses leaderboard_skill view / idx_user_skill_ratings_score)
SELECT * FROM leaderboard_skill WHERE skill_tag = 'python-basics' LIMIT 10;
```

### User Profile (Single Query)
```sql
-- Uses user_gamification_summary view (joins users, user_levels, skill ratings, achievements)
SELECT * FROM user_gamification_summary WHERE user_id = $1;
```

### Skill Progress (User's Skills)
```sql
-- Uses idx_user_skill_ratings_user + idx_user_skill_ratings_score
SELECT skill_tag, proficiency_score, evidence_count, confidence
FROM user_skill_ratings
WHERE user_id = $1
ORDER BY proficiency_score DESC;
```

### Event Analytics (Time-Series)
```sql
-- Uses partitioning + idx_user_interaction_events_created
SELECT date_trunc('day', created_at) AS day, event_type, COUNT(*)
FROM user_interaction_events
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY day, event_type
ORDER BY day DESC;
```

---

## API Integration Points

### Points Awarding (Server-Side)
```python
# Python example using award_engagement_points function
async def award_points(user_id: int, source: str, points: int, **metadata):
    result = await db.fetchval("""
        SELECT award_engagement_points($1, $2, $3, $4, $5, $6)
    """, user_id, points, source, metadata.get('source_id'), json.dumps(metadata), metadata.get('description'))
    return result
```

### Skill Update (On Question Answer)
```python
async def record_answer(user_id: int, skill_tags: list[str], correct: bool, difficulty: float = 1.0):
    score = 100 if correct else 0
    for tag in skill_tags:
        await db.execute("SELECT update_skill_rating($1, $2, $3, $4)",
                         user_id, tag, score, difficulty)
```

### Interaction Logging (Middleware)
```python
async def log_interaction(request, user_id: int, event_type: str, category: str, **metadata):
    await db.execute("SELECT record_interaction_event($1, $2, $3, $4, $5, $6, $7, $8)",
                     user_id, event_type, category, json.dumps(metadata),
                     metadata.get('duration_ms'), str(request.url),
                     request.headers.get('referer'), request.headers.get('user-agent'))
```

---

## Retention & Privacy

| Table | Retention | Notes |
|-------|-----------|-------|
| `user_interaction_events` | 13 months | Monthly partitions, auto-drop old |
| `engagement_points` | Permanent | Financial/legal audit trail |
| `user_skill_ratings` | Permanent | Core user profile |
| `user_achievements` | Permanent | User history |
| `users` (gamification fields) | Permanent | Core profile |

**Privacy:**
- IP addresses hashed via `md5(random() || timestamp)` - not reversible
- No PII in `metadata` JSONB (enforce at application layer)
- RLS policies for multi-tenant isolation

---

## Monitoring & Alerts

### Key Metrics to Track
1. **Points Inflation** - `SUM(points) / COUNT(DISTINCT user_id)` over time
2. **Level Distribution** - `COUNT(*) GROUP BY current_level`
3. **Skill Coverage** - `COUNT(DISTINCT skill_tag) / COUNT(*) FROM skill_taxonomy WHERE is_active`
4. **Event Volume** - Daily `INSERT` count on `user_interaction_events`
5. **Achievement Unlock Rate** - New `user_achievements` per day

### Recommended Alerts
- `engagement_points` insert rate drops >50% (pipeline issue)
- `user_interaction_events` partition creation fails
- Level distribution heavily skewed (balance issue)
- Skill ratings not updating (cron job failure)

---

## Future Extensions

1. **Seasonal/Ranked Tiers** - Add `season_id` to leaderboards
2. **Team/Guild System** - `user_teams`, `team_achievements`
3. **Marketplace** - Spend points on cosmetics (`user_inventory`, `shop_items`)
4. **Quest System** - `quests`, `user_quest_progress` (daily/weekly objectives)
5. **Social Features** - `user_follows`, `activity_feed` (materialized view)

---

## File Locations

| File | Purpose |
|------|---------|
| `gamification/migrations/001_gamification_schema.sql` | Core schema migration |
| `gamification/migrations/002_seed_data.sql` | Reference data (skills, achievements) |
| `gamification/skills.py` | Skill rating algorithm (Python) |
| `gamification/api.py` | FastAPI routes for gamification |
| `gamification/jobs/nightly_skill_update.py` | Cron job for skill recalculation |

---

*Generated: 2026-09-19 | Version: 1.0 | Schema: gamification v1*