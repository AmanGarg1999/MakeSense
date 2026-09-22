#!/usr/bin/env python3
"""
Simple test script to verify the gamification engine core functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from gamification.engine import PointsRules, LevelThresholds, GamificationEngine
from unittest.mock import AsyncMock, Mock
import asyncio

def test_points_rules():
    print("Testing PointsRules...")
    rules = PointsRules()
    
    # Test default values
    assert rules.get_points("course_completion") == 100, f"Expected 100, got {rules.get_points('course_completion')}"
    assert rules.get_points("lesson_completion") == 20, f"Expected 20, got {rules.get_points('lesson_completion')}"
    assert rules.get_points("question_answer_correct") == 10, f"Expected 10, got {rules.get_points('question_answer_correct')}"
    assert rules.get_points("question_answer_incorrect") == 5, f"Expected 5, got {rules.get_points('question_answer_incorrect')}"
    assert rules.get_points("streak_bonus") == 50, f"Expected 50, got {rules.get_points('streak_bonus')}"
    assert rules.get_points("daily_login") == 5, f"Expected 5, got {rules.get_points('daily_login')}"
    assert rules.get_points("peer_help") == 15, f"Expected 15, got {rules.get_points('peer_help')}"
    assert rules.get_points("content_contribution") == 25, f"Expected 25, got {rules.get_points('content_contribution')}"
    assert rules.get_points("review_completion") == 15, f"Expected 15, got {rules.get_points('review_completion')}"
    assert rules.get_points("unknown_event") == 0, f"Expected 0, got {rules.get_points('unknown_event')}"
    
    # Test adding a rule
    rules.add_rule("new_event", 75)
    assert rules.get_points("new_event") == 75, f"Expected 75, got {rules.get_points('new_event')}"
    
    # Test updating a rule
    rules.add_rule("course_completion", 150)
    assert rules.get_points("course_completion") == 150, f"Expected 150, got {rules.get_points('course_completion')}"
    
    # Test removing a rule
    rules.remove_rule("lesson_completion")
    assert rules.get_points("lesson_completion") == 0, f"Expected 0, got {rules.get_points('lesson_completion')}"
    
    print("✓ PointsRules tests passed")

def test_level_thresholds():
    print("Testing LevelThresholds...")
    thresholds = LevelThresholds()
    
    # Test level progression based on the database schema
    # Level 1: 0-99 XP (threshold 0, to next 100)
    # Level 2: 100-349 XP (threshold 100, to next 250) 
    # Level 3: 350-849 XP (threshold 350, to next 500)
    # Level 4: 850-1849 XP (threshold 850, to next 1000)
    # Level 5: 1850-3849 XP (threshold 1850, to next 2000)
    # Level 6: 3850-6849 XP (threshold 3850, to next 3000)
    # Level 7: 6850-11849 XP (threshold 6850, to next 5000)
    # Level 8: 11850+ XP (threshold 11850, to next 10000)
    
    assert thresholds.get_level_from_xp(0) == 1, f"Expected level 1 for 0 XP, got {thresholds.get_level_from_xp(0)}"
    assert thresholds.get_level_from_xp(50) == 1, f"Expected level 1 for 50 XP, got {thresholds.get_level_from_xp(50)}"
    assert thresholds.get_level_from_xp(99) == 1, f"Expected level 1 for 99 XP, got {thresholds.get_level_from_xp(99)}"
    assert thresholds.get_level_from_xp(100) == 2, f"Expected level 2 for 100 XP, got {thresholds.get_level_from_xp(100)}"
    assert thresholds.get_level_from_xp(150) == 2, f"Expected level 2 for 150 XP, got {thresholds.get_level_from_xp(150)}"
    assert thresholds.get_level_from_xp(200) == 2, f"Expected level 2 for 200 XP, got {thresholds.get_level_from_xp(200)}"
    assert thresholds.get_level_from_xp(250) == 2, f"Expected level 2 for 250 XP, got {thresholds.get_level_from_xp(250)}"
    assert thresholds.get_level_from_xp(349) == 2, f"Expected level 2 for 349 XP, got {thresholds.get_level_from_xp(349)}"
    assert thresholds.get_level_from_xp(350) == 3, f"Expected level 3 for 350 XP, got {thresholds.get_level_from_xp(350)}"
    assert thresholds.get_level_from_xp(400) == 3, f"Expected level 3 for 400 XP, got {thresholds.get_level_from_xp(400)}"
    assert thresholds.get_level_from_xp(500) == 3, f"Expected level 3 for 500 XP, got {thresholds.get_level_from_xp(500)}"
    assert thresholds.get_level_from_xp(600) == 3, f"Expected level 3 for 600 XP, got {thresholds.get_level_from_xp(600)}"
    assert thresholds.get_level_from_xp(849) == 3, f"Expected level 3 for 849 XP, got {thresholds.get_level_from_xp(849)}"
    assert thresholds.get_level_from_xp(850) == 4, f"Expected level 4 for 850 XP, got {thresholds.get_level_from_xp(850)}"
    assert thresholds.get_level_from_xp(900) == 4, f"Expected level 4 for 900 XP, got {thresholds.get_level_from_xp(900)}"
    assert thresholds.get_level_from_xp(1000) == 4, f"Expected level 4 for 1000 XP, got {thresholds.get_level_from_xp(1000)}"
    assert thresholds.get_level_from_xp(1100) == 4, f"Expected level 4 for 1100 XP, got {thresholds.get_level_from_xp(1100)}"
    assert thresholds.get_level_from_xp(1849) == 4, f"Expected level 4 for 1849 XP, got {thresholds.get_level_from_xp(1849)}"
    assert thresholds.get_level_from_xp(1850) == 5, f"Expected level 5 for 1850 XP, got {thresholds.get_level_from_xp(1850)}"
    assert thresholds.get_level_from_xp(2000) == 5, f"Expected level 5 for 2000 XP, got {thresholds.get_level_from_xp(2000)}"
    assert thresholds.get_level_from_xp(2500) == 5, f"Expected level 5 for 2500 XP, got {thresholds.get_level_from_xp(2500)}"
    assert thresholds.get_level_from_xp(3000) == 5, f"Expected level 5 for 3000 XP, got {thresholds.get_level_from_xp(3000)}"
    assert thresholds.get_level_from_xp(3500) == 5, f"Expected level 5 for 3500 XP, got {thresholds.get_level_from_xp(3500)}"
    assert thresholds.get_level_from_xp(3849) == 5, f"Expected level 5 for 3849 XP, got {thresholds.get_level_from_xp(3849)}"
    assert thresholds.get_level_from_xp(3850) == 6, f"Expected level 6 for 3850 XP, got {thresholds.get_level_from_xp(3850)}"
    assert thresholds.get_level_from_xp(4000) == 6, f"Expected level 6 for 4000 XP, got {thresholds.get_level_from_xp(4000)}"
    assert thresholds.get_level_from_xp(5000) == 6, f"Expected level 6 for 5000 XP, got {thresholds.get_level_from_xp(5000)}"
    assert thresholds.get_level_from_xp(6000) == 6, f"Expected level 6 for 6000 XP, got {thresholds.get_level_from_xp(6000)}"
    assert thresholds.get_level_from_xp(6849) == 6, f"Expected level 6 for 6849 XP, got {thresholds.get_level_from_xp(6849)}"
    assert thresholds.get_level_from_xp(6850) == 7, f"Expected level 7 for 6850 XP, got {thresholds.get_level_from_xp(6850)}"
    assert thresholds.get_level_from_xp(7000) == 7, f"Expected level 7 for 7000 XP, got {thresholds.get_level_from_xp(7000)}"
    assert thresholds.get_level_from_xp(10000) == 7, f"Expected level 7 for 10000 XP, got {thresholds.get_level_from_xp(10000)}"
    assert thresholds.get_level_from_xp(11849) == 7, f"Expected level 7 for 11849 XP, got {thresholds.get_level_from_xp(11849)}"
    assert thresholds.get_level_from_xp(11850) == 8, f"Expected level 8 for 11850 XP, got {thresholds.get_level_from_xp(11850)}"
    assert thresholds.get_level_from_xp(12000) == 8, f"Expected level 8 for 12000 XP, got {thresholds.get_level_from_xp(12000)}"
    assert thresholds.get_level_from_xp(15000) == 8, f"Expected level 8 for 15000 XP, got {thresholds.get_level_from_xp(15000)}"
    assert thresholds.get_level_from_xp(20000) == 8, f"Expected level 8 for 20000 XP, got {thresholds.get_level_from_xp(20000)}"
    
    # Test level info
    info = thresholds.get_level_info(1)
    assert info is not None, "Level 1 info should not be None"
    level_name, xp_threshold, xp_to_next, badge_icon = info
    assert level_name == 'Novice', f"Expected 'Novice', got {level_name}"
    assert xp_threshold == 0, f"Expected 0, got {xp_threshold}"
    assert xp_to_next == 100, f"Expected 100, got {xp_to_next}"
    assert badge_icon == '🌱', f"Expected '🌱', got {badge_icon}"
    
    info = thresholds.get_level_info(5)
    assert info is not None, "Level 5 info should not be None"
    level_name, xp_threshold, xp_to_next, badge_icon = info
    assert level_name == 'Scholar', f"Expected 'Scholar', got {level_name}"
    assert xp_threshold == 1850, f"Expected 1850, got {xp_threshold}"
    assert xp_to_next == 2000, f"Expected 2000, got {xp_to_next}"
    assert badge_icon == '🎓', f"Expected '🎓', got {badge_icon}"
    
    info = thresholds.get_level_info(8)
    assert info is not None, "Level 8 info should not be None"
    level_name, xp_threshold, xp_to_next, badge_icon = info
    assert level_name == 'Grandmaster', f"Expected 'Grandmaster', got {level_name}"
    assert xp_threshold == 11850, f"Expected 11850, got {xp_threshold}"
    assert xp_to_next == 10000, f"Expected 10000, got {xp_to_next}"  # Fixed: was expecting 0
    assert badge_icon == '👑', f"Expected '👑', got {badge_icon}"
    
    # Test invalid levels
    assert thresholds.get_level_info(0) is None, f"Expected None for level 0, got {thresholds.get_level_info(0)}"
    assert thresholds.get_level_info(9) is None, f"Expected None for level 9, got {thresholds.get_level_info(9)}"
    
    # Test XP to next
    assert thresholds.get_xp_to_next(1) == 100, f"Expected 100 XP to next for level 1, got {thresholds.get_xp_to_next(1)}"
    assert thresholds.get_xp_to_next(2) == 250, f"Expected 250 XP to next for level 2, got {thresholds.get_xp_to_next(2)}"
    assert thresholds.get_xp_to_next(5) == 2000, f"Expected 2000 XP to next for level 5, got {thresholds.get_xp_to_next(5)}"
    assert thresholds.get_xp_to_next(8) == 10000, f"Expected 10000 XP to next for level 8, got {thresholds.get_xp_to_next(8)}"  # Fixed: was expecting 0
    
    print("✓ LevelThresholds tests passed")

async def test_gamification_engine_basic():
    print("Testing GamificationEngine basic structure...")
    # We won't test database functionality without a real DB, but we can test the initialization and helper methods
    engine = GamificationEngine("fake_dsn")
    assert engine.dsn == "fake_dsn"
    assert engine.pool is None
    assert isinstance(engine.points_rules, PointsRules)
    assert isinstance(engine.level_thresholds, LevelThresholds)
    
    # Test the event type mapping
    assert engine._event_type_mapping["lesson_complete"] == "lesson_completion"
    assert engine._event_type_mapping["streak_milestone"] == "streak_bonus"
    assert engine._event_type_mapping["question_submit"] is None  # Special handling
    
    print("✓ GamificationEngine basic structure tests passed")

def test_load_points_rules():
    print("Testing load_points_rules function...")
    from gamification.engine import load_points_rules
    
    # Test with non-existent file (should return defaults)
    rules = load_points_rules("non_existent_file.yaml")
    assert rules.get_points("course_completion") == 100
    assert rules.get_points("lesson_completion") == 20
    assert rules.get_points("unknown_event") == 0
    
    print("✓ load_points_rules tests passed")

async def main():
    print("Running core functionality tests for Gamification Engine...\n")
    
    test_points_rules()
    test_level_thresholds()
    await test_gamification_engine_basic()
    test_load_points_rules()
    
    print("\n✅ All core tests passed!")

if __name__ == "__main__":
    asyncio.run(main())