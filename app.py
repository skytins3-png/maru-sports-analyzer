import os
from io import StringIO
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
import streamlit as st


# ==========================================================
# MARU SPORTS ANALYZER - CLEAN REAL VERSION
# ----------------------------------------------------------
# 원칙:
# 1. 앱 시작 시 외부 사이트 자동 호출 없음
# 2. 샘플/TEST/가짜 추천 없음
# 3. 과거자료/예정경기/현재상태 자료 완전 분리
# 4. 자료 없으면 자료부족 표시
# 5. 기존 복잡한 모듈 import 최소화
# ==========================================================

KST = timezone(timedelta(hours=9))

CACHE_DIR = "cache"
HISTORY_PATH = f"{CACHE_DIR}/history_matches.csv"
UPCOMING_PATH = f"{CACHE_DIR}/upcoming_fixtures.csv"
TEAM_STATUS_PATH = f"{CACHE_DIR}/team_status.csv"

LEAGUE_NAMES = {
    "E0": "잉글랜드 프리미어리그",
    "E1": "잉글랜드 챔피언십",
    "D1": "독일 분데스리가",
    "SP1": "스페인 라리가",
    "I1": "이탈리아 세리에A",
    "F1": "프랑스 리그1",
}

HISTORY_REQUIRED = ["date", "league", "home_team", "away_team", "home_score", "away_score"]
UPCOMING_REQUIRED = ["date", "kickoff_kst", "league", "home_team", "away_team"]
TEAM_STATUS_REQUIRED = ["team", "coach", "missing_players", "key_players", "note"]

KOREAN_COLUMN_MAP = {
    "날짜": "date",
    "경기일": "date",
    "시간": "kickoff_kst",
    "킥오프": "kickoff_kst",
    "리그": "league",
    "홈팀": "home_team",
    "원정팀": "away_team",
    "홈점수": "home_score",
    "원정점수": "away_score",
    "홈 점수": "home_score",
    "원정 점수": "away_score",
    "상태": "status",
    "출처": "source",
    "경기ID": "match_id",
    "경기아이디": "match_id",
    "팀": "team",
    "팀명": "team",
    "감독": "coach",
    "결장": "missing_players",
    "부상": "missing_players",
    "주요선수": "key_players",
    "핵심선수": "key_players",
    "메모": "note",
    "비고": "note",
}


def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def now_kst_text():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={c: KOREAN_COLUMN_MAP.get(c, c) for c in df.columns})
    return df


def clean_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def safe_score(value):
    text = clean_text(value)
    if text == "":
        return ""
    try:
        return int(float(text))
    except Exception:
        return ""


