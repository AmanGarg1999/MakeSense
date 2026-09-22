"""Prompt templates for content generation."""
# The main lesson prompt is defined in server/content_generator.py
# This module can be extended with additional prompt templates

QUIZ_GRADING_PROMPT = """Grade the following short answer response.

Question: {question}
Expected Answer: {expected_answer}
Student Answer: {student_answer}

Respond with JSON: {{"is_correct": true/false, "feedback": "brief feedback"}}"""
