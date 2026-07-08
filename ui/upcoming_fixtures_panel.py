import os
from io import StringIO
from datetime import datetime

import pandas as pd
import streamlit as st


UPCOMING_CSV_PATH = "cache/upcoming_fixtures.csv"

REQUIRED_UPCOMING_COLUMNS = [
    "date",
    "kickoff_kst",
    "league",
    "home_team",
    "away_team",
]

OPTIONAL_UPCOMING_COLUMNS = [
    "status",
    "source",
    "match_id",
]

KOREAN_COLUMN_MAP = {
    "날짜": "date",
    "경기일": "date",
    "시간": "kickoff_kst",
    "킥오프": "kickoff_kst",
    "리그": "league",
    "홈팀": "home_team",
    "원정팀": "away_team",
    "상태": "status",
    "출처": "source",
    "경기ID": "match_id",
    "경기아이디": "match_id",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={c: KOREAN_COLUMN_MAP.get(c, c) for c in df.columns})
    return df


def _clean_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def _validate_upcoming_df(df: pd.DataFrame):
    df = _normalize_columns(df)

    missing = [c for c in REQUIRED_UPCOMING_COLUMNS if c not in df.columns]
    if missing:
        return False, df, {
            "message": "예정 경기 필수 컬럼 누락",
            "missing": missing,
            "required": REQUIRED_UPCOMING_COLUMNS,
        }

    rows = []
    for idx, row in df.iterrows():
        date = _clean_text(row.get("date"))
        kickoff = _clean_text(row.get("kickoff_kst"))
        league = _clean_text(row.get("league"))
        home = _clean_text(row.get("home_team"))
        away = _clean_text(row.get("away_team"))
        status = _clean_text(row.get("status")) or "SCHEDULED"
        source = _clean_text(row.get("source")) or "manual"
        match_id = _clean_text(row.get("match_id"))

        if not date or not league or not home or not away:
            continue

        if not match_id:
            safe_home = home.replace(" ", "_")
            safe_away = away.replace(" ", "_")
            match_id = f"manual_{date}_{safe_home}_{safe_away}"

        # 예정 경기에는 점수 컬럼을 넣지 않는다.
        rows.append({
            "date": date,
            "kickoff_kst": kickoff,
            "league": league,
            "home_team": home,
            "away_team": away,
            "status": status,
            "source": source,
            "match_id": match_id,
        })

    clean_df = pd.DataFrame(rows)

    if clean_df.empty:
        return False, clean_df, {
            "message": "저장 가능한 예정 경기 행이 없습니다.",
            "required": REQUIRED_UPCOMING_COLUMNS,
        }

    for col in clean_df.columns:
        clean_df[col] = clean_df[col].astype(str)

    return True, clean_df, {
        "message": "예정 경기 CSV 정규화 성공",
        "rows": len(clean_df),
    }


def _merge_upcoming_csv(path: str, df_new: pd.DataFrame):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    if os.path.exists(path):
        try:
            df_old = pd.read_csv(path)
            df_total = pd.concat([df_old, df_new], ignore_index=True)
        except Exception:
            df_total = df_new
    else:
        df_total = df_new

    if "match_id" in df_total.columns:
        df_total = df_total.drop_duplicates(subset=["match_id"], keep="last")
    else:
        df_total = df_total.drop_duplicates(subset=["date", "home_team", "away_team"], keep="last")

    df_total.to_csv(path, index=False)
    return len(df_total)


def render_upcoming_fixtures_panel():
    st.subheader("📅 예정 경기 직접 입력")
    st.caption(
        "여기는 앞으로 분석할 경기 입력칸입니다. 예정 경기는 아직 점수가 없으므로 "
        "home_score, away_score가 필요 없습니다."
    )

    sample_csv = """date,kickoff_kst,league,home_team,away_team,status,source,match_id
2026-07-10,20:00,잉글랜드 프리미어리그,Liverpool,Man City,SCHEDULED,manual,manual_001
2026-07-10,22:00,잉글랜드 프리미어리그,Arsenal,Chelsea,SCHEDULED,manual,manual_002
"""

    st.download_button(
        "예정 경기 샘플 CSV 다운로드",
        data=sample_csv.encode("utf-8-sig"),
        file_name="upcoming_fixtures_sample.csv",
        mime="text/csv",
        key="download_upcoming_fixtures_sample",
    )

    pasted_csv = st.text_area(
        "예정 경기 CSV 직접 붙여넣기",
        value=sample_csv,
        height=160,
        key="upcoming_fixtures_csv_textarea",
    )

    uploaded_file = st.file_uploader(
        "또는 예정 경기 CSV 파일 업로드",
        type=["csv"],
        key="upcoming_fixtures_csv_uploader",
    )

    df_input = None

    if uploaded_file is not None:
        try:
            df_input = pd.read_csv(uploaded_file)
        except Exception as exc:
            st.error(f"CSV 파일 읽기 실패: {exc}")
    elif pasted_csv.strip():
        try:
            df_input = pd.read_csv(StringIO(pasted_csv))
        except Exception as exc:
            st.error(f"붙여넣은 CSV 읽기 실패: {exc}")

    if st.button("예정 경기 CSV 검사", key="check_upcoming_csv_btn"):
        if df_input is None:
            st.warning("검사할 예정 경기 CSV가 없습니다.")
        else:
            ok, clean_df, info = _validate_upcoming_df(df_input)
            st.json(info)
            if ok:
                st.success(f"예정 경기 {len(clean_df)}건 정규화 성공")
                st.dataframe(clean_df, width="stretch")
            else:
                st.error(info.get("message", "예정 경기 CSV 검사 실패"))

    if st.button("예정 경기 저장", key="save_upcoming_csv_btn"):
        if df_input is None:
            st.warning("저장할 예정 경기 CSV가 없습니다.")
        else:
            ok, clean_df, info = _validate_upcoming_df(df_input)
            if not ok:
                st.error(info.get("message", "예정 경기 CSV 검사 실패"))
                st.json(info)
            else:
                total = _merge_upcoming_csv(UPCOMING_CSV_PATH, clean_df)
                st.success(f"예정 경기 저장 완료: 입력 {len(clean_df)}건 · 전체 {total}건")
                st.info("저장 후 앱을 새로고침하면 추천카드가 예정 경기 기준으로 생성됩니다.")
                st.dataframe(clean_df, width="stretch")

    with st.expander("저장된 예정 경기 보기", expanded=False):
        if os.path.exists(UPCOMING_CSV_PATH):
            try:
                saved_df = pd.read_csv(UPCOMING_CSV_PATH)
                st.dataframe(saved_df, width="stretch")
            except Exception as exc:
                st.error(f"저장된 예정 경기 읽기 실패: {exc}")
        else:
            st.caption("아직 저장된 예정 경기가 없습니다.")
