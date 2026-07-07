import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import AppConfig
from core.cache_manager import CacheManager
from core.safe_logger import log_event
from sports.football_fixtures import load_sample_fixtures
from sports.football_pre_match import build_pre_match_snapshot
from sports.football_analyzer import analyze_match
from sports.football_recommender import build_recommendations
from sports.analysis_transparency import build_collection_status, build_score_breakdown_from_analysis, package_raw_data

def main():
    config = AppConfig.from_env()
    cache = CacheManager()
    fixtures = load_sample_fixtures()
    snapshots, analyses, recommendations, scores = [], [], [], []
    for fixture in fixtures:
        snapshot = build_pre_match_snapshot(fixture, cache=cache, use_slow_api=config.use_slow_api)
        analysis = analyze_match(fixture, snapshot)
        rec = build_recommendations(fixture, snapshot, analysis)
        snapshots.append(snapshot)
        analyses.append(analysis)
        if rec:
            recommendations.append(rec)
        scores.extend(build_score_breakdown_from_analysis(fixture, snapshot, analysis))

    status = build_collection_status(
        fixture_count=len(fixtures),
        has_sports_api=bool(config.sports_api_key),
        has_odds_api=bool(config.odds_api_key),
        has_weather_api=bool(config.weather_api_key),
        sheet_enabled=bool(config.gas_webapp_url),
    )
    cache.set("collection_status", "latest", status)
    cache.set("raw_data", "latest", package_raw_data(fixtures, recommendations))
    cache.set("score_breakdown", "latest", scores)
    log_event("data_visible_collect", {"fixtures": len(fixtures), "recommendations": len(recommendations), "score_rows": len(scores)})
    print(f"data_visible_collect ok: fixtures={len(fixtures)}, recs={len(recommendations)}, scores={len(scores)}")

if __name__ == "__main__":
    main()
