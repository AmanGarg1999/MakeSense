import sys
from pathlib import Path

# Make the repo importable for pytest without PYTHONPATH gymnastics
# (rootdir may not be sys.path[0] when invoked from elsewhere).
sys.path.insert(0, str(Path(__file__).parent))
