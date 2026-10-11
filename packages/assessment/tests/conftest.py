"""Test fixtures: make the repo root importable + provide a fresh registry."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from packages.assessment.registry import VerificationRegistry  # noqa: E402


@pytest.fixture()
def registry():
    r = VerificationRegistry(":memory:")
    yield r
    r.close()
