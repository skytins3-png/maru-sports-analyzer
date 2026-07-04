def build_recommendations(fixture: dict, snapshot: dict, analysis: dict):
    """
    빈 추천 보호:
    라인업 미확정 + 신뢰도 낮음이면 억지 추천을 만들지 않는다.
    """
    if analysis["confidence"] < 50:
        return None

    reasons = []

    if analysis["gap"] > 5:
        reasons.append("홈팀 종합 점수가 원정팀보다 우세")
    elif analysis["gap"] < -5:
        reasons.append("원정팀 종합 점수가 홈팀보다 우세")
    else:
        reasons.append("양팀 전력 차이가 크지 않아 무승부 가능성 확인 필요")

    if snapshot["home_injury_risk"] > 25 or snapshot["away_injury_risk"] > 25:
        reasons.append("부상/결장 리스크가 분석에 반영됨")

    if snapshot["expected_total_goals"] >= 2.7:
        reasons.append("예상 총득점 흐름이 높은 편")
    elif snapshot["expected_total_goals"] <= 2.2:
        reasons.append("예상 총득점 흐름이 낮은 편")

    if snapshot.get("slow_api_used"):
        reasons.append("느린 API 자료를 후순위로 반영")

    return {
        "rank": 1,
        "match_id": fixture["match_id"],
        "league": fixture["league"],
        "match_no": fixture["match_no"],
        "title": f'{fixture["home_team"]} vs {fixture["away_team"]}',
        "home_team": fixture["home_team"],
        "away_team": fixture["away_team"],
        "kickoff_kst": fixture["kickoff_kst"],
        "main_pick": analysis["win_draw_loss_pick"],
        "sub_pick": analysis["over_under_pick"],
        "confidence": analysis["confidence"],
        "risk": analysis["risk_level"],
        "summary": " / ".join(reasons),
        "auto_purchase": "NO",
        "auto_payment": "NO",
        "user_must_choose": "YES",
    }