def read_csv_safe(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        df = normalize_columns(df)
        for col in df.columns:
            df[col] = df[col].astype(str)
        return df
    except Exception:
        return pd.DataFrame()


def write_csv_safe(path: str, df: pd.DataFrame):
    ensure_cache_dir()
    df.to_csv(path, index=False)


def merge_csv(path: str, df_new: pd.DataFrame, subset_cols):
    ensure_cache_dir()
    if df_new is None or df_new.empty:
        current = read_csv_safe(path)
        return 0, len(current)

    current = read_csv_safe(path)
    before = len(current)

    if current.empty:
        total = df_new.copy()
    else:
        total = pd.concat([current, df_new], ignore_index=True)

    existing_subset = [c for c in subset_cols if c in total.columns]
    if existing_subset:
        total = total.drop_duplicates(subset=existing_subset, keep="last")
    else:
        total = total.drop_duplicates(keep="last")

    write_csv_safe(path, total)
    return max(len(total) - before, 0), len(total)


def parse_csv_text(text: str) -> pd.DataFrame:
    if not text.strip():
        return pd.DataFrame()
    return pd.read_csv(StringIO(text))


def normalize_date(raw_date: str) -> str:
    raw = clean_text(raw_date)
    if not raw:
        return ""
    if "/" in raw:
        parts = raw.split("/")
        if len(parts) == 3:
            day, month, year = parts
            if len(year) == 2:
                year = f"20{year}"
            return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
    return raw


def validate_history_df(df: pd.DataFrame):
    df = normalize_columns(df)
    missing = [c for c in HISTORY_REQUIRED if c not in df.columns]
    if missing:
        return False, pd.DataFrame(), f"과거자료 필수 컬럼 부족: {', '.join(missing)}"

    rows = []
    for _, row in df.iterrows():
        date = normalize_date(row.get("date"))
        league = clean_text(row.get("league"))
        home = clean_text(row.get("home_team"))
        away = clean_text(row.get("away_team"))
        hs = safe_score(row.get("home_score"))
        aw = safe_score(row.get("away_score"))

        if not date or not league or not home or not away:
            continue
        if hs == "" or aw == "":
            continue

        match_id = clean_text(row.get("match_id")) or f"hist_{date}_{home}_{away}".replace(" ", "_")
        rows.append({
            "date": date,
            "kickoff_kst": clean_text(row.get("kickoff_kst")),
            "league": league,
            "home_team": home,
            "away_team": away,
            "home_score": str(hs),
            "away_score": str(aw),
            "status": clean_text(row.get("status")) or "FT",
            "source": clean_text(row.get("source")) or "manual_history",
            "match_id": match_id,
        })

    clean_df = pd.DataFrame(rows)
    if clean_df.empty:
        return False, clean_df, "저장 가능한 과거 완료 경기가 없습니다."

    return True, clean_df, f"과거자료 {len(clean_df)}건 정규화 성공"


def validate_upcoming_df(df: pd.DataFrame):
    df = normalize_columns(df)
    missing = [c for c in UPCOMING_REQUIRED if c not in df.columns]
    if missing:
        return False, pd.DataFrame(), f"예정경기 필수 컬럼 부족: {', '.join(missing)}"

    rows = []
    for _, row in df.iterrows():
        date = normalize_date(row.get("date"))
        kickoff = clean_text(row.get("kickoff_kst"))
        league = clean_text(row.get("league"))
        home = clean_text(row.get("home_team"))
        away = clean_text(row.get("away_team"))

        if not date or not league or not home or not away:
            continue

        # 예정경기는 점수가 있으면 안 된다. 점수가 있으면 완료 경기로 판단하여 제외.
        hs = clean_text(row.get("home_score"))
        aw = clean_text(row.get("away_score"))
        if hs or aw:
            continue

        match_id = clean_text(row.get("match_id")) or f"up_{date}_{home}_{away}".replace(" ", "_")
        rows.append({
            "date": date,
            "kickoff_kst": kickoff,
            "league": league,
            "home_team": home,
            "away_team": away,
            "status": clean_text(row.get("status")) or "SCHEDULED",
            "source": clean_text(row.get("source")) or "manual",
            "match_id": match_id,
        })

    clean_df = pd.DataFrame(rows)
    if clean_df.empty:
        return False, clean_df, "저장 가능한 예정 경기가 없습니다."

    return True, clean_df, f"예정경기 {len(clean_df)}건 정규화 성공"


def validate_team_status_df(df: pd.DataFrame):
    df = normalize_columns(df)
    missing = [c for c in TEAM_STATUS_REQUIRED if c not in df.columns]
    if missing:
        return False, pd.DataFrame(), f"팀 현재상태 필수 컬럼 부족: {', '.join(missing)}"

    rows = []
    for _, row in df.iterrows():
        team = clean_text(row.get("team"))
        if not team:
            continue
        rows.append({
            "team": team,
            "coach": clean_text(row.get("coach")),
            "missing_players": clean_text(row.get("missing_players")),
            "key_players": clean_text(row.get("key_players")),
            "note": clean_text(row.get("note")),
            "updated_at": clean_text(row.get("updated_at")) or now_kst_text(),
        })

    clean_df = pd.DataFrame(rows)
    if clean_df.empty:
        return False, clean_df, "저장 가능한 팀 현재상태 자료가 없습니다."

    return True, clean_df, f"팀 현재상태 {len(clean_df)}건 정규화 성공"


def season_candidates(season_code: str):
    clean = clean_text(season_code).replace("/", "")
    candidates = []
    if clean:
        candidates.append(clean)
    if len(clean) == 4 and clean.isdigit():
        reversed_pair = clean[2:] + clean[:2]
        if reversed_pair not in candidates:
            candidates.append(reversed_pair)
    for fallback in ["2526", "2425"]:
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


def url_candidates(season: str, league_code: str):
    return [
        f"https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv",
        f"https://www.football-data.co.uk/mmz4371/{season}/{league_code}.csv",
    ]


def fetch_football_data_uk(season_code: str, league_codes, timeout=10):
    rows = []
    logs = []

    clean_input = clean_text(season_code).replace("/", "")
    if not clean_input.isdigit() or len(clean_input) != 4:
        return pd.DataFrame(), [{
            "source": "football-data.co.uk",
            "ok": False,
            "message": "시즌 코드는 2526처럼 4자리 숫자여야 합니다.",
        }]

    for season in season_candidates(clean_input):
        for code in league_codes:
            code = clean_text(code).upper()
            league_name = LEAGUE_NAMES.get(code, code)

            for url in url_candidates(season, code):
                log = {
                    "source": "football-data.co.uk",
                    "season": season,
                    "league_code": code,
                    "league": league_name,
                    "url": url,
                    "ok": False,
                    "http_status": "",
                    "rows": 0,
                    "message": "",
                }

                try:
                    response = requests.get(
                        url,
                        timeout=timeout,
                        headers={"User-Agent": "MARU-Sports-Analyzer/clean-real"},
                    )
                    log["http_status"] = str(response.status_code)

                    if response.status_code != 200:
                        log["message"] = f"HTTP {response.status_code}"
                        logs.append(log)
                        continue

                    csv_text = response.content.decode("utf-8", errors="ignore")
                    raw_df = pd.read_csv(StringIO(csv_text))
                    ok, clean_df, msg = validate_history_df(raw_df.assign(league=league_name, source=f"football_data_uk_{season}_{code}"))

                    if not ok:
                        log["message"] = msg
                        logs.append(log)
                        continue

                    # Football-Data 원본에는 league/source가 assign으로 들어간 상태
                    for _, row in clean_df.iterrows():
                        row_dict = row.to_dict()
                        row_dict["league"] = league_name
                        row_dict["source"] = f"football_data_uk_{season}_{code}"
                        row_dict["match_id"] = f"fd_{season}_{code}_{row_dict['date']}_{row_dict['home_team']}_{row_dict['away_team']}".replace(" ", "_")
                        rows.append(row_dict)

                    log["ok"] = True
                    log["rows"] = len(clean_df)
                    log["message"] = f"{len(clean_df)}건 변환"
                    logs.append(log)
                    break

                except Exception as exc:
                    log["message"] = str(exc)
                    logs.append(log)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["match_id"], keep="last")
    return df, logs


