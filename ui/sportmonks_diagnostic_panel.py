import streamlit as st


def _load_sportmonks_tools():
    """
    앱 시작 시 import하지 않고, 화면/버튼 실행 시점에만 import한다.
    sportmonks_client가 빠졌거나 오류가 있어도 앱 전체가 죽지 않게 한다.
    """
    try:
        from sports.sportmonks_client import run_diagnostic_test, get_last_collection_info
        return run_diagnostic_test, get_last_collection_info, None
    except Exception as e:
        return None, None, e


def render_sportmonks_diagnostic_panel():
    st.subheader("🧪 Sportmonks API 직접 수집 테스트")
    st.caption("앱 안에서 실제 API가 호출되는지, 0건인지, 권한 문제인지 바로 확인합니다.")

    run_diagnostic_test, get_last_collection_info, load_error = _load_sportmonks_tools()

    if load_error:
        st.error("Sportmonks 진단 모듈을 불러오지 못했습니다.")
        st.code(str(load_error), language="text")
        st.warning("GitHub에 sports/sportmonks_client.py 파일이 올라갔는지 확인하세요.")
        return

    with st.expander("최근 자동 수집 상태", expanded=True):
        try:
            st.json(get_last_collection_info(), expanded=False)
        except Exception as e:
            st.error("최근 수집 상태 읽기 실패")
            st.code(str(e), language="text")

    if st.button("Sportmonks API 지금 테스트", key="sportmonks_api_test_button"):
        try:
            with st.spinner("Sportmonks API 호출 중..."):
                result = run_diagnostic_test()
            st.json(result, expanded=False)

            if result.get("fixtures_count", 0) > 0:
                st.success(f"실제 경기 {result['fixtures_count']}건 수집 성공")
            else:
                st.error("실제 경기 수집 0건 또는 실패")
                info = result.get("info", {})
                st.code(str(info.get("message", "")), language="text")
                st.code(str(info.get("response_preview", ""))[:900], language="text")
        except Exception as e:
            st.error("Sportmonks API 테스트 실행 중 오류")
            st.code(str(e), language="text")
