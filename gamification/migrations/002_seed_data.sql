-- Gamification Seed Data Migration
-- Version: 1.0
-- Created: 2026-09-19
-- Description: Reference data for skills, achievements, and initial configuration

-- ============================================================================
-- Skill Taxonomy - CBSE/NCERT Aligned Skills
-- ============================================================================

INSERT INTO skill_taxonomy (skill_tag, display_name, description, category, difficulty, is_active) VALUES
-- Mathematics
('number-systems', 'Number Systems', 'Understanding real numbers, rational/irrational numbers, decimal expansions', 'mathematics', 2, TRUE),
('polynomials', 'Polynomials', 'Polynomial expressions, zeroes, factorization, algebraic identities', 'mathematics', 3, TRUE),
('coordinate-geometry', 'Coordinate Geometry', 'Cartesian plane, distance formula, section formula, area of triangles', 'mathematics', 2, TRUE),
('linear-equations', 'Linear Equations in Two Variables', 'Graphical and algebraic solutions, consistency, applications', 'mathematics', 2, TRUE),
('euclid-geometry', 'Introduction to Euclid''s Geometry', 'Axioms, postulates, theorems, geometric proofs', 'mathematics', 2, TRUE),
('lines-angles', 'Lines and Angles', 'Angle properties, parallel lines, transversal, triangle angle sum', 'mathematics', 2, TRUE),
('triangles', 'Triangles', 'Congruence criteria, inequalities, properties, similarity', 'mathematics', 3, TRUE),
('quadrilaterals', 'Quadrilaterals', 'Properties of parallelograms, rectangles, squares, rhombus, trapezium', 'mathematics', 3, TRUE),
('areas-parallelograms', 'Areas of Parallelograms and Triangles', 'Area theorems, figures on same base and between same parallels', 'mathematics', 2, TRUE),
('circles', 'Circles', 'Circle theorems, chords, arcs, cyclic quadrilaterals', 'mathematics', 3, TRUE),
('constructions', 'Geometric Constructions', 'Bisectors, perpendicular lines, triangle constructions', 'mathematics', 2, TRUE),
('heron-formula', 'Heron''s Formula', 'Area of triangles using semiperimeter, applications to quadrilaterals', 'mathematics', 2, TRUE),
('surface-areas-volumes', 'Surface Areas and Volumes', 'Cubes, cuboids, cylinders, cones, spheres, combinations', 'mathematics', 3, TRUE),
('statistics', 'Statistics', 'Data collection, presentation, mean, median, mode, grouped data', 'mathematics', 2, TRUE),
('probability', 'Probability', 'Experimental probability, theoretical probability, simple events', 'mathematics', 2, TRUE),

-- Science - Physics
('motion', 'Motion', 'Distance, displacement, speed, velocity, acceleration, graphs', 'physics', 2, TRUE),
('force-laws', 'Force and Laws of Motion', 'Newton''s laws, inertia, momentum, conservation laws', 'physics', 3, TRUE),
('gravitation', 'Gravitation', 'Universal law, free fall, mass vs weight, thrust, pressure', 'physics', 3, TRUE),
('work-energy', 'Work and Energy', 'Work, kinetic/potential energy, power, conservation of energy', 'physics', 3, TRUE),
('sound', 'Sound', 'Production, propagation, characteristics, reflection, ultrasound', 'physics', 2, TRUE),

-- Science - Chemistry
('matter-surroundings', 'Matter in Our Surroundings', 'States of matter, interconversion, evaporation, latent heat', 'chemistry', 2, TRUE),
('pure-matter', 'Is Matter Around Us Pure', 'Mixtures, solutions, separation techniques, physical/chemical changes', 'chemistry', 2, TRUE),
('atoms-molecules', 'Atoms and Molecules', 'Laws of combination, atomic/molecular mass, mole concept', 'chemistry', 3, TRUE),
('atom-structure', 'Structure of the Atom', 'Subatomic particles, models, isotopes, electronic configuration', 'chemistry', 3, TRUE),

