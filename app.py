import streamlit as st
from core.display_safe import patch_streamlit_dataframe
import pandas as pd
from datetime import datetime, timezone, timedelta

from core.config import AppConfig
from core.cache_manager import CacheManager
from core.sheet_hub import SheetHub
from core.safe_logger import log_event
from sports.football_fixtures import load_sample_fixtures
from sports.football_pre_match import build_pre_match_snapshot
from sports.football_analyzer import analyze_match
from sports.football_recommender import build_recommendations
from ui.mobile_cards import render_mobile_cards
from ui.empty_guard import render_empty_guard
from ui.dashboard import render_header, render_footer, render_system_status
from ui.dual_engine_panel import render_dual_engine_panel
from ui.live_score_panel import render_live_score_panel
from ui.data_collection_panel import render_data_collection_panel
from sports.toto_adapter import analyze_fixture_with_dual_engine
try:
    from ui.history_range_test_panel import render_history_range_test_panel
except Exception as _history_test_error:
    def render_history_range_test_panel():
        import streamlit as st
        st.error("지난 경기 수집 테스트 패널 import 실패")
        st.code(str(_history_test_error), language="text")
try:
    from ui.sportmonks_diagnostic_panel import render_sportmonks_diagnostic_panel
except Exception as _diag_error:
    def render_sportmonks_diagnostic_panel():
        import streamlit as st
        st.error("Sportmonks 진단 패널 import 실패")
        st.code(str(_diag_error), language="text")



patch_streamlit_dataframe(st)

KST = timezone(timedelta(hours=9))


def main():
    st.set_page_config(
        page_title="MARU SPORTS ANALYZER",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    config = AppConfig.from_streamlit_secrets()
    cache = CacheManager()
    hub = SheetHub(config.gas_webapp_url)

    render_header()

    with st.sidebar:
        st.subheader("MARU 설정")
        app_mode = st.selectbox("앱 모드", ["축구 전용", "확장 준비"], index=0)
        use_slow_api = st.toggle("느린 API 후순위 실행", value=config.use_slow_api)
        save_to_sheet = st.toggle("Google Sheet 허브 저장", value=bool(config.gas_webapp_url))
        st.caption("자동구매/자동결제 없음 · 사용자가 직접 선택")

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    fixtures = load_sample_fixtures()
    recommendations = []
    snapshots = []
    analyses = []

    for fixture in fixtures:
        snapshot = build_pre_match_snapshot(fixture, cache=cache, use_slow_api=use_slow_api)
        snapshots.append(snapshot)
        analysis = analyze_match(fixture, snapshot)
        analyses.append(analysis)
        rec = build_recommendations(fixture, snapshot, analysis)
        if rec:
            recommendations.append(rec)

    render_system_status(
        now_kst=now_kst,
        fixture_count=len(fixtures),
        recommendation_count=len(recommendations),
        slow_api=use_slow_api,
        sheet_enabled=save_to_sheet,
    )

    if recommendations:
        render_mobile_cards(recommendations)
    else:
        render_empty_guard()

    st.divider()
    with st.expander("경기 원자료 보기"):
        st.dataframe(pd.DataFrame(fixtures), width="stretch")

    with st.expander("추천 결과 원자료 보기"):
        st.dataframe(pd.DataFrame(recommendations), width="stretch")

    with st.expander("기존 SKYTOTO 듀얼 엔진 자동 비교", expanded=False):
        dual_rows = []
        for fixture in fixtures:
            snapshot = build_pre_match_snapshot(fixture, cache=cache, use_slow_api=use_slow_api)
            dual = analyze_fixture_with_dual_engine(fixture, snapshot)
            dual_rows.append({
                "match_id": fixture["match_id"],
                "title": f'{fixture["home_team"]} vs {fixture["away_team"]}',
                "hub_pick": dual["hub"]["predicted_label"],
                "sheet_pick": dual["sheet"]["predicted_label"],
                "final": dual["compare"]["final"],
                "avg_confidence": dual["compare"].get("avg_conf", 0),
                "risk": dual["compare"].get("max_risk", 0),
            })
        st.dataframe(pd.DataFrame(dual_rows), width="stretch")

    render_dual_engine_panel()

    if save_to_sheet and recommendations:
        payload = {
            "type": "mobile_recommend",
            "app": "MARU SPORTS ANALYZER",
            "created_at": now_kst,
            "rows": recommendations,
        }
        ok, msg = hub.push(payload)
        if ok:
            st.success("Google Sheet 허브 저장 완료")
        else:
            st.warning(f"Google Sheet 허브 저장 실패 또는 미설정: {msg}")

    log_event("app_run", {"fixtures": len(fixtures), "recommendations": len(recommendations)})
    st.divider()
    st.divider()
    render_data_collection_panel(config, fixtures, snapshots, analyses, recommendations)

    st.divider()
    render_live_score_panel()

    render_footer()


if __name__ == "__main__":
    main()
