from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List


@dataclass
class LiveScoreInput:
    match_id: str
    league: str
    market_type: str
    home_team: str
    away_team: str
    live_status: str
    home_score: int
    away_score: int
    odds_home: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away: Optional[float] = None
    handicap_line: Optional[float] = None
    over_under_line: Optional[float] = None
    memo: str = ""


def safe_float(v):
    if v in ("", None, "-"):
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None


def safe_int(v, default=0):
    try:
        return int(float(str(v).replace(",", "").strip()))
    except Exception:
        return default


def parse_live_score_row(row: Dict[str, Any]) -> LiveScoreInput:
    """
    Google Sheet live_score 탭 또는 CSV 행을 LiveScoreInput으로 변환한다.

    권장 컬럼:
    match_id, league, market_type, home_team, away_team, live_status,
    home_score, away_score, odds_home, odds_draw, odds_away,
    handicap_line, over_under_line, memo
    """
    return LiveScoreInput(
        match_id=str(row.get("match_id", "")).strip(),
        league=str(row.get("league", "")).strip(),
        market_type=str(row.get("market_type", row.get("market", ""))).strip(),
        home_team=str(row.get("home_team", row.get("home", ""))).strip(),
        away_team=str(row.get("away_team", row.get("away", ""))).strip(),
        live_status=str(row.get("live_status", row.get("inning", ""))).strip(),
        home_score=safe_int(row.get("home_score", 0)),
        away_score=safe_int(row.get("away_score", 0)),
        odds_home=safe_float(row.get("odds_home")),
        odds_draw=safe_float(row.get("odds_draw")),
        odds_away=safe_float(row.get("odds_away")),
        handicap_line=safe_float(row.get("handicap_line", row.get("line"))),
        over_under_line=safe_float(row.get("over_under_line", row.get("line"))),
        memo=str(row.get("memo", "")).strip(),
    )


def analyze_live_score(item: LiveScoreInput) -> Dict[str, Any]:
    """
    라이브 스코어용 간단 분석.
    자동구매/자동결제 없이 참고 카드만 만든다.
    """
    score_gap = item.home_score - item.away_score
    total_score = item.home_score + item.away_score
    market = item.market_type.upper().replace(" ", "")

    risk = "중간"
    confidence = 55
    pick = "보류"
    reason = []

    # 야구/축구 공통으로 안전하게 쓰는 흐름형 분석
    if "U/O" in market or "언오버" in market or "OVER" in market or "UNDER" in market:
        line = item.over_under_line
        if line is None:
            pick = "언오버 기준점 확인 필요"
            confidence = 45
            risk = "높음"
            reason.append("언오버 기준점이 없어 추천을 만들지 않음")
        else:
            if total_score >= line:
                pick = f"{line:g} 오버 흐름"
                confidence = min(82, 58 + int((total_score - line) * 7))
                reason.append(f"현재 총점 {total_score}점이 기준점 {line:g}보다 높거나 같음")
            else:
                remaining_hint = "경기 후반" if any(x in item.live_status for x in ["7", "8", "9", "후반"]) else "경기 중반/초반"
                pick = f"{line:g} 언더 관찰"
                confidence = min(78, 56 + int((line - total_score) * 5))
                reason.append(f"현재 총점 {total_score}점이 기준점 {line:g}보다 낮음")
                reason.append(f"현재 상태: {remaining_hint}")
            risk = "낮음" if confidence >= 72 else "중간"

    elif "H" in market or "핸디" in market or "HANDI" in market:
        line = item.handicap_line
        if line is None:
            pick = "핸디캡 기준점 확인 필요"
            confidence = 45
            risk = "높음"
            reason.append("핸디캡 기준점이 없어 추천을 만들지 않음")
        else:
            adjusted_home = item.home_score + line
            if adjusted_home > item.away_score:
                pick = f"{item.home_team} 핸디 우세 흐름"
                confidence = min(82, 58 + int((adjusted_home - item.away_score) * 7))
                reason.append(f"핸디 반영 점수 {adjusted_home:g} : {item.away_score:g}")
            else:
                pick = f"{item.away_team} 핸디 우세 흐름"
                confidence = min(82, 58 + int((item.away_score - adjusted_home) * 7))
                reason.append(f"핸디 반영 후 {item.away_team} 쪽 흐름 우세")
            risk = "낮음" if confidence >= 72 else "중간"

    else:
        if score_gap > 0:
            pick = f"{item.home_team} 리드 유지 후보"
            confidence = min(80, 57 + score_gap * 6)
            reason.append(f"{item.home_team} 현재 {score_gap}점 차 리드")
        elif score_gap < 0:
            pick = f"{item.away_team} 리드 유지 후보"
            confidence = min(80, 57 + abs(score_gap) * 6)
            reason.append(f"{item.away_team} 현재 {abs(score_gap)}점 차 리드")
        else:
            pick = "동점/접전 보류"
            confidence = 50
            risk = "높음"
            reason.append("현재 동점 또는 접전이라 방향성 약함")

        if item.odds_home or item.odds_away:
            reason.append("배당값은 참고용으로 표시됨")

    if confidence < 55:
        risk = "높음"

    return {
        "match_id": item.match_id,
        "league": item.league,
        "market_type": item.market_type,
        "title": f"{item.home_team} vs {item.away_team}",
        "live_status": item.live_status,
        "score": f"{item.home_score}:{item.away_score}",
        "main_pick": pick,
        "confidence": int(confidence),
        "risk": risk,
        "summary": " / ".join(reason) if reason else "자료 부족으로 보류",
        "odds_home": item.odds_home,
        "odds_draw": item.odds_draw,
        "odds_away": item.odds_away,
        "handicap_line": item.handicap_line,
        "over_under_line": item.over_under_line,
        "auto_purchase": "NO",
        "auto_payment": "NO",
        "user_must_choose": "YES",
    }


def analyze_live_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for row in rows:
        item = parse_live_score_row(row)
        if not item.match_id or not item.home_team or not item.away_team:
            continue
        results.append(analyze_live_score(item))
    return results


def sample_live_rows() -> List[Dict[str, Any]]:
    """
    사용자가 보낸 라이브스코어 화면 예시 기반 샘플.
    """
    return [
        {
            "match_id": "5360",
            "league": "MLB",
            "market_type": "프로토 일반",
            "home_team": "텍사스",
            "away_team": "디트로이트",
            "live_status": "7회 초",
            "home_score": 0,
            "away_score": 3,
            "odds_home": 1.80,
            "odds_away": 1.72,
        },
        {
            "match_id": "5361",
            "league": "MLB",
            "market_type": "승1패",
            "home_team": "텍사스",
            "away_team": "디트로이트",
            "live_status": "7회 초",
            "home_score": 0,
            "away_score": 3,
            "odds_home": 2.65,
            "odds_draw": 3.20,
            "odds_away": 2.18,
        },
        {
            "match_id": "5362",
            "league": "MLB",
            "market_type": "H +2.5",
            "home_team": "텍사스",
            "away_team": "디트로이트",
            "live_status": "7회 초",
            "home_score": 0,
            "away_score": 3,
            "handicap_line": 2.5,
            "odds_home": 1.27,
            "odds_away": 2.87,
        },
        {
            "match_id": "5363",
            "league": "MLB",
            "market_type": "U/O 7.5",
            "home_team": "텍사스",
            "away_team": "디트로이트",
            "live_status": "7회 초",
            "home_score": 0,
            "away_score": 3,
            "over_under_line": 7.5,
        },
    ]