-- Science - Biology
('fundamental-unit', 'The Fundamental Unit of Life', 'Cell structure, organelles, plant vs animal cells, cell division', 'biology', 2, TRUE),
('tissues', 'Tissues', 'Plant and animal tissues, types, functions', 'biology', 2, TRUE),
('diversity-organisms', 'Diversity in Living Organisms', 'Classification, hierarchy, major groups, nomenclature', 'biology', 2, TRUE),
('why-ill', 'Why Do We Fall Ill', 'Health, diseases, pathogens, immunity, prevention', 'biology', 2, TRUE),
('natural-resources', 'Natural Resources', 'Air, water, soil, biogeochemical cycles, ozone layer', 'biology', 2, TRUE),
('food-resources', 'Improvement in Food Resources', 'Crop production, animal husbandry, fisheries, sustainable practices', 'biology', 2, TRUE),

-- English
('reading-comprehension', 'Reading Comprehension', 'Understanding passages, inference, vocabulary in context', 'english', 2, TRUE),
('grammar-tenses', 'Grammar - Tenses', 'Present, past, future forms, perfect, continuous, perfect continuous', 'english', 2, TRUE),
('grammar-modals', 'Grammar - Modals', 'Can, could, may, might, must, should, ought to, would', 'english', 2, TRUE),
('grammar-voice', 'Grammar - Active and Passive Voice', 'Transformation, usage, appropriate contexts', 'english', 3, TRUE),
('grammar-speech', 'Grammar - Direct and Indirect Speech', 'Reporting statements, questions, commands, tense changes', 'english', 3, TRUE),
('grammar-clauses', 'Grammar - Clauses', 'Noun, adjective, adverb clauses, subordinating conjunctions', 'english', 3, TRUE),
('writing-skills', 'Writing Skills', 'Letters, emails, articles, speeches, reports, stories', 'english', 3, TRUE),
('literature-prose', 'Literature - Prose', 'Understanding themes, characters, plot, literary devices', 'english', 2, TRUE),
('literature-poetry', 'Literature - Poetry', 'Poetic devices, themes, imagery, rhythm, rhyme', 'english', 2, TRUE),

-- Social Science - History
('french-revolution', 'The French Revolution', 'Causes, events, impact, legacy, Napoleon', 'history', 2, TRUE),
('socialism-europe', 'Socialism in Europe and Russian Revolution', 'Ideologies, 1905/1917 revolutions, USSR formation', 'history', 2, TRUE),
('nazism-hitler', 'Nazism and Rise of Hitler', 'Weimar Republic, Nazi ideology, WWII, Holocaust', 'history', 2, TRUE),
('forest-society', 'Forest Society and Colonialism', 'Deforestation, colonial policies, tribal movements', 'history', 2, TRUE),
('pastoralists', 'Pastoralists in the Modern World', 'Nomadic communities, colonial impact, modern challenges', 'history', 2, TRUE),

-- Social Science - Geography
('india-size-location', 'India - Size and Location', 'Latitude/longitude, neighbors, time zones, strategic importance', 'geography', 1, TRUE),
('physical-features', 'Physical Features of India', 'Himalayas, plains, plateau, coasts, islands', 'geography', 2, TRUE),
('drainage', 'Drainage', 'Himalayan vs Peninsular rivers, lakes, river pollution', 'geography', 2, TRUE),
('climate', 'Climate', 'Monsoon mechanism, seasons, distribution, climate change', 'geography', 2, TRUE),
('natural-vegetation', 'Natural Vegetation and Wildlife', 'Forest types, wildlife, conservation, biosphere reserves', 'geography', 2, TRUE),
('population', 'Population', 'Size, distribution, growth, density, composition, policy', 'geography', 2, TRUE),

-- Social Science - Political Science
('democracy-what', 'What is Democracy? Why Democracy?', 'Features, merits/demerits, broader meaning', 'political-science', 2, TRUE),
('constitutional-design', 'Constitutional Design', 'Need, making, guiding values, preamble', 'political-science', 2, TRUE),
('electoral-politics', 'Electoral Politics', 'Elections, constituencies, parties, campaign, reform', 'political-science', 2, TRUE),
('working-institutions', 'Working of Institutions', 'Parliament, executive, judiciary, relations', 'political-science', 2, TRUE),
('democratic-rights', 'Democratic Rights', 'Fundamental rights, judiciary role, expanding scope', 'political-science', 2, TRUE),

