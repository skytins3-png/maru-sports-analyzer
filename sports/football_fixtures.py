from datetime import datetime, timezone, timedelta
from sports.sportmonks_client import fetch_sportmonks_fixtures, get_last_collection_info


KST = timezone(timedelta(hours=9))


def sample_fixtures():
    today = datetime.now(KST).strftime("%Y-%m-%d")
    return [
        {
            "match_id": f"{today}_EPL_001",
            "date": today,
            "league": "EPL",
            "match_no": "001",
            "home_team": "Manchester City",
            "away_team": "Chelsea",
            "kickoff_kst": f"{today} 23:00 KST",
            "status": "scheduled",
            "data_source": "sample",
        },
        {
            "match_id": f"{today}_KLEAGUE_002",
            "date": today,
            "league": "K LEAGUE",
            "match_no": "002",
            "home_team": "Ulsan HD",
            "away_team": "Jeonbuk Hyundai",
            "kickoff_kst": f"{today} 19:30 KST",
            "status": "scheduled",
            "data_source": "sample",
        },
    ]


def load_sample_fixtures():
    """
    기존 함수명 유지.
    1순위: Sportmonks 실제 경기 일정
    2순위: 실패/0건이면 샘플 경기 fallback
    """
    fixtures, info = fetch_sportmonks_fixtures()
    if fixtures:
        return fixtures
    rows = sample_fixtures()
    for r in rows:
        r["fallback_reason"] = info.get("message", "Sportmonks 수집 실패")
    return rows


def load_football_fixtures():
    return load_sample_fixtures()


def get_fixture_collection_info():
    return get_last_collection_info()
