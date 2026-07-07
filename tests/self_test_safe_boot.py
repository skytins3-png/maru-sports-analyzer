import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sports.sportmonks_client import run_diagnostic_test, fetch_sportmonks_fixtures, get_last_collection_info
from sports.football_fixtures import load_sample_fixtures

rows = load_sample_fixtures()
assert rows and rows[0]["data_source"] == "sample_safe_boot", rows
assert callable(run_diagnostic_test)
assert callable(fetch_sportmonks_fixtures)
assert isinstance(get_last_collection_info(), dict)

print("SAFE_BOOT_SELF_TEST_OK")