-- Social Science - Economics
('village-palamur', 'The Story of Village Palampur', 'Factors of production, farming, non-farm activities', 'economics', 2, TRUE),
('people-resource', 'People as Resource', 'Human capital, education, health, unemployment', 'economics', 2, TRUE),
('poverty-challenge', 'Poverty as a Challenge', 'Poverty line, estimates, vulnerable groups, anti-poverty measures', 'economics', 2, TRUE),
('food-security', 'Food Security in India', 'Buffer stock, PDS, cooperatives, current status', 'economics', 2, TRUE),

-- Programming / Computational Thinking
('algorithmic-thinking', 'Algorithmic Thinking', 'Problem decomposition, pattern recognition, abstraction, algorithms', 'programming', 2, TRUE),
('python-basics', 'Python Basics', 'Variables, data types, operators, control flow, functions', 'programming', 2, TRUE),
('data-structures-intro', 'Introduction to Data Structures', 'Lists, tuples, dictionaries, sets, basic operations', 'programming', 3, TRUE),
('file-handling', 'File Handling', 'Reading/writing text/binary files, CSV, JSON, context managers', 'programming', 3, TRUE),
('libraries-intro', 'Introduction to Python Libraries', 'NumPy, pandas, matplotlib basics for data science', 'programming', 4, TRUE),

-- General Skills
('critical-thinking', 'Critical Thinking', 'Analysis, evaluation, inference, explanation, self-regulation', 'general', 3, TRUE),
('problem-solving', 'Problem Solving', 'Define, plan, execute, review, iterate', 'general', 3, TRUE),
('collaboration', 'Collaboration', 'Communication, teamwork, conflict resolution, shared goals', 'general', 2, TRUE),
('communication', 'Communication', 'Verbal, written, visual, active listening, presentation', 'general', 2, TRUE),
('creativity', 'Creativity', 'Ideation, divergent thinking, innovation, design thinking', 'general', 3, TRUE),
('digital-literacy', 'Digital Literacy', 'Information literacy, media literacy, cyber safety, ethics', 'general', 2, TRUE)

ON CONFLICT (skill_tag) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    difficulty = EXCLUDED.difficulty,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();


-- ============================================================================
-- Parent Skill Categories
-- ============================================================================

INSERT INTO skill_taxonomy (skill_tag, display_name, description, category, difficulty, is_active) VALUES
('algebra-basics', 'Algebra Fundamentals', 'Core algebra concepts and operations', 'mathematics', 1, TRUE),
('geometry-basics', 'Geometry Fundamentals', 'Foundations of geometric shapes and proofs', 'mathematics', 1, TRUE),
('statistics-probability', 'Statistics & Probability', 'Data analysis and probability theory', 'mathematics', 1, TRUE),
('mechanics', 'Classical Mechanics', 'Forces, motion, and energy', 'physics', 1, TRUE),
('waves', 'Waves & Sound', 'Wave propagation and acoustics', 'physics', 1, TRUE),
('matter', 'Matter & Materials', 'States and structure of matter', 'chemistry', 1, TRUE),
('cell-biology', 'Cell Biology', 'Cellular structures and tissues', 'biology', 1, TRUE),
('ecology', 'Ecology & Environment', 'Living systems and natural resources', 'biology', 1, TRUE),
('health', 'Health & Medicine', 'Human health, disease, and prevention', 'biology', 1, TRUE),
('agriculture', 'Agricultural Sciences', 'Crop and animal resources', 'biology', 1, TRUE),
('grammar', 'English Grammar', 'Grammar and language mechanics', 'english', 1, TRUE),
('literature', 'English Literature', 'Reading and analyzing literary texts', 'english', 1, TRUE),
('writing', 'Writing Skills', 'Composition and communication', 'english', 1, TRUE),
('indian-history', 'World & Indian History', 'Historical movements and world revolutions', 'history', 1, TRUE),
('indian-geography', 'Geography & Demographics', 'Physical geography and population', 'geography', 1, TRUE),
('indian-polity', 'Civics & Political Science', 'Democracy, institutions, and rights', 'polity', 1, TRUE),
('indian-economy', 'Economics & Development', 'Economic structures and human resources', 'economics', 1, TRUE)
ON CONFLICT (skill_tag) DO NOTHING;

