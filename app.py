import streamlit as st
from core.display_safe import patch_streamlit_dataframe
import pandas as pd
from datetime import datetime, timezone, timedelta

from core.config import AppConfig
from core.cache_manager import CacheManager
from core.sheet_hub import SheetHub
from core.safe_logger import log_event
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

from sports.free_football_data_uk import (
    fetch_football_data_uk_history,
    merge_history_csv,
    load_history_rows,
    load_upcoming_rows,
)

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

try:
    from ui.free_source_hub_panel import render_free_source_hub_panel
except Exception:
    def render_free_source_hub_panel():
        st.info("무료 경기자료 수집 허브 패널 준비 중")


patch_streamlit_dataframe(st)

KST = timezone(timedelta(hours=9))
HISTORY_CSV_PATH = "cache/history_matches.csv"
UPCOMING_CSV_PATH = "cache/upcoming_fixtures.csv"


def clean_ui_text(text_mapped_dict):
    """실제 추천카드 표시 문구 보정."""
    if not isinstance(text_mapped_dict, dict):
        return text_mapped_dict

    replacements = {
        "미음": "매우 높음",
        "어색하다": "오버/언더 기준",
        "홈승부": "홈승 후보",
        "무승부하다": "무승부 후보",
        "믿는다": "신뢰도",
        "운동:": "근거:",
    }

    cleaned = {}
    for key, value in text_mapped_dict.items():
        if isinstance(value, str):
            for old, new in replacements.items():
                value = value.replace(old, new)
        cleaned[key] = value
    return cleaned


def _is_invalid_real_row(row: dict) -> bool:
    """실버전에서 테스트/샘플/가짜 데이터를 완전히 차단."""
    text = " ".join(
        str(row.get(k, ""))
        for k in ["match_id", "match_no", "league", "home_team", "away_team", "source", "date"]
    ).upper()

    blocked_words = ["TEST", "SAMPLE", "DUMMY", "FAKE", "샘플", "테스트", "가짜"]
    if any(word in text for word in blocked_words):
        return True

    home = str(row.get("home_team", "")).strip().upper()
    away = str(row.get("away_team", "")).strip().upper()

    # 개발용 A/B/C 팀 완전 차단
    if home in {"A", "B", "C", "HOME", "UNKNOWN HOME"}:
        return True
    if away in {"A", "B", "C", "AWAY", "UNKNOWN AWAY"}:
        return True

    return False


def _inject_fixture_defaults(fixture: dict, idx: int) -> dict:
    fixture = dict(fixture)
    fixture.setdefault("match_no", fixture.get("match_id", idx + 1))
    fixture.setdefault("match_id", f"match_{idx + 1}")
    fixture.setdefault("home_team", "")
    fixture.setdefault("away_team", "")
    fixture.setdefault("league", "")
    fixture.setdefault("date", datetime.now(KST).strftime("%Y-%m-%d"))
    fixture.setdefault("kickoff_kst", fixture.get("time", fixture.get("kickoff", "")))
    fixture.setdefault("source", "unknown")
    return fixture


