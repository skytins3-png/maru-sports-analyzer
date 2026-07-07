from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.cache_manager import CacheManager
from core.safe_logger import log_event
from sports.live_score_engine import sample_live_rows, analyze_live_rows


def main():
    cache = CacheManager()
    rows = sample_live_rows()
    results = analyze_live_rows(rows)
    cache.set("live_score", "latest_live_recommendations", results)
    log_event("live_score_collect", {"rows": len(rows), "results": len(results)})
    print(f"live_score_collect ok: {len(results)} results")


if __name__ == "__main__":
    main()
