def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def analyze_match(fixture: dict, snapshot: dict):
    """
    승무패 + 언오버 기본 분석.
    첫 버전은 설명 가능한 점수형 모델로 간다.
    """

    home_score = (
        snapshot["home_recent_form"] * 0.28
        + snapshot["home_attack"] * 0.22
        + snapshot["home_defense"] * 0.12
        + (100 - snapshot["home_injury_risk"]) * 0.18
        + max(0, -snapshot["odds_home_movement"] * 100) * 0.10
        + 55 * 0.10
    )

    away_score = (
        snapshot["away_recent_form"] * 0.28
        + snapshot["away_attack"] * 0.22
        + snapshot["away_defense"] * 0.12
        + (100 - snapshot["away_injury_risk"]) * 0.18
        + max(0, -snapshot["odds_away_movement"] * 100) * 0.10
        + 48 * 0.10
    )

    gap = home_score - away_score

    if abs(gap) < 5:
        wdl_pick = "무승부 후보"
        wdl_confidence = 52 + abs(gap)
    elif gap > 0:
        wdl_pick = "홈승 후보"
        wdl_confidence = 55 + min(25, abs(gap))
    else:
        wdl_pick = "원정승 후보"
        wdl_confidence = 55 + min(25, abs(gap))

    goal_power = (
        snapshot["expected_total_goals"] * 20
        + snapshot["home_attack"] * 0.18
        + snapshot["away_attack"] * 0.18
        + (100 - snapshot["home_defense"]) * 0.10
        + (100 - snapshot["away_defense"]) * 0.10
        - snapshot["weather_risk"] * 0.25
    )

    if goal_power >= 66:
        ou_pick = "2.5 오버 후보"
        ou_confidence = clamp(goal_power)
    elif goal_power <= 52:
        ou_pick = "2.5 언더 후보"
        ou_confidence = clamp(100 - goal_power + 20)
    else:
        ou_pick = "언오버 보류"
        ou_confidence = 50

    total_confidence = int(clamp((wdl_confidence * 0.55 + ou_confidence * 0.45)))

    if total_confidence >= 75:
        risk = "낮음"
    elif total_confidence >= 62:
        risk = "중간"
    else:
        risk = "높음"

    return {
        "home_score": round(home_score, 1),
        "away_score": round(away_score, 1),
        "gap": round(gap, 1),
        "win_draw_loss_pick": wdl_pick,
        "win_draw_loss_confidence": int(clamp(wdl_confidence)),
        "over_under_pick": ou_pick,
        "over_under_confidence": int(clamp(ou_confidence)),
        "confidence": total_confidence,
        "risk_level": risk,
    }
