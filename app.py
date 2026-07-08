import streamlit as st
from core.display_safe import patch_streamlit_dataframe
import pandas as pd
import os
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
from ui.history_store_panel import render_history_store_panel

# 안전한 임포트 처리 및 패널 예외 방어
try:
    from ui.history_range_test_panel import render_history_range_test_panel
except Exception as _history_test_error:
    def render_history_range_test_panel():
        st.error("지난 경기 수집 테스트 패널 import 실패")
        st.code(str(_history_test_error), language="text")

try:
    from ui.sportmonks_diagnostic_panel import render_sportmonks_diagnostic_panel
except Exception as _diag_error:
    def render_sportmonks_diagnostic_panel():
        st.error("Sportmonks 진단 패널 import 실패")
        st.code(str(_diag_error), language="text")

# 1. Streamlit 데이터프레임 패치 적용
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

    # 사이드바 설정 영역
    with st.sidebar:
        st.subheader("MARU 설정")
        app_mode = st.selectbox("앱 모드", ["축구 전용", "확장 준비"], index=0, key="maru_app_mode_select")
        use_slow_api = st.toggle("느린 API 후순위 실행", value=config.use_slow_api, key="maru_slow_api_toggle")
        save_to_sheet = st.toggle("Google Sheet 허브 저장", value=bool(config.gas_webapp_url), key="maru_sheet_save_toggle")
        st.caption("자동구매/자동결제 없음 · 사용자가 직접 선택")

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    # ==========================================
    # 🔄 무료 경기자료 데이터 수집 허브 로직
    # ==========================================
    fixtures = []
    data_source_info = "로컬 저장소"

    # 1순위: 캐싱된 실제 경기 데이터 로드 시도
    history_csv_path = "cache/history_matches.csv"
    if os.path.exists(history_csv_path):
        try:
            df_local = pd.read_csv(history_csv_path)
            if not df_local.empty:
                # ArrowTypeError 방지를 위해 '값' 또는 object 타입 클리닝
                if '값' in df_local.columns:
                    df_local['값'] = df_local['값'].astype(str)
                
                # 데이터프레임을 레코드 딕셔너리 리스트로 변환
                fixtures = df_local.to_dict(orient="records")
                data_source_info = f"실제 수집 데이터 ({len(fixtures)}건)"
        except Exception as e:
            st.sidebar.error(f"로컬 수집 허브 파일 로드 실패: {e}")

    # 2순위: 만약 수집된 실데이터가 0건이라면 가이드 및 샘플 모드 전환
    is_sample_mode = False
    if not fixtures:
        fixtures = load_sample_fixtures()
        is_sample_mode = True
        data_source_info = "샘플 데이터 (실제 수집 데이터 없음)"
        st.info("💡 현재 실제 수집된 경기 데이터(`cache/history_matches.csv`)가 없어 샘플 모드로 작동 중입니다. 수집센터에서 자료를 채워주세요.")

    recommendations = []
    snapshots = []
    analyses = []

    # ==========================================
    # 🛡️ 데이터 분석 및 KeyError 방어 처리 루프
    # ==========================================
    for idx, fixture in enumerate(fixtures):
        # 🚨 [KeyError 방어벽] 수동 CSV나 타사 API에 빠지기 쉬운 필수 구조 강제 인젝션
        if "match_no" not in fixture:
            fixture["match_no"] = fixture.get("match_id", idx + 1)
        if "match_id" not in fixture:
            fixture["match_id"] = f"match_{idx + 1}"
        if "home_team" not in fixture:
            fixture["home_team"] = "Home"
        if "away_team" not in fixture:
            fixture["away_team"] = "Away"
        if "league" not in fixture:
            fixture["league"] = "Unknown League"
        if "date" not in fixture:
            fixture["date"] = datetime.now(KST).strftime("%Y-%m-%d")

        # 인프라 핵심 엔진 가동
        snapshot = build_pre_match_snapshot(fixture, cache=cache, use_slow_api=use_slow_api)
        snapshots.append(snapshot)
        
        analysis = analyze_match(fixture, snapshot)
        analyses.append(analysis)
        
        # 여기서 하위 모듈(football_recommender.py)의 KeyError를 원천적으로 틀어막습니다.
        rec = build_recommendations(fixture, snapshot, analysis)
        if rec:
            recommendations.append(rec)

    # 대시보드 상태창 출력
    render_system_status(
        now_kst=now_kst,
        fixture_count=len(fixtures),
        recommendation_count=len(recommendations),
        slow_api=use_slow_api,
        sheet_enabled=save_to_sheet,
    )
    st.caption(f"📊 **현재 활성화된 데이터 수집원:** {data_source_info}")

    # UI 컴포넌트 배치
    st.divider()
    render_history_range_test_panel()

    st.divider()
    render_history_store_panel(fixtures)

    st.divider()
    render_sportmonks_diagnostic_panel()

    # 결과 분석 카드 출력 혹은 자료부족 가드 활성화
    if recommendations and not is_sample_mode:
        render_mobile_cards(recommendations)
    elif is_sample_mode:
        render_empty_guard()
        with st.expander("🛠️ [개발자용] 가짜 샘플 분석 결과 미리보기"):
            if recommendations:
                render_mobile_cards(recommendations)
    else:
        render_empty_guard()

    # ==========================================
    # 📊 데이터프레임 출력 파트 (Arrow 직렬화 에러 완벽 방어)
    # ==========================================
    st.divider()
    with st.expander("경기 원자료 보기"):
        df_fix = pd.DataFrame(fixtures)
        if '값' in df_fix.columns:
            df_fix['값'] = df_fix['값'].astype(str)
        st.dataframe(df_fix, width="stretch")

    with st.expander("추천 결과 원자료 보기"):
        df_rec = pd.DataFrame(recommendations)
        if '값' in df_rec.columns:
            df_rec['값'] = df_rec['값'].astype(str)
        st.dataframe(df_rec, width="stretch")

    with st.expander("기존 SKYTOTO 듀얼 엔진 자동 비교", expanded=False):
        dual_rows = []
        for fixture in fixtures:
            # 루프 도는 경기 원천 데이터 정합성 보장 재확인
            if "match_id" not in fixture:
                fixture["match_id"] = f"match_dual_{idx + 1}"
            
            snapshot = build_pre_match_snapshot(fixture, cache=cache, use_slow_api=use_slow_api)
            dual = analyze_fixture_with_dual_engine(fixture, snapshot)
            dual_rows.append({
                "match_id": fixture.get("match_id", "N/A"),
                "title": f'{fixture.get("home_team", "Home")} vs {fixture.get("away_team", "Away")}',
                "hub_pick": dual["hub"]["predicted_label"],
                "sheet_pick": dual["sheet"]["predicted_label"],
                "final": dual["compare"]["final"],
                "avg_confidence": dual["compare"].get("avg_conf", 0),
                "risk": dual["compare"].get("max_risk", 0),
            })
        df_dual = pd.DataFrame(dual_rows)
        if '값' in df_dual.columns:
            df_dual['값'] = df_dual['값'].astype(str)
        st.dataframe(df_dual, width="stretch")

    render_dual_engine_panel()

    # 구글 시트 웹앱 전송 연동 파트
    if save_to_sheet and recommendations and not is_sample_mode:
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
    render_data_collection_panel(config, fixtures, snapshots, analyses, recommendations)

    st.divider()
    render_live_score_panel()

    render_footer()


if __name__ == "__main__":
    main()
