import streamlit as st
import pandas as pd


def render_history_range_test_panel():
    st.subheader("📚 지난 경기 수집 가능 일수 테스트")
    st.caption("분석 전에 Sportmonks에서 과거 며칠치가 실제로 받아지는지 먼저 확인합니다. 앱 시작 때는 호출하지 않습니다.")

    try:
        from sports.sportmonks_client import test_history_range, test_history_ranges, get_last_collection_info
    except Exception as e:
        st.error("과거자료 수집 테스트 모듈 로드 실패")
        st.code(str(e), language="text")
        return

    with st.expander("최근 수집 상태", expanded=False):
        st.json(get_last_collection_info(), expanded=False)

    days_options = [1, 3, 7, 14, 30, 60, 90]
    col1, col2 = st.columns(2)

    with col1:
        selected_days = st.selectbox("테스트할 지난 기간", days_options, index=2, key="history_range_days")
        if st.button("선택 기간 테스트", key="history_range_single_test"):
            with st.spinner(f"지난 {selected_days}일 자료 수집 테스트 중..."):
                result = test_history_range(int(selected_days), timeout=15)
            st.json(result, expanded=False)
            if result.get("fixtures_count", 0) > 0:
                st.success(f"지난 {selected_days}일 범위에서 {result['fixtures_count']}경기 수집됨")
            else:
                st.error(f"지난 {selected_days}일 범위 수집 0건 또는 실패")
                st.code(str(result.get("info", {}).get("message", "")), language="text")
                st.code(str(result.get("info", {}).get("response_preview", ""))[:1200], language="text")

    with col2:
        if st.button("1/3/7/14/30/60/90일 전체 테스트", key="history_range_all_test"):
            with st.spinner("여러 기간을 차례로 테스트 중..."):
                result = test_history_ranges(days_options, timeout=12)

            rows = []
            for r in result.get("results", []):
                info = r.get("info", {})
                rows.append({
                    "기간": f"지난 {r.get('range_days')}일",
                    "시작일": r.get("from_dash"),
                    "종료일": r.get("to_dash"),
                    "수집경기수": r.get("fixtures_count"),
                    "HTTP": info.get("http_status", ""),
                    "상태": info.get("message", ""),
                })

            st.write(f"자료가 확인된 최대 범위: 지난 {result.get('max_range_with_data')}일")
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

            with st.expander("전체 원본 결과", expanded=False):
                st.json(result, expanded=False)
