import sys
from pathlib import Path

# Ensure pi/ is on sys.path so imports work from tests/
sys.path.insert(0, str(Path(__file__).parent.parent))
