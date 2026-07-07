import streamlit as st


def render_sportmonks_diagnostic_panel():
    st.subheader("🧪 Sportmonks 기본 진단")
    st.caption("기본 진단은 지난 7일 범위로 실제 수집 여부를 확인합니다.")

    try:
        from sports.sportmonks_client import run_diagnostic_test, get_last_collection_info
    except Exception as e:
        st.error("Sportmonks 진단 모듈 로드 실패")
        st.code(str(e), language="text")
        return

    with st.expander("최근 수집 상태", expanded=False):
        st.json(get_last_collection_info(), expanded=False)

    if st.button("Sportmonks 지난 7일 기본 테스트", key="sportmonks_api_test_button"):
        with st.spinner("Sportmonks API 호출 중..."):
            result = run_diagnostic_test()
        st.json(result, expanded=False)
        if result.get("fixtures_count", 0) > 0:
            st.success(f"지난 7일 기준 {result['fixtures_count']}경기 수집 성공")
        else:
            st.error("수집 0건 또는 실패")
            info = result.get("info", {})
            st.code(str(info.get("message", "")), language="text")
            st.code(str(info.get("response_preview", ""))[:1200], language="text")
