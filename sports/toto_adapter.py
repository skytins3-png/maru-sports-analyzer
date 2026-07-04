from __future__ import annotations

from .toto_dual_engine import MatchInput, sample_history, dual_analyze


def fixture_snapshot_to_match_input(fixture: dict, snapshot: dict) -> MatchInput:
    """MARU SPORTS 샘플/실제 수집 데이터를 듀얼 분석 엔진 입력값으로 변환."""
    return MatchInput(
        league=str(fixture.get("league", "축구")),
        home_team=str(fixture.get("home_team", "홈팀")),
        away_team=str(fixture.get("away_team", "원정팀")),
        match_minute=0,
        home_live_score=0,
        away_live_score=0,
        odds_home=1.95,
        odds_draw=3.25,
        odds_away=3.65,
        home_form_score=float(snapshot.get("home_recent_form", 55)),
        away_form_score=float(snapshot.get("away_recent_form", 52)),
        home_attack=float(snapshot.get("home_attack", 55)),
        away_attack=float(snapshot.get("away_attack", 52)),
        home_defense_risk=float(100 - snapshot.get("home_defense", 55)),
        away_defense_risk=float(100 - snapshot.get("away_defense", 55)),
        home_main_injuries=int(snapshot.get("home_injury_risk", 0) // 15),
        away_main_injuries=int(snapshot.get("away_injury_risk", 0) // 15),
        home_suspended=0,
        away_suspended=0,
        home_bench_depth=60,
        away_bench_depth=58,
        home_tactic_fit=62,
        away_tactic_fit=59,
        home_coach_months=18,
        away_coach_months=14,
        home_rotation_risk=30,
        away_rotation_risk=32,
        home_motivation=65,
        away_motivation=62,
        coach_note="MARU SPORTS 자동 변환 입력",
        tactic_note="축구 1차 버전 기본 전술값",
        lineup_note=str(snapshot.get("lineup_status", "probable")),
        market_note="자동구매/자동결제 없음",
    )


def analyze_fixture_with_dual_engine(fixture: dict, snapshot: dict) -> dict:
    inp = fixture_snapshot_to_match_input(fixture, snapshot)
    return dual_analyze(inp, sample_history())
