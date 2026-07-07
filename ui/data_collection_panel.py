import streamlit as st
import pandas as pd
from core.config import AppConfig
from core.api_clients import mask_key
from sports.football_fixtures import get_fixture_collection_info
from sports.analysis_transparency import build_collection_status, build_score_breakdown_from_analysis, package_raw_data

def _df(rows):
    return pd.DataFrame(rows or [])

def render_data_collection_panel(config: AppConfig, fixtures: list, snapshots: list | None = None, analyses: list | None = None, recommendations: list | None = None):
    snapshots = snapshots or []
    analyses = analyses or []
    recommendations = recommendations or []

    st.subheader("📡 자료수집 현황판")
    st.caption("수집 자료, 원자료, 분석 점수표를 직접 확인할 수 있습니다. 자동구매/자동결제는 없습니다.")

    fixture_info = get_fixture_collection_info()
    status_rows = build_collection_status(
        fixture_count=len(fixtures),
        live_count=0,
        has_sports_api=bool(config.sports_api_key),
        has_odds_api=bool(config.odds_api_key),
        has_weather_api=bool(config.weather_api_key),
        sheet_enabled=bool(config.gas_webapp_url),
        fixture_source=fixture_info.get('source', ''),
        fixture_message=fixture_info.get('message', ''),
    )
    st.dataframe(_df(status_rows), width="stretch", hide_index=True)

    with st.expander("⚽ Sportmonks 실제 수집 상태", expanded=True):
        st.json(fixture_info, expanded=False)

    with st.expander("🔐 API 연결 상태 보기", expanded=False):
        api_rows = [
            {"name": "SPORTS_API_KEY", "status": "있음" if config.sports_api_key else "없음", "preview": mask_key(config.sports_api_key)},
            {"name": "ODDS_API_KEY", "status": "있음" if config.odds_api_key else "없음", "preview": mask_key(config.odds_api_key)},
            {"name": "WEATHER_API_KEY", "status": "있음" if config.weather_api_key else "없음", "preview": mask_key(config.weather_api_key)},
            {"name": "GAS_WEBAPP_URL", "status": "있음" if config.gas_webapp_url else "없음", "preview": mask_key(config.gas_webapp_url)},
        ]
        st.dataframe(pd.DataFrame(api_rows), width="stretch", hide_index=True)
        st.warning("API 키는 전체를 화면에 표시하지 않습니다. Streamlit Secrets / GitHub Secrets에 넣으세요.")

    st.subheader("📦 원자료 보기")
    tab1, tab2, tab3, tab4 = st.tabs(["경기 일정", "경기 전 변동자료", "추천 결과", "JSON 원본"])
    with tab1:
        st.dataframe(_df(fixtures), width="stretch", hide_index=True)
    with tab2:
        st.dataframe(_df(snapshots), width="stretch", hide_index=True) if snapshots else st.info("아직 경기 전 변동자료가 없습니다.")
    with tab3:
        st.dataframe(_df(recommendations), width="stretch", hide_index=True) if recommendations else st.info("아직 추천 결과가 없습니다.")
    with tab4:
        st.json(package_raw_data(fixtures, recommendations), expanded=False)

    st.subheader("🧮 분석 점수표")
    score_rows = []
    for idx, fixture in enumerate(fixtures):
        snapshot = snapshots[idx] if idx < len(snapshots) else {}
        analysis = analyses[idx] if idx < len(analyses) else {}
        if snapshot and analysis:
            score_rows.extend(build_score_breakdown_from_analysis(fixture, snapshot, analysis))
    st.dataframe(pd.DataFrame(score_rows), width="stretch", hide_index=True) if score_rows else st.info("분석 점수표를 만들 자료가 아직 없습니다.")
    st.caption("점수표는 승패 확정이 아니라 추천 후보와 위험도를 설명하는 근거표입니다.")
