from core.cache_manager import CacheManager
from core.safe_logger import log_event
from sports.football_fixtures import load_sample_fixtures
from sports.football_pre_match import build_pre_match_snapshot
from sports.football_analyzer import analyze_match
from sports.football_recommender import build_recommendations


def main():
    cache = CacheManager()
    fixtures = load_sample_fixtures()
    recommendations = []

    for fixture in fixtures:
        snapshot = build_pre_match_snapshot(fixture, cache, use_slow_api=True)
        analysis = analyze_match(fixture, snapshot)
        rec = build_recommendations(fixture, snapshot, analysis)
        if rec:
            recommendations.append(rec)

    cache.set("pre_match", "latest_recommendations", recommendations)
    log_event("pre_match_collect", {"fixtures": len(fixtures), "recommendations": len(recommendations)})
    print(f"pre_match_collect ok: {len(recommendations)} recommendations")


if __name__ == "__main__":
    main()
