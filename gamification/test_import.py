#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from gamification.engine import PointsRules, LevelThresholds
    print("SUCCESS: Imported PointsRules and LevelThresholds")
    rules = PointsRules()
    print(f"course_completion points: {rules.get_points('course_completion')}")
    thresholds = LevelThresholds()
    print(f"Level for 150 XP: {thresholds.get_level_from_xp(150)}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()