import streamlit as st


def render_mobile_cards(recommendations: list[dict]):
    st.subheader("🔥 모바일 추천 카드")

    sorted_rows = sorted(recommendations, key=lambda x: x.get("confidence", 0), reverse=True)

    for i, row in enumerate(sorted_rows, start=1):
        with st.container(border=True):
            st.markdown(f"### {i}. {row['league']} {row['match_no']}경기")
            st.markdown(f"## {row['title']}")
            st.write(f"⏰ {row['kickoff_kst']}")

            c1, c2, c3 = st.columns(3)
            c1.metric("승무패", row["main_pick"])
            c2.metric("언오버", row["sub_pick"])
            c3.metric("신뢰도", f"{row['confidence']}%")

            st.write(f"위험도: **{row['risk']}**")
            st.write(f"근거: {row['summary']}")
            st.caption("자동구매/자동결제 없음 · 사용자가 직접 선택")
