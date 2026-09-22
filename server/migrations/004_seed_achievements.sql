-- 004_seed_achievements.sql
INSERT INTO achievements (code, name, description, icon, category, criteria_json, xp_reward, is_hidden) VALUES
('first_lesson', 'First Steps', 'Complete your first lesson', '🌱', 'progress', '{"metric": "lessons_completed", "operator": ">=", "value": 1}', 25, false),
('quiz_ace', 'Perfect Score', 'Score 100% on any quiz', '💯', 'mastery', '{"metric": "perfect_scores", "operator": ">=", "value": 1}', 50, false),
('streak_7', 'Weekly Warrior', 'Maintain a 7-day streak', '🔥', 'streak', '{"metric": "current_streak", "operator": ">=", "value": 7}', 100, false),
('streak_30', 'Monthly Master', 'Maintain a 30-day streak', '🌟', 'streak', '{"metric": "current_streak", "operator": ">=", "value": 30}', 500, false),
('five_lessons', 'Getting Serious', 'Complete 5 lessons', '📖', 'progress', '{"metric": "lessons_completed", "operator": ">=", "value": 5}', 75, false),
('ten_lessons', 'Knowledge Seeker', 'Complete 10 lessons', '📚', 'progress', '{"metric": "lessons_completed", "operator": ">=", "value": 10}', 150, false),
('xp_500', 'Rising Star', 'Earn 500 XP total', '⭐', 'progress', '{"metric": "total_xp", "operator": ">=", "value": 500}', 50, false),
('xp_2000', 'XP Machine', 'Earn 2000 XP total', '🚀', 'progress', '{"metric": "total_xp", "operator": ">=", "value": 2000}', 100, false),
('multi_domain', 'Renaissance Mind', 'Study 3+ different categories', '🎨', 'mastery', '{"metric": "unique_categories", "operator": ">=", "value": 3}', 150, false),
('night_owl', 'Night Owl', 'Complete a lesson after midnight', '🦉', 'special', '{"metric": "quiz_time", "operator": "in", "value": "night"}', 25, true),
('comeback', 'Phoenix Rising', 'Return after 7+ day absence', '🔥', 'special', '{"metric": "comeback_days", "operator": ">=", "value": 7}', 75, true)
ON CONFLICT (code) DO NOTHING;
