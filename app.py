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


def clean_ui_text(text_mapped_dict):
    """UI 카드에서 발생하는 어순 및 번역 오류 텍스트 패치 기기"""
    if not isinstance(text_mapped_dict, dict):
        return text_mapped_dict
        
    # 터진 텍스트 직접 치환 보정 벨트
    bad_translations = {
        "미음": "매우 높음",
        "어색하다": "오버/언더 기준",
        "홈승부": "홈승 후보",
        "무승부하다": "무승부 후보"
    }
    
    cleaned = {}
    for k, v in text_mapped_dict.items():
        if isinstance(v, str):
            for bad, good in bad_translations.items():
                v = v.replace(bad, good)
        cleaned[k] = v
    return cleaned


def parse_sportmonks_raw_response(sportmonks_payload):
    """
    Sportmonks API 응답 원본 패킷에서 
    participants 뎁스를 깨부수고 표준 규격 데이터프레임으로 추출하는 커넥터
    """
    standardized_rows = []
    if not sportmonks_payload or "data" not in sportmonks_payload:
        return pd.DataFrame()
        
    for item in sportmonks_payload.get("data", []):
        home_team = "Unknown Home"
        away_team = "Unknown Away"
        
        # participants 배열 내부 루프를 돌며 홈/원정 스위칭 분리
        for part in item.get("participants", []):
            location = part.get("meta", {}).get("location", "")
            if location == "home":
                home_team = part.get("name", "Home")
            elif location == "away":
                away_team = part.get("name", "Away")
                
        starting_at = item.get("starting_at", "")
        match_date = starting_at.split(" ")[0] if starting_at else datetime.now(KST).strftime("%Y-%m-%d")
        kickoff_time = starting_at.split(" ")[1][:5] if " " in starting_at else "00:00"
        
        standardized_rows.append({
            "date": match_date,
            "kickoff_kst": kickoff_time,
            "league": item.get("name", f"League_{item.get('league_id', 'Unknown')}").split(" vs ")[0],
            "home_team": home_team,
            "away_team": away_team,
            "home_score": 0,
            "away_score": 0,
            "status": "FT" if item.get("state_id") == 5 else "SCHEDULED",
            "source": "sportmonks_api",
            "match_id": str(item.get("id", ""))
        })
    return pd.DataFrame(standardized_rows)


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
    # 🔄 무료 경기자료 데이터 수집 허브 파이프라인
    # ==========================================
    fixtures = []
    data_source_info = "로컬 저장소"
    history_csv_path = "cache/history_matches.csv"

    # [백엔드 자동 처리 연동] 만약 진단 패널 등 세션에 Sportmonks 원본 로우 데이터 수집 흔적이 있다면 병합 자동 시도
    if st.session_state.get("sportmonks_raw_debug_payload"):
        try:
            df_parsed = parse_sportmonks_raw_response(st.session_state["sportmonks_raw_debug_payload"])
            if not df_parsed.empty:
                os.makedirs("cache", exist_ok=True)
                if os.path.exists(history_csv_path):
                    df_existing = pd.read_csv(history_csv_path)
                    df_total = pd.concat([df_existing, df_parsed]).drop_duplicates(subset=["date", "home_team", "away_team"])
                else:
                    df_total = df_parsed
                df_total.to_csv(history_csv_path, index=False)
                st.sidebar.success(f"Sportmonks 실데이터 {len(df_parsed)}건 동기화 완료!")
        except Exception as _sync_err:
            st.sidebar.warning(f"Sportmonks 실데이터 허브 변환 스킵: {_sync_err}")

    # 1순위: 캐싱된 수집 허브 경기 데이터 파일 로드
    if os.path.exists(history_csv_path):
        try:
            df_local = pd.read_csv(history_csv_path)
            if not df_local.empty:
                if '값' in df_local.columns:
                    df_local['값'] = df_local['값'].astype(str)
                fixtures = df_local.to_dict(orient="records")
                data_source_info = f"실제 수집 데이터 ({len(fixtures)}건)"
        except Exception as e:
            st.sidebar.error(f"로컬 수집 허브 파일 로드 실패: {e}")

    # 2순위: 만약 파일 시스템 내 데이터가 0건이라면 가이드 샘플 전환
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
    # 🛡️ 데이터 분석 및 KeyError 가드월 가동
    # ==========================================
    for idx, fixture in enumerate(fixtures):
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
        if "kickoff_kst" not in fixture:
            fixture["kickoff_kst"] = fixture.get("time", fixture.get("kickoff", "00:00"))

        # 스냅샷 및 마루 통계 코어 연산 가동
        snapshot = build_pre_match_snapshot(fixture, cache=cache, use_slow_api=use_slow_api)
        snapshots.append(snapshot)
        
        analysis = analyze_match(fixture, snapshot)
        analyses.append(analysis)
        
        rec = build_recommendations(fixture, snapshot, analysis)
        if rec:
            # 💡 [UI 패치 가동] 출력 직전에 꼬인 한글 텍스트 정밀 클리닝
            rec = clean_ui_text(rec)
            recommendations.append(rec)

    # 대시보드 마스터 상태창 출력
    render_system_status(
        now_kst=now_kst,
        fixture_count=len(fixtures),
        recommendation_count=len(recommendations),
        slow_api=use_slow_api,
        sheet_enabled=save_to_sheet,
    )
    st.caption(f"📊 **현재 활성화된 데이터 수집원:** {data_source_info}")

    # UI 컴포넌트 순차 배치
    st.divider()
    render_history_range_test_panel()

    st.divider()
    render_history_store_panel(fixtures)

    st.divider()
    render_sportmonks_diagnostic_panel()

    # 결과 카드 출력 가드 시스템
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
    # 📊 데이터프레임 원자료 출력 파트 (Arrow TypeError 완벽 케어)
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
        for idx_d, fixture in enumerate(fixtures):
            if "match_id" not in fixture:
                fixture["match_id"] = f"match_dual_{idx_d + 1}"
            
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

    # 구글 시트 업스케일링 전송
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
