import sys
from pathlib import Path

# Ensure the repository root is on the Python path so "backend" can be
# imported regardless of where the tests are executed from.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