-- ============================================================================
-- Skill Hierarchy (Parent-Child Relationships)
-- ============================================================================

UPDATE skill_taxonomy SET parent_tag = 'algebra-basics' WHERE skill_tag IN ('polynomials', 'linear-equations');
UPDATE skill_taxonomy SET parent_tag = 'geometry-basics' WHERE skill_tag IN ('coordinate-geometry', 'euclid-geometry', 'lines-angles', 'triangles', 'quadrilaterals', 'circles', 'constructions');
UPDATE skill_taxonomy SET parent_tag = 'geometry-basics' WHERE skill_tag IN ('areas-parallelograms', 'heron-formula', 'surface-areas-volumes');
UPDATE skill_taxonomy SET parent_tag = 'statistics-probability' WHERE skill_tag IN ('statistics', 'probability');

UPDATE skill_taxonomy SET parent_tag = 'mechanics' WHERE skill_tag IN ('motion', 'force-laws', 'gravitation', 'work-energy');
UPDATE skill_taxonomy SET parent_tag = 'waves' WHERE skill_tag = 'sound';

UPDATE skill_taxonomy SET parent_tag = 'matter' WHERE skill_tag IN ('matter-surroundings', 'pure-matter', 'atoms-molecules', 'atom-structure');

UPDATE skill_taxonomy SET parent_tag = 'cell-biology' WHERE skill_tag IN ('fundamental-unit', 'tissues');
UPDATE skill_taxonomy SET parent_tag = 'ecology' WHERE skill_tag IN ('diversity-organisms', 'natural-resources');
UPDATE skill_taxonomy SET parent_tag = 'health' WHERE skill_tag = 'why-ill';
UPDATE skill_taxonomy SET parent_tag = 'agriculture' WHERE skill_tag = 'food-resources';

UPDATE skill_taxonomy SET parent_tag = 'grammar' WHERE skill_tag IN ('grammar-tenses', 'grammar-modals', 'grammar-voice', 'grammar-speech', 'grammar-clauses');
UPDATE skill_taxonomy SET parent_tag = 'literature' WHERE skill_tag IN ('literature-prose', 'literature-poetry');
UPDATE skill_taxonomy SET parent_tag = 'writing' WHERE skill_tag = 'writing-skills';

UPDATE skill_taxonomy SET parent_tag = 'indian-history' WHERE skill_tag IN ('french-revolution', 'socialism-europe', 'nazism-hitler', 'forest-society', 'pastoralists');
UPDATE skill_taxonomy SET parent_tag = 'indian-geography' WHERE skill_tag IN ('india-size-location', 'physical-features', 'drainage', 'climate', 'natural-vegetation', 'population');
UPDATE skill_taxonomy SET parent_tag = 'indian-polity' WHERE skill_tag IN ('democracy-what', 'constitutional-design', 'electoral-politics', 'working-institutions', 'democratic-rights');
UPDATE skill_taxonomy SET parent_tag = 'indian-economy' WHERE skill_tag IN ('village-palamur', 'people-resource', 'poverty-challenge', 'food-security');


-- ============================================================================
-- Achievements
-- ============================================================================

INSERT INTO achievements (code, name, description, icon, category, criteria_json, xp_reward, is_hidden, is_active) VALUES
-- Progress Achievements
('first-lesson', 'First Steps', 'Complete your very first lesson', '👶', 'progress',
 '{"metric": "lessons_completed", "operator": ">=", "value": 1}', 50, FALSE, TRUE),

('ten-lessons', 'Getting Started', 'Complete 10 lessons', '📖', 'progress',
 '{"metric": "lessons_completed", "operator": ">=", "value": 10}', 200, FALSE, TRUE),

