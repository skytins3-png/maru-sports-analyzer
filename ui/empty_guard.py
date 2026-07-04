import streamlit as st


def render_empty_guard():
    st.warning("현재 추천 없음")
    st.write(
        """
        추천을 억지로 만들지 않았습니다.

        가능한 이유:
        - 라인업 미확정
        - 부상자 정보 부족
        - 배당 변화 미수집
        - 경기 시작까지 시간이 많이 남음
        - 신뢰도 기준 미달
        """
    )
