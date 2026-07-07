import streamlit as st
import pandas as pd
from sports.history_store import append_history, load_history, history_summary, normalize_history_df, analyze_fixture_from_history
from sports.fallback_collector import collect_history_with_fallback

def render_history_store_panel(fixtures=None):
    st.subheader("🗄️ 과거자료 저장소 / 대체자료 분석")
    st.caption("Sportmonks 무료 플랜에서 못 받는 과거자료는 CSV 저장자료로 대체합니다. 없는 자료는 분석불가로 표시합니다.")

    summary = history_summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("저장 경기 수", summary.get("rows", 0))
    c2.metric("팀 수", summary.get("teams", 0))
    c3.metric("리그 수", summary.get("leagues", 0))
    c4.metric("기간", f"{summary.get('date_min','')} ~ {summary.get('date_max','')}")

    with st.expander("CSV 업로드 형식", expanded=False):
        st.code("date,league,home_team,away_team,home_score,away_score,status,source", language="text")
        st.write("한글 컬럼명도 일부 지원: 날짜, 리그, 홈팀, 원정팀, 홈점수, 원정점수")

    uploaded = st.file_uploader("과거 경기 CSV 업로드", type=["csv"], key="history_csv_upload")
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
            norm, info = normalize_history_df(df)
            st.write("정규화 검사")
            st.json(info, expanded=False)
            if info.get("ok"):
                st.dataframe(norm.head(50), width="stretch", hide_index=True)
                if st.button("이 CSV를 과거자료 저장소에 추가", key="append_history_csv_button"):
                    result = append_history(norm)
                    st.json(result, expanded=False)
                    if result.get("ok"):
                        st.success("과거자료 저장 완료")
                    else:
                        st.error("저장 실패")
            else:
                st.error("CSV 필수 컬럼이 부족합니다.")
        except Exception as e:
            st.error("CSV 읽기 실패")
            st.code(str(e), language="text")

    if st.button("자료 대체 흐름 점검", key="fallback_flow_check"):
        result = collect_history_with_fallback(days_back=7)
        st.json(result, expanded=False)
        if result.get("ok"):
            st.success(result.get("message", "대체자료 사용 가능"))
        else:
            st.error(result.get("message", "자료 부족"))

    with st.expander("저장된 과거자료 미리보기", expanded=False):
        hist = load_history()
        if hist.empty:
            st.warning("저장된 과거자료가 없습니다.")
        else:
            st.dataframe(hist.tail(100), width="stretch", hide_index=True)

    if fixtures:
        with st.expander("현재 경기 목록을 저장된 과거자료로 분석 시도", expanded=False):
            hist = load_history()
            rows = []
            for fixture in fixtures:
                r = analyze_fixture_from_history(fixture, hist, n=10)
                rows.append({
                    "경기": r.get("title"),
                    "분석가능": r.get("analysis_possible"),
                    "자료충분도": r.get("data_sufficiency"),
                    "위험도": r.get("risk"),
                    "판단": r.get("pick", ""),
                    "메시지": r.get("message"),
                })
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
