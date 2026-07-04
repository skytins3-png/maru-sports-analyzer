import streamlit as st


def render_header():
    st.title("⚽ MARU SPORTS ANALYZER")
    st.caption("축구 경기 자료수집 · 분석 · 추천 참고용 | 자동구매 없음 | 자동결제 없음 | 사용자가 직접 선택")


def render_system_status(now_kst: str, fixture_count: int, recommendation_count: int, slow_api: bool, sheet_enabled: bool):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("현재 시간", now_kst)
    c2.metric("경기 수", fixture_count)
    c3.metric("추천 카드", recommendation_count)
    c4.metric("느린 API", "ON" if slow_api else "OFF")

    st.info(
        f"Google Sheet 허브: {'ON' if sheet_enabled else 'OFF'} · "
        "Streamlit Cloud / GitHub Actions / 모바일 카드 구조 유지"
    )


def render_footer():
    st.divider()
    st.caption(
        "본 앱은 스포츠 경기 자료수집, 통계 분석, 추천 참고용 도구입니다. "
        "자동구매, 자동결제, 베팅 대행 기능은 제공하지 않습니다."
    )
