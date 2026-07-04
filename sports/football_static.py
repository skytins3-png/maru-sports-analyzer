def get_team_static_profile(team_name: str):
    """
    고정자료 캐시 대상:
    팀 기본정보, 감독, 구장, 과거 시즌 결과 등.
    실제 API 연결 전에는 기본값을 반환한다.
    """
    return {
        "team": team_name,
        "coach": "unknown",
        "stadium": "unknown",
        "season_strength": 50,
        "home_strength": 50,
        "away_strength": 50,
    }
