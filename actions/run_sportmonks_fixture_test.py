import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sports.sportmonks_client import fetch_sportmonks_fixtures


def main():
    fixtures, info = fetch_sportmonks_fixtures()
    print("SPORTMONKS_INFO=", info)
    print("FIXTURE_COUNT=", len(fixtures))
    for row in fixtures[:5]:
        print(row)


if __name__ == "__main__":
    main()