def render_real_csv_collection_box():
    st.subheader("📥 무료 경기결과 실제 수집")
    st.caption(
        "Football-Data.co.uk 완료 경기 CSV를 가져와 과거자료 저장소에 저장합니다. "
        "이 자료는 추천카드가 아니라 최근 흐름/홈원정/상대전적 분석 근거로 사용합니다."
    )

    league_options = {
        "E0": "잉글랜드 프리미어리그",
        "E1": "잉글랜드 챔피언십",
        "D1": "독일 분데스리가",
        "SP1": "스페인 라리가",
        "I1": "이탈리아 세리에A",
        "F1": "프랑스 리그1",
    }

    col1, col2 = st.columns([1, 2])

    with col1:
        season_code = st.text_input(
            "시즌 코드",
            value="2627",
            key="maru_real_fd_uk_season_code",
            help="예: 2526, 2627",
        )

    with col2:
        selected_codes = st.multiselect(
            "수집 리그",
            options=list(league_options.keys()),
            default=["E0", "D1", "SP1"],
            format_func=lambda code: f"{code} · {league_options[code]}",
            key="maru_real_fd_uk_league_codes",
        )

    if st.button("실제 CSV 수집 후 과거자료 저장", key="maru_real_fd_uk_collect_btn"):
        with st.spinner("Football-Data.co.uk 실제 완료 경기 수집 중..."):
            df_new, logs = fetch_football_data_uk_history(
                season_code=season_code,
                league_codes=selected_codes,
            )

        with st.expander("수집 로그 보기", expanded=False):
            st.dataframe(pd.DataFrame(logs), width="stretch")

        if df_new.empty:
            st.warning("수집된 완료 경기 데이터가 없습니다. 시즌 코드, 리그 코드, 경기 진행 여부를 확인하세요.")
        else:
            # 실버전 필터: 테스트/샘플 행 저장 차단
            df_new = df_new[
                ~df_new.apply(lambda r: _is_invalid_real_row(r.to_dict()), axis=1)
            ]

            if df_new.empty:
                st.warning("수집 결과가 실데이터 필터를 통과하지 못했습니다.")
            else:
                added_count, total_count = merge_history_csv(HISTORY_CSV_PATH, df_new)
                st.success(f"과거자료 저장 완료: 신규/정리 {added_count}건 · 전체 {total_count}건")
                st.dataframe(df_new.head(30), width="stretch")


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

    # ==========================================================
    # 실버전 핵심 원칙
    # history_matches.csv = 과거 완료 경기 저장소
    # upcoming_fixtures.csv = 예정 경기 저장소
    # 과거자료/샘플/테스트 데이터로 추천카드 생성 금지
    # 앱 시작 시 외부 사이트 자동호출 금지
    # ==========================================================
    history_rows = [
        r for r in load_history_rows(HISTORY_CSV_PATH)
        if not _is_invalid_real_row(r)
    ]

    fixtures = [
        _inject_fixture_defaults(r, idx)
        for idx, r in enumerate(load_upcoming_rows(UPCOMING_CSV_PATH))
        if not _is_invalid_real_row(r)
    ]

    recommendations = []
    snapshots = []
    analyses = []

    for idx, fixture in enumerate(fixtures):
        snapshot = build_pre_match_snapshot(fixture, cache=cache, use_slow_api=use_slow_api)
        snapshots.append(snapshot)

        analysis = analyze_match(fixture, snapshot)
        analyses.append(analysis)

        rec = build_recommendations(fixture, snapshot, analysis)
        if rec:
            recommendations.append(clean_ui_text(rec))

    data_source_info = f"실제 과거자료 {len(history_rows)}건 / 실제 예정경기 {len(fixtures)}건"

    render_system_status(
        now_kst=now_kst,
        fixture_count=len(fixtures),
        recommendation_count=len(recommendations),
        slow_api=use_slow_api,
        sheet_enabled=save_to_sheet,
    )
    st.caption(f"📊 **현재 활성화된 데이터 수집원:** {data_source_info}")

    st.divider()
    render_real_csv_collection_box()

    st.divider()
    render_history_range_test_panel()

    st.divider()
    render_free_source_hub_panel()

    st.divider()
    render_history_store_panel(history_rows)

    st.divider()
    render_sportmonks_diagnostic_panel()

    if recommendations:
        render_mobile_cards(recommendations)
    else:
        render_empty_guard()
        st.info(
            "실제 예정 경기 자료가 없어 추천카드를 만들지 않았습니다. "
            "과거 완료 경기는 최근 5경기/10경기/홈원정/득실/상대전적 분석 근거로만 사용합니다."
        )

    st.divider()
    with st.expander("과거 경기 원자료 보기"):
        st.dataframe(pd.DataFrame(history_rows), width="stretch")

    with st.expander("예정 경기 원자료 보기"):
        st.dataframe(pd.DataFrame(fixtures), width="stretch")

    with st.expander("추천 결과 원자료 보기"):
        st.dataframe(pd.DataFrame(recommendations), width="stretch")

    with st.expander("기존 SKYTOTO 듀얼 엔진 자동 비교", expanded=False):
        if not fixtures:
            st.info("실제 예정 경기 자료가 없어 듀얼 엔진 비교를 실행하지 않았습니다.")
        else:
            dual_rows = []
            for idx_d, fixture in enumerate(fixtures):
                fixture = _inject_fixture_defaults(fixture, idx_d)
                current_snapshot = snapshots[idx_d] if idx_d < len(snapshots) else {}
                dual = analyze_fixture_with_dual_engine(fixture, current_snapshot)

                dual_rows.append({
                    "match_id": fixture.get("match_id", "N/A"),
                    "title": f'{fixture.get("home_team", "")} vs {fixture.get("away_team", "")}',
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

    log_event(
        "app_run",
        {
            "history_rows": len(history_rows),
            "fixtures": len(fixtures),
            "recommendations": len(recommendations),
        },
    )

    st.divider()
    render_data_collection_panel(config, fixtures, snapshots, analyses, recommendations)

    st.divider()
    render_live_score_panel()

    render_footer()


if __name__ == "__main__":
    main()