('fifty-lessons', 'Dedicated Learner', 'Complete 50 lessons', '🎓', 'progress',
 '{"metric": "lessons_completed", "operator": ">=", "value": 50}', 500, FALSE, TRUE),

('hundred-lessons', 'Century Club', 'Complete 100 lessons', '💯', 'progress',
 '{"metric": "lessons_completed", "operator": ">=", "value": 100}', 1000, FALSE, TRUE),

('first-course', 'Course Completer', 'Complete your first full course', '🏁', 'progress',
 '{"metric": "courses_completed", "operator": ">=", "value": 1}', 300, FALSE, TRUE),

('five-courses', 'Polyglot', 'Complete 5 courses', '🌍', 'progress',
 '{"metric": "courses_completed", "operator": ">=", "value": 5}', 1000, FALSE, TRUE),

-- Streak Achievements
('streak-3', 'Three-Day Streak', 'Log in 3 days in a row', '🔥', 'streak',
 '{"metric": "current_streak", "operator": ">=", "value": 3}', 100, FALSE, TRUE),

('streak-7', 'Week Warrior', 'Log in 7 days in a row', '📅', 'streak',
 '{"metric": "current_streak", "operator": ">=", "value": 7}', 300, FALSE, TRUE),

('streak-30', 'Monthly Master', 'Log in 30 days in a row', '🗓️', 'streak',
 '{"metric": "current_streak", "operator": ">=", "value": 30}', 1000, FALSE, TRUE),

('streak-100', 'Centurion', 'Log in 100 days in a row', '💯', 'streak',
 '{"metric": "current_streak", "operator": ">=", "value": 100}', 5000, FALSE, TRUE),

('longest-streak-30', 'Consistency King', 'Achieve a 30-day longest streak', '👑', 'streak',
 '{"metric": "longest_streak", "operator": ">=", "value": 30}', 500, FALSE, TRUE),

-- Social Achievements
('first-help', 'Helping Hand', 'Help another user for the first time', '🤝', 'social',
 '{"metric": "helpful_votes_received", "operator": ">=", "value": 1}', 100, FALSE, TRUE),

('ten-helps', 'Community Hero', 'Receive 10 helpful votes', '🦸', 'social',
 '{"metric": "helpful_votes_received", "operator": ">=", "value": 10}', 500, FALSE, TRUE),

('fifty-helps', 'Mentor', 'Receive 50 helpful votes', '🧙', 'social',
 '{"metric": "helpful_votes_received", "operator": ">=", "value": 50}', 2000, FALSE, TRUE),

('first-question', 'Curious Mind', 'Ask your first question', '❓', 'social',
 '{"metric": "questions_asked", "operator": ">=", "value": 1}', 50, FALSE, TRUE),

('ten-answers', 'Answer Key', 'Provide 10 answers', '🔑', 'social',
 '{"metric": "answers_given", "operator": ">=", "value": 10}', 300, FALSE, TRUE),

-- Mastery Achievements
('skill-50', 'Skill Novice', 'Reach 50 proficiency in any skill', '🌱', 'mastery',
 '{"metric": "max_skill_score", "operator": ">=", "value": 50}', 200, FALSE, TRUE),

('skill-75', 'Skill Adept', 'Reach 75 proficiency in any skill', '🌿', 'mastery',
 '{"metric": "max_skill_score", "operator": ">=", "value": 75}', 500, FALSE, TRUE),

('skill-90', 'Skill Expert', 'Reach 90 proficiency in any skill', '🌳', 'mastery',
 '{"metric": "max_skill_score", "operator": ">=", "value": 90}', 1500, FALSE, TRUE),

('skill-100', 'Skill Master', 'Reach 100 proficiency in any skill', '💎', 'mastery',
 '{"metric": "max_skill_score", "operator": ">=", "value": 100}', 5000, FALSE, TRUE),

('five-skills-50', 'Renaissance Learner', 'Reach 50+ proficiency in 5 skills', '🎨', 'mastery',
 '{"metric": "skills_above_50", "operator": ">=", "value": 5}', 1000, FALSE, TRUE),