def get_team_history(history_df: pd.DataFrame, team: str, league: str = "") -> pd.DataFrame:
    if history_df.empty:
        return pd.DataFrame()

    df = history_df.copy()
    if league and "league" in df.columns:
        league_df = df[df["league"].astype(str) == league]
        if not league_df.empty:
            df = league_df

    mask = (df["home_team"].astype(str) == team) | (df["away_team"].astype(str) == team)
    df = df[mask].copy()

    if "date" in df.columns:
        df = df.sort_values("date", ascending=False)

    return df


def calc_team_stats(history_df: pd.DataFrame, team: str, league: str = "", n: int = 10):
    df = get_team_history(history_df, team, league).head(n)
    if df.empty:
        return {
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "avg_for": 0,
            "avg_against": 0,
            "points": 0,
            "form_text": "자료없음",
        }

    wins = draws = losses = goals_for = goals_against = 0
    form = []

    for _, row in df.iterrows():
        home = clean_text(row.get("home_team"))
        away = clean_text(row.get("away_team"))
        hs = safe_score(row.get("home_score"))
        aw = safe_score(row.get("away_score"))
        if hs == "" or aw == "":
            continue

        if team == home:
            gf, ga = hs, aw
        elif team == away:
            gf, ga = aw, hs
        else:
            continue

        goals_for += gf
        goals_against += ga

        if gf > ga:
            wins += 1
            form.append("W")
        elif gf == ga:
            draws += 1
            form.append("D")
        else:
            losses += 1
            form.append("L")

    matches = wins + draws + losses
    points = wins * 3 + draws
    return {
        "matches": matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "avg_for": round(goals_for / matches, 2) if matches else 0,
        "avg_against": round(goals_against / matches, 2) if matches else 0,
        "points": points,
        "form_text": "-".join(form[:5]) if form else "자료없음",
    }


