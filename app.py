import streamlit as st
from core.display_safe import patch_streamlit_dataframe
import pandas as pd
import os
import requests
from datetime import datetime, timezone, timedelta

# 🚨 urllib3 경고 로그(InsecureRequestWarning) 차단막 추가
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

# 1. Streamlit 데이터프레임 패치 적용
patch_streamlit_dataframe(st)

KST = timezone(timedelta(hours=9))

# 📱 라이브스코어 앱 한글 팀명 -> Football-Data.co.uk 영문 데이터 매칭 사전
TEAM_TRANSLATION = {
    "아스널": "Arsenal", "아스날": "Arsenal",
    "맨시티": "Man City", "맨체스터시티": "Man City", "맨체스터 시티": "Man City",
    "리버풀": "Liverpool",
    "첼시": "Chelsea",
    "맨유": "Man United", "맨체스터유나이티드": "Man United",
    "토트넘": "Tottenham",
    "바이에른뮌헨": "Bayern Munich", "뮌헨": "Bayern Munich",
    "레알마드리드": "Real Madrid", "레알": "Real Madrid",
    "바르셀로나": "Barcelona", "바르샤": "Barcelona"
}


def clean_ui_text(text_mapped_dict):
    """UI 카드에서 발생하는 번역 및 오타 패치"""
    if not isinstance(text_mapped_dict, dict):
        return text_mapped_dict
        
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


