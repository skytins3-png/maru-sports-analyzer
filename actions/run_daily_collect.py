from datetime import datetime, timezone, timedelta
from core.cache_manager import CacheManager
from core.safe_logger import log_event
from sports.football_fixtures import load_sample_fixtures


KST = timezone(timedelta(hours=9))


def main():
    cache = CacheManager()
    fixtures = load_sample_fixtures()
    cache.set("static", "latest_fixtures", fixtures)
    log_event("daily_collect", {"count": len(fixtures), "time": datetime.now(KST).isoformat()})
    print(f"daily_collect ok: {len(fixtures)} fixtures")


if __name__ == "__main__":
    main()
