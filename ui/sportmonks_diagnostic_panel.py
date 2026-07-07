import streamlit as st


def render_sportmonks_diagnostic_panel():
    st.subheader("🧪 Sportmonks API 직접 수집 테스트")
    st.caption("안전부팅 모드입니다. 앱 시작 때는 API를 부르지 않고, 이 버튼을 눌렀을 때만 호출합니다.")

    try:
        from sports.sportmonks_client import run_diagnostic_test, get_last_collection_info
    except Exception as e:
        st.error("Sportmonks 진단 모듈 로드 실패")
        st.code(str(e), language="text")
        return

    with st.expander("최근 수집 상태", expanded=True):
        try:
            st.json(get_last_collection_info(), expanded=False)
        except Exception as e:
            st.code(str(e), language="text")

    if st.button("Sportmonks API 지금 테스트", key="sportmonks_api_test_button"):
        try:
            with st.spinner("Sportmonks API 호출 중... 최대 12초"):
                result = run_diagnostic_test()
            st.json(result, expanded=False)

            if result.get("fixtures_count", 0) > 0:
                st.success(f"실제 경기 {result['fixtures_count']}건 수집 성공")
            else:
                st.error("실제 경기 수집 0건 또는 실패")
                info = result.get("info", {})
                st.write("message")
                st.code(str(info.get("message", "")), language="text")
                st.write("response_preview")
                st.code(str(info.get("response_preview", ""))[:1200], language="text")
        except Exception as e:
            st.error("Sportmonks API 테스트 실행 중 오류")
            st.code(str(e), language="text")
