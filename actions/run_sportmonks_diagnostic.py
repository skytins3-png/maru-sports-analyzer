import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from sports.sportmonks_client import run_diagnostic_test
print(run_diagnostic_test())
