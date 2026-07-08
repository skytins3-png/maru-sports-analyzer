# MARU SPORTS ANALYZER - 예정 경기 입력 패널 패치

## 문제

화면에서 예정 경기 CSV를 과거자료 검사기에 넣어서 실패했습니다.

예정 경기 CSV:
date,kickoff_kst,league,home_team,away_team,status,source,match_id

과거자료 검사기는 완료 경기용이라 다음 컬럼을 요구합니다:
home_score, away_score

그래서 "필수 컬럼 부족" 오류가 뜬 것입니다.

## 해결

예정 경기는 별도 패널에서 입력합니다.

추가 파일:
ui/upcoming_fixtures_panel.py

## app.py 연결

app.py 상단 import 근처에 추가:

try:
    from ui.upcoming_fixtures_panel import render_upcoming_fixtures_panel
except Exception as _upcoming_panel_error:
    def render_upcoming_fixtures_panel():
        import streamlit as st
        st.error("예정 경기 입력 패널 import 실패")
        st.code(str(_upcoming_panel_error), language="text")

그리고 화면 배치 구간에 추가:

st.divider()
render_upcoming_fixtures_panel()

추천카드는 cache/upcoming_fixtures.csv에 저장된 예정 경기 기준으로 생성됩니다.