def fetch_football_data_uk_csv():
    """[1순위 수집원] Football-Data.co.uk 실시간 CSV 다운로드 엔진"""
    standardized_rows = []
    target_leagues = {
        "E0": "잉글랜드 프리미어리그",
        "E1": "잉글랜드 챔피언십",
        "D1": "독일 분데스리가",
        "SP1": "스페인 라리가"
    }
    
    base_url = "https://www.football-data.co.uk/mmz4371/2627/"
    
    for league_code, league_name in target_leagues.items():
        csv_url = f"{base_url}{league_code}.csv"
        try:
            response = requests.get(csv_url, timeout=7, verify=False)
            if response.status_code == 200:
                csv_data = response.content.decode('utf-8', errors='ignore')
                from io import StringIO
                df_raw = pd.read_csv(StringIO(csv_data))
                
                required_cols = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]
                if all(col in df_raw.columns for col in required_cols):
                    df_raw = df_raw.dropna(subset=required_cols)
                    
                    for _, row in df_raw.iterrows():
                        raw_date = str(row["Date"]).strip()
                        try:
                            if "/" in raw_date:
                                parts = raw_date.split("/")
                                if len(parts[2]) == 2:
                                    parts[2] = f"20{parts[2]}"
                                formatted_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                            else:
                                formatted_date = raw_date
                        except Exception:
                            formatted_date = raw_date

                        standardized_rows.append({
                            "date": formatted_date,
                            "kickoff_kst": "00:00",
                            "league": league_name,
                            "home_team": str(row["HomeTeam"]).strip(),
                            "away_team": str(row["AwayTeam"]).strip(),
                            "home_score": int(row["FTHG"]),
                            "away_score": int(row["FTAG"]),
                            "status": "FT",
                            "source": f"football_data_uk_{league_code}",
                            "match_id": f"uk_{league_code}_{formatted_date}_{str(row['HomeTeam'])[:3]}"
                        })
        except Exception:
            continue
            
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

    with st.sidebar:
        st.subheader("MARU 설정")
        app_mode = st.selectbox("앱 모드", ["축구 전용", "확장 준비"], index=0, key="maru_app_mode_select")
        use_slow_api = st.toggle("느린 API 후순위 실행", value=config.use_slow_api, key="maru_slow_api_toggle")
        save_to_sheet = st.toggle("Google Sheet 허브 저장", value=bool(config.gas_webapp_url), key="maru_sheet_save_toggle")
        st.caption("자동구매/자동결제 없음 · 사용자가 직접 선택")

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    fixtures = []
    data_source_info = "로컬 저장소"
    history_csv_path = "cache/history_matches.csv"

    # ==========================================
    # 📡 1순위 Football-Data.co.uk 자동 파이프라인 가동
    # ==========================================
    with st.spinner("🔄 Football-Data.co.uk 실시간 축구 원천자료 수집 중..."):
        df_uk_parsed = fetch_football_data_uk_csv()
        if not df_uk_parsed.empty:
            os.makedirs("cache", exist_ok=True)
            if os.path.exists(history_csv_path):
                try:
                    df_existing = pd.read_csv(history_csv_path)
                    df_total = pd.concat([df_existing, df_uk_parsed]).drop_duplicates(subset=["date", "home_team", "away_team"])
                except Exception:
                    df_total = df_uk_parsed
            else:
                df_total = df_uk_parsed
            
            df_total.to_csv(history_csv_path, index=False)
            fixtures = df_total.to_dict(orient="records")
            data_source_info = f"Football-Data.co.uk 실시간 CSV 연동 ({len(fixtures)}건 데이터 로드 완료)"

    # 비상용 로컬 캐시 백킹
    if not fixtures and os.path.exists(history_csv_path):
        try:
            df_local = pd.read_csv(history_csv_path)
            if not df_local.empty:
                if '값' in df_local.columns:
                    df_local['값'] = df_local['값'].astype(str)
                fixtures = df_local.to_dict(orient="records")
                data_source_info = f"로컬 캐시 허브 파일 ({len(fixtures)}건)"
        except Exception:
            pass

    # 최종 예외 모드
    is_sample_mode = False
    if not fixtures:
        fixtures = load_sample_fixtures()
        is_sample_mode = True
        data_source_info = "샘플 데이터 모드"

    # ==========================================
    # 📱 라이브스코어 앱 연동 브릿지 필터링
    # ==========================================
    st.sidebar.markdown("---")
    st.sidebar.subheader("📱 라이브스코어 팀명 매칭")
    search_input = st.sidebar.text_input("앱 화면의 팀명을 입력하세요 (예: 아스널)", key="livescore_team_search").strip()
    
    if search_input:
        english_team_name = TEAM_TRANSLATION.get(search_input, search_input).lower()
        fixtures = [
            f for f in fixtures 
            if english_team_name in str(f.get("home_team", "")).lower() or english_team_name in str(f.get("away_team", "")).lower()
        ]
        data_source_info += f" 🔍 [라이브스코어 앱 '{search_input}' 필터링 작동 중 - {len(fixtures)}건 매칭]"

    recommendations = []
    snapshots = []
    analyses = []

    # ==========================================
    # 🛡️ 데이터 분석 및 결측치 가드월
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

        snapshot = build_pre_match_snapshot(fixture, cache=cache, use_slow_api=use_slow_api)
        snapshots.append(snapshot)
        
        analysis = analyze_match(fixture, snapshot)
        analyses.append(analysis)
        
        rec = build_recommendations(fixture, snapshot, analysis)
        if rec:
            rec = clean_ui_text(rec)
            recommendations.append(rec)

    # 마스터 상태 메인 대시보드
    render_system_status(
        now_kst=now_kst,
        fixture_count=len(fixtures),
        recommendation_count=len(recommendations),
        slow_api=use_slow_api,
        sheet_enabled=save_to_sheet,
    )
    st.caption(f"📊 **현재 활성화된 데이터 수집원:** {data_source_info}")

    # ==========================================
    # 🗄️ 과거자료 수집센터 및 핵심 분석 카드
    # ==========================================
    st.divider()
    render_history_store_panel(fixtures)

    if recommendations and not is_sample_mode:
        render_mobile_cards(recommendations)
    else:
        render_empty_guard()

    # 원자료 모니터링 섹션
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

    # 듀얼 매칭 비교 엔진
    with st.expander("기존 SKYTOTO 듀얼 엔진 자동 비교", expanded=False):
        dual_rows = []
        for idx_d, fixture in enumerate(fixtures):
            if "match_id" not in fixture:
                fixture["match_id"] = f"match_dual_{idx_d + 1}"
            
            current_snapshot = snapshots[idx_d] if idx_d < len(snapshots) else {}
            dual = analyze_fixture_with_dual_engine(fixture, current_snapshot)
            
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
