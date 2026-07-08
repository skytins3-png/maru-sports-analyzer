import io
import streamlit as st
import pandas as pd

from sports.history_store import append_history, load_history, history_summary, normalize_history_df, analyze_fixture_from_history
from sports.fallback_collector import collect_history_with_fallback

SAMPLE_CSV = """date,league,home_team,away_team,home_score,away_score,status,source
2026-07-01,K LEAGUE,Ulsan HD,Jeonbuk Hyundai,2,1,finished,csv
2026-07-02,K LEAGUE,FC Seoul,Pohang Steelers,1,1,finished,csv
2026-07-03,K LEAGUE,Suwon FC,Daegu FC,0,2,finished,csv
2026-07-04,K LEAGUE,Pohang Steelers,Ulsan HD,1,3,finished,csv
2026-07-05,K LEAGUE,Jeonbuk Hyundai,FC Seoul,2,2,finished,csv
"""

def _read_csv_text(csv_text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(csv_text.strip()))

def _show_and_save_df(df: pd.DataFrame, source_label: str):
    norm, info = normalize_history_df(df)
    st.write(f"{source_label} 정규화 검사")
    st.json(info, expanded=False)
    if not info.get("ok"):
        st.error("필수 컬럼이 부족합니다. date, league, home_team, away_team, home_score, away_score가 필요합니다.")
        return
    st.dataframe(norm.head(50), width="stretch", hide_index=True)
    if st.button(f"{source_label} 자료를 과거자료 저장소에 추가", key=f"append_history_{source_label}"):
        result = append_history(norm)
        st.json(result, expanded=False)
        if result.get("ok"):
            st.success("과거자료 저장 완료")
            st.rerun()
        else:
            st.error("저장 실패")

def render_history_store_panel(fixtures=None):
    st.subheader("🗄️ 과거자료 저장소 / 대체자료 분석")
    st.caption("Sportmonks 무료 플랜에서 못 받는 과거자료는 CSV 저장자료로 대체합니다. 없는 자료는 분석불가로 표시합니다.")

    summary = history_summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("저장 경기 수", summary.get("rows", 0))
    c2.metric("팀 수", summary.get("teams", 0))
    c3.metric("리그 수", summary.get("leagues", 0))
    c4.metric("기간", f"{summary.get('date_min','')} ~ {summary.get('date_max','')}")

    st.info("회색 CSV 형식 안내문은 입력칸이 아닙니다. 직접 붙여넣기는 아래 'CSV 직접 붙여넣기' 칸에 넣으세요.")

    with st.expander("CSV 형식 보기 / 샘플 다운로드", expanded=True):
        st.code("date,league,home_team,away_team,home_score,away_score,status,source", language="text")
        st.write("한글 컬럼명도 일부 지원합니다: 날짜, 리그, 홈팀, 원정팀, 홈점수, 원정점수")
        st.download_button(
            "샘플 CSV 다운로드",
            data=SAMPLE_CSV.encode("utf-8-sig"),
            file_name="maru_history_sample.csv",
            mime="text/csv",
            key="download_history_sample_csv",
        )

    paste_text = st.text_area(
        "CSV 직접 붙여넣기",
        value="",
        height=180,
        placeholder=SAMPLE_CSV,
        key="history_csv_paste_textarea",
    )

    if st.button("붙여넣은 CSV 검사", key="check_pasted_csv_button"):
        if not paste_text.strip():
            st.warning("붙여넣은 CSV 내용이 없습니다.")
        else:
            try:
                pasted_df = _read_csv_text(paste_text)
                _show_and_save_df(pasted_df, "붙여넣은 CSV")
            except Exception as e:
                st.error("붙여넣은 CSV 읽기 실패")
                st.code(str(e), language="text")

    st.divider()

    uploaded = st.file_uploader("또는 CSV 파일 업로드", type=["csv"], key="history_csv_upload")
    if uploaded is not None:
        try:
            uploaded_df = pd.read_csv(uploaded)
            _show_and_save_df(uploaded_df, "업로드 CSV")
        except Exception as e:
            st.error("CSV 파일 읽기 실패")
            st.code(str(e), language="text")

    st.divider()

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
