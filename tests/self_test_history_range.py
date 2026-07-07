import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sports.sportmonks_client import (
    test_history_range,
    test_history_ranges,
    run_diagnostic_test,
    get_last_collection_info,
)
from sports.football_fixtures import load_sample_fixtures

rows = load_sample_fixtures()
assert rows and rows[0]["data_source"] == "sample_safe_boot"
assert callable(test_history_range)
assert callable(test_history_ranges)
assert callable(run_diagnostic_test)
assert isinstance(get_last_collection_info(), dict)

# No token 상태에서는 외부 호출 없이 안전 실패해야 함
r = test_history_range(1, timeout=1)
assert "fixtures_count" in r
assert "info" in r

print("HISTORY_RANGE_SELF_TEST_OK")
