from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

KST = timezone(timedelta(hours=9))

def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def build_collection_status(fixture_count: int = 0, live_count: int = 0, has_sports_api: bool = False, has_odds_api: bool = False, has_weather_api: bool = False, sheet_enabled: bool = False, fixture_source: str = '', fixture_message: str = '') -> List[Dict[str, Any]]:
    return [
        {"category": "경기 일정", "status": "실제 API" if fixture_source == "sportmonks" and fixture_count else ("API 대기" if has_sports_api else "샘플/수동"), "source": fixture_source or "SPORTS_API_KEY / 샘플", "count": fixture_count, "updated_at": now_kst(), "note": fixture_message or "API 연결 시 실제 경기 일정으로 교체"},
        {"category": "라이브스코어", "status": "API 연결" if has_sports_api else "수동/CSV", "source": "SPORTS_API_KEY / CSV / Google Sheet", "count": live_count, "updated_at": now_kst(), "note": "실시간 점수/이닝/시간"},
        {"category": "배당/핸디캡/언오버", "status": "API 연결" if has_odds_api else "수동/CSV", "source": "ODDS_API_KEY / CSV", "count": 0, "updated_at": now_kst(), "note": "배당 흐름, 기준점"},
        {"category": "부상자/결장자/라인업", "status": "API 연결" if has_sports_api else "후순위", "source": "SPORTS_API_KEY", "count": 0, "updated_at": now_kst(), "note": "경기 전 변동자료"},
        {"category": "날씨", "status": "API 연결" if has_weather_api else "미연결", "source": "WEATHER_API_KEY", "count": 0, "updated_at": now_kst(), "note": "야외 경기 영향"},
        {"category": "Google Sheet 저장", "status": "연결됨" if sheet_enabled else "미연결", "source": "GAS_WEBAPP_URL", "count": 0, "updated_at": now_kst(), "note": "추천/원자료/분석 이력 저장"},
    ]

def build_score_breakdown_from_analysis(fixture: Dict[str, Any], snapshot: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    def add(factor, home_value, away_value, weight, note):
        rows.append({"match_id": fixture.get("match_id", ""), "factor": factor, "home_team": fixture.get("home_team", ""), "away_team": fixture.get("away_team", ""), "home_value": home_value, "away_value": away_value, "weight": weight, "note": note})
    add("최근 폼", snapshot.get("home_recent_form"), snapshot.get("away_recent_form"), 0.28, "최근 경기 흐름")
    add("공격력", snapshot.get("home_attack"), snapshot.get("away_attack"), 0.22, "득점 가능성")
    add("수비력", snapshot.get("home_defense"), snapshot.get("away_defense"), 0.12, "실점 억제")
    add("부상 리스크", snapshot.get("home_injury_risk"), snapshot.get("away_injury_risk"), 0.18, "낮을수록 유리")
    add("배당 변화", snapshot.get("odds_home_movement"), snapshot.get("odds_away_movement"), 0.10, "배당 흐름 참고")
    add("종합 점수", analysis.get("home_score"), analysis.get("away_score"), 1.00, analysis.get("win_draw_loss_pick", ""))
    return rows

def build_live_score_breakdown(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"match_id": row.get("match_id", ""), "factor": "현재 스코어", "value": row.get("score", ""), "note": "현재 리드/접전 상태 판단"},
        {"match_id": row.get("match_id", ""), "factor": "현재 상황", "value": row.get("live_status", ""), "note": "이닝/전후반/경기시간"},
        {"match_id": row.get("match_id", ""), "factor": "마켓", "value": row.get("market_type", ""), "note": "승무패/핸디캡/언오버 구분"},
        {"match_id": row.get("match_id", ""), "factor": "기준점", "value": row.get("handicap_line") or row.get("over_under_line") or "", "note": "핸디캡 또는 언오버 기준"},
        {"match_id": row.get("match_id", ""), "factor": "판정", "value": row.get("main_pick", ""), "note": row.get("summary", "")},
        {"match_id": row.get("match_id", ""), "factor": "신뢰도/위험도", "value": f"{row.get('confidence', '')}% / {row.get('risk', '')}", "note": "자동구매 아님, 참고용"},
    ]

def package_raw_data(fixtures: List[Dict[str, Any]], recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"created_at": now_kst(), "fixtures": fixtures, "recommendations": recommendations, "notice": "사용자가 직접 확인할 수 있는 원자료 패키지", "auto_purchase": "NO", "auto_payment": "NO"}
