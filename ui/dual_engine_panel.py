from __future__ import annotations

import streamlit as st
import pandas as pd

from sports.toto_dual_engine import MatchInput, sample_history, dual_analyze
from sports.backtest_engine import run_quick_backtest


def render_dual_engine_panel():
    st.subheader("🧪 듀얼 분석 엔진")
    st.caption("기존 SKYTOTO 실험앱에서 추출한 허브 분석 + 과거자료 분석 + 비교 엔진입니다. 자동구매/자동결제 없음.")

    with st.expander("수동 경기 입력 테스트", expanded=False):
        c1, c2 = st.columns(2)
        league = c1.text_input("리그", "K리그")
        home_team = c1.text_input("홈팀", "울산")
        away_team = c2.text_input("원정팀", "전북")
        match_minute = c1.number_input("경기 시간(분)", 0, 120, 0)
        home_live_score = c1.number_input("홈 현재 득점", 0, 20, 0)
        away_live_score = c2.number_input("원정 현재 득점", 0, 20, 0)
        odds_home = c1.number_input("홈승 배당", 1.01, 50.0, 1.95)
        odds_draw = c1.number_input("무승부 배당", 1.01, 50.0, 3.25)
        odds_away = c2.number_input("원정승 배당", 1.01, 50.0, 3.65)

        c3, c4, c5 = st.columns(3)
        home_form = c3.slider("홈 최근 폼", 0, 100, 62)
        away_form = c4.slider("원정 최근 폼", 0, 100, 58)
        home_attack = c3.slider("홈 공격", 0, 100, 65)
        away_attack = c4.slider("원정 공격", 0, 100, 60)
        home_def_risk = c3.slider("홈 수비위험", 0, 100, 38)
        away_def_risk = c4.slider("원정 수비위험", 0, 100, 42)
        home_inj = c5.number_input("홈 주전 부상", 0, 15, 0)
        away_inj = c5.number_input("원정 주전 부상", 0, 15, 1)

        if st.button("듀얼 분석 실행", key="dual_engine_run_btn"):
            inp = MatchInput(
                league=league, home_team=home_team, away_team=away_team,
                match_minute=int(match_minute), home_live_score=int(home_live_score), away_live_score=int(away_live_score),
                odds_home=float(odds_home), odds_draw=float(odds_draw), odds_away=float(odds_away),
                home_form_score=float(home_form), away_form_score=float(away_form),
                home_attack=float(home_attack), away_attack=float(away_attack),
                home_defense_risk=float(home_def_risk), away_defense_risk=float(away_def_risk),
                home_main_injuries=int(home_inj), away_main_injuries=int(away_inj),
                home_suspended=0, away_suspended=0,
                home_bench_depth=60, away_bench_depth=58,
                home_tactic_fit=62, away_tactic_fit=59,
                home_coach_months=18, away_coach_months=14,
                home_rotation_risk=30, away_rotation_risk=35,
                home_motivation=65, away_motivation=62,
                coach_note="", tactic_note="", lineup_note="", market_note="",
            )
            result = dual_analyze(inp, sample_history())
            comp = result["compare"]
            st.success(f"{comp['icon']} 최종판정: {comp['final']} / 평균신뢰도 {comp.get('avg_conf', 0)}%")
            st.write("비교 메모:", " / ".join(comp.get("notes", [])))
            st.dataframe(pd.DataFrame([result["hub"], result["sheet"]]), use_container_width=True)

    with st.expander("빠른 백테스트", expanded=False):
        row_count = st.slider("실험 과거자료 수", 100, 3000, 500, step=100)
        sample_n = st.slider("백테스트 표본", 20, 500, 80, step=20)
        scenario = st.selectbox("시나리오", ["mixed", "저배당함정", "무승부함정", "역배위험"], index=0)
        if st.button("백테스트 실행", key="quick_backtest_btn"):
            bt = run_quick_backtest(row_count=row_count, sample_n=sample_n, scenario=scenario)
            if bt.get("ok"):
                c1, c2, c3 = st.columns(3)
                c1.metric("허브 적중률", f"{bt.get('hub_accuracy', 0)}%")
                c2.metric("시트 적중률", f"{bt.get('sheet_accuracy', 0)}%")
                c3.metric("동시일치 적중률", f"{bt.get('same_accuracy', 0)}%")
                st.dataframe(pd.DataFrame(bt.get("rows", [])[:200]), use_container_width=True)
            else:
                st.warning(bt.get("message", "백테스트 실패"))
