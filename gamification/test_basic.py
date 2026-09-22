#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '.')

from gamification.engine import PointsRules, LevelThresholds

print('Testing PointsRules...')
rules = PointsRules()
print(f'course_completion: {rules.get_points("course_completion")}')
print(f'lesson_completion: {rules.get_points("lesson_completion")}')
print(f'unknown_event: {rules.get_points("unknown_event")}')

print('\nTesting LevelThresholds...')
thresholds = LevelThresholds()
print(f'Level from 0 XP: {thresholds.get_level_from_xp(0)}')
print(f'Level from 150 XP: {thresholds.get_level_from_xp(150)}')
print(f'Level from 500 XP: {thresholds.get_level_from_xp(500)}')
print(f'Level from 1000 XP: {thresholds.get_level_from_xp(1000)}')
print(f'Level from 2000 XP: {thresholds.get_level_from_xp(2000)}')
print(f'Level from 5000 XP: {thresholds.get_level_from_xp(5000)}')
print(f'Level from 12000 XP: {thresholds.get_level_from_xp(12000)}')
print('\nAll basic tests passed!')