('ten-skills-50', 'Polymath', 'Reach 50+ proficiency in 10 skills', '🧠', 'mastery',
 '{"metric": "skills_above_50", "operator": ">=", "value": 10}', 3000, FALSE, TRUE),

-- Level Achievements
('level-2', 'Explorer', 'Reach Level 2 (Explorer)', '🧭', 'progress',
 '{"metric": "current_level", "operator": ">=", "value": 2}', 100, FALSE, TRUE),

('level-3', 'Learner', 'Reach Level 3 (Learner)', '📚', 'progress',
 '{"metric": "current_level", "operator": ">=", "value": 3}', 200, FALSE, TRUE),

('level-4', 'Practitioner', 'Reach Level 4 (Practitioner)', '⚡', 'progress',
 '{"metric": "current_level", "operator": ">=", "value": 4}', 500, FALSE, TRUE),

('level-5', 'Scholar', 'Reach Level 5 (Scholar)', '🎓', 'progress',
 '{"metric": "current_level", "operator": ">=", "value": 5}', 1000, FALSE, TRUE),

('level-6', 'Expert', 'Reach Level 6 (Expert)', '💎', 'progress',
 '{"metric": "current_level", "operator": ">=", "value": 6}', 2500, FALSE, TRUE),

('level-7', 'Master', 'Reach Level 7 (Master)', '🏆', 'progress',
 '{"metric": "current_level", "operator": ">=", "value": 7}', 5000, FALSE, TRUE),

('level-8', 'Grandmaster', 'Reach Level 8 (Grandmaster)', '👑', 'progress',
 '{"metric": "current_level", "operator": ">=", "value": 8}', 10000, FALSE, TRUE),

-- Special / Hidden Achievements
('night-owl', 'Night Owl', 'Complete a lesson between 12 AM - 5 AM', '🦉', 'special',
 '{"metric": "night_lesson_completed", "operator": ">=", "value": 1}', 200, TRUE, TRUE),

('early-bird', 'Early Bird', 'Complete a lesson between 5 AM - 7 AM', '🐦', 'special',
 '{"metric": "morning_lesson_completed", "operator": ">=", "value": 1}', 200, TRUE, TRUE),

('weekend-warrior', 'Weekend Warrior', 'Complete 5 lessons on a weekend', '⚔️', 'special',
 '{"metric": "weekend_lessons", "operator": ">=", "value": 5}', 300, TRUE, TRUE),

('perfect-score', 'Perfectionist', 'Score 100% on 5 assessments', '💯', 'special',
 '{"metric": "perfect_assessments", "operator": ">=", "value": 5}', 1000, TRUE, TRUE),

('referral-1', 'Ambassador', 'Refer 1 friend who completes a course', '📣', 'special',
 '{"metric": "successful_referrals", "operator": ">=", "value": 1}', 500, FALSE, TRUE),

('referral-5', 'Recruiter', 'Refer 5 friends who complete a course', '🎯', 'special',
 '{"metric": "successful_referrals", "operator": ">=", "value": 5}', 2000, FALSE, TRUE),

('beta-tester', 'Beta Tester', 'Participated in beta testing', '🧪', 'special',
 '{"metric": "beta_participant", "operator": ">=", "value": 1}', 1000, TRUE, TRUE),

('content-creator', 'Content Creator', 'Create content used by 100+ learners', '✍️', 'special',
 '{"metric": "content_views", "operator": ">=", "value": 100}', 2000, FALSE, TRUE)

ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    category = EXCLUDED.category,
    criteria_json = EXCLUDED.criteria_json,
    xp_reward = EXCLUDED.xp_reward,
    is_hidden = EXCLUDED.is_hidden,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();


-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Verify skill taxonomy
-- SELECT category, COUNT(*) as count FROM skill_taxonomy WHERE is_active GROUP BY category ORDER BY count DESC;

-- Verify achievements
-- SELECT category, COUNT(*) as count FROM achievements WHERE is_active GROUP BY category ORDER BY count DESC;

-- Verify level configuration
-- SELECT * FROM user_levels ORDER BY level_id;