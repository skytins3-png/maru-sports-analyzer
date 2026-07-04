import random


def build_pre_match_snapshot(fixture: dict, cache, use_slow_api: bool = True):
    """
    경기 전 변동자료:
    라인업, 부상, 결장, 징계, 날씨, 배당, 뉴스.
    실제 API 연결 전에는 안정적인 샘플값을 만든다.
    """
    match_id = fixture["match_id"]
    cached = cache.get("pre_match", match_id, max_age_seconds=60 * 30)
    if cached:
        return cached

    # 샘플 데이터. 나중에 실제 API 응답으로 교체.
    seed = sum(ord(c) for c in match_id)
    random.seed(seed)

    snapshot = {
        "match_id": match_id,
        "lineup_status": "probable",
        "home_recent_form": random.randint(45, 85),
        "away_recent_form": random.randint(40, 82),
        "home_attack": random.randint(45, 88),
        "away_attack": random.randint(40, 85),
        "home_defense": random.randint(42, 86),
        "away_defense": random.randint(40, 84),
        "home_injury_risk": random.randint(0, 35),
        "away_injury_risk": random.randint(0, 35),
        "odds_home_movement": round(random.uniform(-0.15, 0.18), 3),
        "odds_draw_movement": round(random.uniform(-0.08, 0.08), 3),
        "odds_away_movement": round(random.uniform(-0.15, 0.18), 3),
        "expected_total_goals": round(random.uniform(1.8, 3.4), 2),
        "weather_risk": random.randint(0, 20),
        "news_score": random.randint(40, 80) if use_slow_api else None,
        "slow_api_used": bool(use_slow_api),
    }

    cache.set("pre_match", match_id, snapshot)
    return snapshot
