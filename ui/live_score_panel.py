import streamlit as st
import pandas as pd
from sports.analysis_transparency import build_live_score_breakdown

from sports.live_score_engine import (
    sample_live_rows,
    analyze_live_rows,
    parse_live_score_row,
    analyze_live_score,
)


LIVE_COLUMNS = [
    "match_id", "league", "market_type", "home_team", "away_team",
    "live_status", "home_score", "away_score",
    "odds_home", "odds_draw", "odds_away",
    "handicap_line", "over_under_line", "memo"
]


def render_live_score_cards(results):
    if not results:
        st.warning("라이브스코어 추천 없음: 경기번호/팀명/스코어를 확인하세요.")
        return

    for row in results:
        with st.container(border=True):
            st.markdown(f"### 🔴 LIVE {row['league']} · {row['match_id']}")
            st.markdown(f"## {row['title']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("현재", row["live_status"])
            c2.metric("스코어", row["score"])
            c3.metric("신뢰도", f"{row['confidence']}%")
            st.write(f"마켓: **{row['market_type']}**")
            st.write(f"판정: **{row['main_pick']}**")
            st.write(f"위험도: **{row['risk']}**")
            st.caption(row["summary"])
            st.caption("자동구매/자동결제 없음 · 사용자가 직접 선택")
            with st.expander("LIVE 분석 점수표 / 근거 보기"):
                st.dataframe(pd.DataFrame(build_live_score_breakdown(row)), width="stretch", hide_index=True)


def render_live_score_panel():
    st.subheader("🔴 라이브스코어 입력 분석")
    st.caption("사진처럼 보이는 경기번호, 팀, 현재 스코어, 배당, 핸디캡, 언오버 기준점을 입력해서 즉시 분석합니다.")

    tab1, tab2, tab3 = st.tabs(["샘플 화면 적용", "수동 1경기 입력", "CSV/시트 붙여넣기"])

    with tab1:
        rows = sample_live_rows()
        st.dataframe(pd.DataFrame(rows), width="stretch")
        results = analyze_live_rows(rows)
        render_live_score_cards(results)

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            match_id = st.text_input("경기번호", "5361", key="live_match_id")
            league = st.text_input("리그", "MLB", key="live_league")
            market_type = st.text_input("마켓", "승1패", key="live_market")
            home_team = st.text_input("홈팀/왼쪽팀", "텍사스", key="live_home")
            away_team = st.text_input("원정팀/오른쪽팀", "디트로이트", key="live_away")
            live_status = st.text_input("현재 상황", "7회 초", key="live_status")
        with c2:
            home_score = st.number_input("홈/왼쪽 점수", min_value=0, value=0, step=1, key="live_home_score")
            away_score = st.number_input("원정/오른쪽 점수", min_value=0, value=3, step=1, key="live_away_score")
            odds_home = st.number_input("홈/왼쪽 배당", min_value=0.0, value=2.65, step=0.01, key="live_odds_home")
            odds_draw = st.number_input("무/중간 배당", min_value=0.0, value=3.20, step=0.01, key="live_odds_draw")
            odds_away = st.number_input("원정/오른쪽 배당", min_value=0.0, value=2.18, step=0.01, key="live_odds_away")
            handicap_line = st.number_input("핸디캡 기준", value=0.0, step=0.5, key="live_handicap")
            over_under_line = st.number_input("언오버 기준", value=7.5, step=0.5, key="live_ou")

        row = {
            "match_id": match_id,
            "league": league,
            "market_type": market_type,
            "home_team": home_team,
            "away_team": away_team,
            "live_status": live_status,
            "home_score": int(home_score),
            "away_score": int(away_score),
            "odds_home": odds_home if odds_home > 0 else None,
            "odds_draw": odds_draw if odds_draw > 0 else None,
            "odds_away": odds_away if odds_away > 0 else None,
            "handicap_line": handicap_line if handicap_line != 0 else None,
            "over_under_line": over_under_line if over_under_line != 0 else None,
        }
        render_live_score_cards(analyze_live_rows([row]))

    with tab3:
        st.write("아래 컬럼 형식으로 CSV를 붙여넣으면 여러 경기를 한 번에 분석합니다.")
        st.code(",".join(LIVE_COLUMNS), language="text")
        csv_text = st.text_area(
            "CSV 붙여넣기",
            value="match_id,league,market_type,home_team,away_team,live_status,home_score,away_score,odds_home,odds_draw,odds_away,handicap_line,over_under_line,memo\n5363,MLB,U/O 7.5,텍사스,디트로이트,7회 초,0,3,,,,,7.5,",
            height=160,
            key="live_csv_text",
        )
        if csv_text.strip():
            try:
                from io import StringIO
                df = pd.read_csv(StringIO(csv_text))
                st.dataframe(df, width="stretch")
                results = analyze_live_rows(df.to_dict("records"))
                render_live_score_cards(results)
            except Exception as e:
                st.error(f"CSV 분석 실패: {e}")
