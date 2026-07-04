from datetime import datetime, timezone, timedelta


KST = timezone(timedelta(hours=9))


def load_sample_fixtures():
    """
    첫 버전 샘플 경기.
    실제 API 연결 전에도 모바일 카드/분석/허브 저장 흐름을 테스트할 수 있게 한다.
    """
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
        },
    ]