def status_for_team(team_status_df: pd.DataFrame, team: str):
    if team_status_df.empty or "team" not in team_status_df.columns:
        return {}
    exact = team_status_df[team_status_df["team"].astype(str).str.lower() == team.lower()]
    if exact.empty:
        return {}
    return exact.iloc[-1].to_dict()


def count_missing_players(status: dict):
    text = clean_text(status.get("missing_players"))
    if not text:
        return 0
    parts = [p.strip() for p in text.replace("/", ",").replace("|", ",").split(",") if p.strip()]
    return len(parts)


def analyze_fixture(fixture: dict, history_df: pd.DataFrame, team_status_df: pd.DataFrame):
    home = clean_text(fixture.get("home_team"))
    away = clean_text(fixture.get("away_team"))
    league = clean_text(fixture.get("league"))

    home_stats = calc_team_stats(history_df, home, league, n=10)
    away_stats = calc_team_stats(history_df, away, league, n=10)

    home_status = status_for_team(team_status_df, home)
    away_status = status_for_team(team_status_df, away)

    home_missing = count_missing_players(home_status)
    away_missing = count_missing_players(away_status)

    data_points = home_stats["matches"] + away_stats["matches"]
    if data_points < 4:
        return {
            "match": f"{home} vs {away}",
            "pick": "분석불가",
            "confidence": 0,
            "risk": "높음",
            "message": "양팀 과거자료가 부족합니다.",
            "home_form": home_stats["form_text"],
            "away_form": away_stats["form_text"],
            "home_avg": home_stats["avg_for"],
            "away_avg": away_stats["avg_for"],
            "home_missing": home_missing,
            "away_missing": away_missing,
            "data_points": data_points,
        }

    home_power = home_stats["points"] + home_stats["goals_for"] - home_stats["goals_against"]
    away_power = away_stats["points"] + away_stats["goals_for"] - away_stats["goals_against"]

    # 홈 어드밴티지와 현재상태 리스크 반영
    home_score = home_power + 2 - (home_missing * 1.5)
    away_score = away_power - (away_missing * 1.5)

    diff = home_score - away_score
    total_goal_flow = home_stats["avg_for"] + away_stats["avg_for"]

    if diff >= 4:
        pick = "홈 우세"
    elif diff <= -4:
        pick = "원정 우세"
    else:
        pick = "접전/무승부 주의"

    if data_points >= 16 and abs(diff) >= 5:
        confidence = 72
    elif data_points >= 10 and abs(diff) >= 3:
        confidence = 63
    else:
        confidence = 52

    risk = "낮음" if confidence >= 70 else "중간" if confidence >= 58 else "높음"

    notes = []
    notes.append(f"최근자료 {data_points}경기 기준")
    notes.append(f"홈 최근폼 {home_stats['form_text']}")
    notes.append(f"원정 최근폼 {away_stats['form_text']}")
    if home_missing:
        notes.append(f"홈 결장/부상 입력 {home_missing}명")
    if away_missing:
        notes.append(f"원정 결장/부상 입력 {away_missing}명")
    if total_goal_flow >= 3.0:
        notes.append("득점 흐름 높음")
    elif total_goal_flow <= 2.0:
        notes.append("득점 흐름 낮음")

    return {
        "match": f"{home} vs {away}",
        "date_time": f"{clean_text(fixture.get('date'))} {clean_text(fixture.get('kickoff_kst'))}",
        "league": league,
        "pick": pick,
        "confidence": confidence,
        "risk": risk,
        "message": " / ".join(notes),
        "home_form": home_stats["form_text"],
        "away_form": away_stats["form_text"],
        "home_avg": home_stats["avg_for"],
        "away_avg": away_stats["avg_for"],
        "home_missing": home_missing,
        "away_missing": away_missing,
        "data_points": data_points,
    }


def render_card(result: dict):
    st.markdown(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:16px;padding:18px;margin-bottom:14px;background:#ffffff;">
            <div style="font-size:14px;color:#6b7280;">{result.get('league','')} · {result.get('date_time','')}</div>
            <div style="font-size:24px;font-weight:800;margin:6px 0;">{result.get('match','')}</div>
            <div style="display:flex;gap:10px;flex-wrap:wrap;margin:8px 0;">
                <span style="background:#eef2ff;padding:6px 10px;border-radius:999px;">판단: <b>{result.get('pick','')}</b></span>
                <span style="background:#ecfdf5;padding:6px 10px;border-radius:999px;">신뢰도: <b>{result.get('confidence',0)}%</b></span>
                <span style="background:#fff7ed;padding:6px 10px;border-radius:999px;">위험도: <b>{result.get('risk','')}</b></span>
                <span style="background:#f3f4f6;padding:6px 10px;border-radius:999px;">자료: <b>{result.get('data_points',0)}경기</b></span>
            </div>
            <div style="font-size:14px;color:#374151;line-height:1.55;">{result.get('message','')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.markdown(
        """
        <div style="padding:20px 0 8px 0;">
            <div style="font-size:34px;font-weight:900;">⚽ MARU SPORTS ANALYZER</div>
            <div style="font-size:15px;color:#6b7280;margin-top:6px;">
                실버전 · 자동구매 없음 · 자동결제 없음 · 자료 없으면 분석불가 표시
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status(history_df, upcoming_df, team_status_df, results):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("과거 경기자료", len(history_df))
    c2.metric("예정 경기", len(upcoming_df))
    c3.metric("팀 현재상태", len(team_status_df))
    c4.metric("추천카드", len(results))


def render_collect_tab():
    st.subheader("📥 과거 경기결과 수집")
    st.caption("Football-Data.co.uk 완료 경기만 가져옵니다. 앱 시작 시 자동호출하지 않고, 버튼을 눌렀을 때만 수집합니다.")

    col1, col2 = st.columns([1, 2])
    with col1:
        season_code = st.text_input("시즌 코드", value="2526", help="예: 2025/26 시즌은 2526")
    with col2:
        selected = st.multiselect(
            "리그 선택",
            options=list(LEAGUE_NAMES.keys()),
            default=["E0", "D1", "SP1"],
            format_func=lambda x: f"{x} · {LEAGUE_NAMES[x]}",
        )

    if st.button("실제 과거자료 수집/저장", type="primary"):
        if not selected:
            st.warning("리그를 하나 이상 선택하세요.")
            return

        with st.spinner("Football-Data.co.uk 수집 중..."):
            df_new, logs = fetch_football_data_uk(season_code, selected)

        with st.expander("수집 로그", expanded=True):
            st.dataframe(pd.DataFrame(logs), width="stretch")

        if df_new.empty:
            st.error("수집된 완료 경기 데이터가 없습니다. 시즌 코드/리그/HTTP 상태를 확인하세요.")
        else:
            added, total = merge_csv(HISTORY_PATH, df_new, ["match_id"])
            st.success(f"과거자료 저장 완료: 신규/정리 {added}건 · 전체 {total}건")
            st.dataframe(df_new.head(30), width="stretch")


def render_upcoming_tab():
    st.subheader("📅 예정 경기 입력")
    st.caption("추천카드는 여기 저장된 예정 경기만 대상으로 만듭니다. 예정경기는 점수가 없어야 정상입니다.")

    sample = """date,kickoff_kst,league,home_team,away_team,status,source,match_id
2026-07-10,20:00,잉글랜드 프리미어리그,Liverpool,Man City,SCHEDULED,manual,manual_001
2026-07-10,22:00,잉글랜드 프리미어리그,Arsenal,Chelsea,SCHEDULED,manual,manual_002
"""
    st.download_button("예정 경기 샘플 다운로드", sample.encode("utf-8-sig"), "upcoming_fixtures_sample.csv", "text/csv")

    text = st.text_area("예정 경기 CSV 붙여넣기", value=sample, height=150)
    uploaded = st.file_uploader("또는 예정 경기 CSV 업로드", type=["csv"], key="upcoming_upload")

    df_input = pd.DataFrame()
    if uploaded is not None:
        df_input = pd.read_csv(uploaded)
    elif text.strip():
        df_input = parse_csv_text(text)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("예정 경기 검사"):
            ok, clean_df, msg = validate_upcoming_df(df_input)
            if ok:
                st.success(msg)
                st.dataframe(clean_df, width="stretch")
            else:
                st.error(msg)

    with col2:
        if st.button("예정 경기 저장", type="primary"):
            ok, clean_df, msg = validate_upcoming_df(df_input)
            if not ok:
                st.error(msg)
            else:
                added, total = merge_csv(UPCOMING_PATH, clean_df, ["match_id"])
                st.success(f"예정 경기 저장 완료: 신규/정리 {added}건 · 전체 {total}건")
                st.dataframe(clean_df, width="stretch")

    saved = read_csv_safe(UPCOMING_PATH)
    with st.expander("저장된 예정 경기", expanded=False):
        if saved.empty:
            st.info("저장된 예정 경기가 없습니다.")
        else:
            st.dataframe(saved, width="stretch")


def render_team_status_tab():
    st.subheader("🧑‍💼 감독·선수·부상 자료")
    st.caption("무료 자동자료가 부족한 부분은 우선 CSV로 안정화합니다. 이 자료는 추천 신뢰도와 위험도에 반영됩니다.")

    sample = """team,coach,missing_players,key_players,note
Liverpool,Arne Slot,,Salah; Van Dijk,주전 유지 확인 필요
Man City,Pep Guardiola,,Haaland; Foden,로테이션 가능성 확인
Arsenal,Mikel Arteta,,Saka; Odegaard,부상자 발표 확인
Chelsea,Enzo Maresca,,Palmer,선발 변동성 주의
"""
    st.download_button("팀 현재상태 샘플 다운로드", sample.encode("utf-8-sig"), "team_status_sample.csv", "text/csv")

    text = st.text_area("팀 현재상태 CSV 붙여넣기", value=sample, height=150)
    uploaded = st.file_uploader("또는 팀 현재상태 CSV 업로드", type=["csv"], key="team_status_upload")

    df_input = pd.DataFrame()
    if uploaded is not None:
        df_input = pd.read_csv(uploaded)
    elif text.strip():
        df_input = parse_csv_text(text)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("팀 현재상태 검사"):
            ok, clean_df, msg = validate_team_status_df(df_input)
            if ok:
                st.success(msg)
                st.dataframe(clean_df, width="stretch")
            else:
                st.error(msg)

    with col2:
        if st.button("팀 현재상태 저장", type="primary"):
            ok, clean_df, msg = validate_team_status_df(df_input)
            if not ok:
                st.error(msg)
            else:
                added, total = merge_csv(TEAM_STATUS_PATH, clean_df, ["team"])
                st.success(f"팀 현재상태 저장 완료: 신규/정리 {added}건 · 전체 {total}건")
                st.dataframe(clean_df, width="stretch")

    saved = read_csv_safe(TEAM_STATUS_PATH)
    with st.expander("저장된 팀 현재상태", expanded=False):
        if saved.empty:
            st.info("저장된 팀 현재상태 자료가 없습니다.")
        else:
            st.dataframe(saved, width="stretch")


def render_analysis_tab(history_df, upcoming_df, team_status_df):
    st.subheader("🔥 분석 결과")
    st.caption("예정 경기 + 과거 결과 + 감독/선수/부상 자료를 분리해서 계산합니다.")

    if upcoming_df.empty:
        st.warning("예정 경기가 없습니다. 먼저 예정 경기 탭에서 upcoming_fixtures.csv를 저장하세요.")
        return []

    if history_df.empty:
        st.error("과거 경기자료가 없습니다. 먼저 과거자료 수집 탭에서 실제 자료를 저장하세요.")
        return []

    results = []
    for _, fixture in upcoming_df.iterrows():
        result = analyze_fixture(fixture.to_dict(), history_df, team_status_df)
        results.append(result)

    for result in results:
        render_card(result)

    with st.expander("분석 원자료", expanded=False):
        st.dataframe(pd.DataFrame(results), width="stretch")

    return results


def render_data_tab(history_df, upcoming_df, team_status_df):
    st.subheader("📊 저장 데이터")
    tab1, tab2, tab3 = st.tabs(["과거자료", "예정경기", "팀 현재상태"])

    with tab1:
        if history_df.empty:
            st.info("과거자료 없음")
        else:
            st.dataframe(history_df.tail(100), width="stretch")
            st.download_button(
                "과거자료 CSV 다운로드",
                history_df.to_csv(index=False).encode("utf-8-sig"),
                "history_matches.csv",
                "text/csv",
            )

    with tab2:
        if upcoming_df.empty:
            st.info("예정경기 없음")
        else:
            st.dataframe(upcoming_df, width="stretch")
            st.download_button(
                "예정경기 CSV 다운로드",
                upcoming_df.to_csv(index=False).encode("utf-8-sig"),
                "upcoming_fixtures.csv",
                "text/csv",
            )

    with tab3:
        if team_status_df.empty:
            st.info("팀 현재상태 없음")
        else:
            st.dataframe(team_status_df, width="stretch")
            st.download_button(
                "팀 현재상태 CSV 다운로드",
                team_status_df.to_csv(index=False).encode("utf-8-sig"),
                "team_status.csv",
                "text/csv",
            )


def main():
    st.set_page_config(
        page_title="MARU SPORTS ANALYZER",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    ensure_cache_dir()
    render_header()

    history_df = read_csv_safe(HISTORY_PATH)
    upcoming_df = read_csv_safe(UPCOMING_PATH)
    team_status_df = read_csv_safe(TEAM_STATUS_PATH)

    # 완료/예정 데이터 재필터링
    if not history_df.empty:
        ok, history_df_clean, _ = validate_history_df(history_df)
        history_df = history_df_clean if ok else pd.DataFrame()

    if not upcoming_df.empty:
        ok, upcoming_df_clean, _ = validate_upcoming_df(upcoming_df)
        upcoming_df = upcoming_df_clean if ok else pd.DataFrame()

    if not team_status_df.empty:
        ok, team_status_df_clean, _ = validate_team_status_df(team_status_df)
        team_status_df = team_status_df_clean if ok else pd.DataFrame()

    results_preview = []
    if not upcoming_df.empty and not history_df.empty:
        for _, fixture in upcoming_df.iterrows():
            results_preview.append(analyze_fixture(fixture.to_dict(), history_df, team_status_df))

    render_status(history_df, upcoming_df, team_status_df, results_preview)

    st.markdown("---")

    tabs = st.tabs([
        "🔥 분석",
        "📅 예정경기",
        "📥 과거자료 수집",
        "🧑‍💼 감독·선수",
        "📊 저장데이터",
    ])

    with tabs[0]:
        render_analysis_tab(history_df, upcoming_df, team_status_df)

    with tabs[1]:
        render_upcoming_tab()

    with tabs[2]:
        render_collect_tab()

    with tabs[3]:
        render_team_status_tab()

    with tabs[4]:
        render_data_tab(history_df, upcoming_df, team_status_df)

    st.markdown("---")
    st.caption(f"현재 시간: {now_kst_text()} · 자동구매/자동결제 없음 · 자료 없으면 분석불가")


if __name__ == "__main__":
    main()
