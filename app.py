import os
import tempfile
from io import StringIO
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

import pandas as pd
import requests
import streamlit as st

# ==========================================================
# MARU SPORTS ANALYZER - PROTO FIXTURE HUB V5 BACKEND DIAGNOSIS
# ----------------------------------------------------------
# 사진 1: 라이브스코어/토토 일정표 = 경기 목록 기준만
# 사진 2: 프로토 승부식 = 승무패/핸디/언오버/전반/더블찬스/SUM/승패/한경기조합/기타
# 9. PC 모니터링과 전체실행에 실제 실행 버튼을 둔다.
# 10. 일정표는 매일 수동 입력이 아니라 자동수집 버튼/Actions로 갱신한다.
# 11. 허브/구글시트가 없어도 가상 백엔드 테스트와 payload 검사를 기본 탑재한다.
# 원칙:
# 1. 특정 사이트 하나에 의존하지 않는다.
# 2. 라이브스코어는 일정표 기준만 사용한다.
# 3. source_* 원본 저장, standard_* 표준화, output 추천/허브 로그 분리.
# 4. 분석 엔진은 standard_*만 읽는다.
# 5. 추천카드는 예정 경기만 대상으로 만든다.
# 6. 샘플/TEST/가짜 추천카드는 자동 생성하지 않는다.
# 7. 자료 부족하면 분석불가/자료부족 표시.
# 8. 자동구매/자동결제 없음.
# ==========================================================

KST = timezone(timedelta(hours=9))
DATA_DIR = "data"

SOURCE_FILES = {
    "livescore_fixtures": "source_livescore_fixtures.csv",       # 일정표만
    "livescore_team_form": "source_livescore_team_form.csv",     # 홈/원정/최근 흐름 복사자료
    "livescore_h2h": "source_livescore_h2h.csv",                 # 상대전적 복사자료
    "livescore_news": "source_livescore_news.csv",               # 공지/뉴스 복사자료
    "football_data": "source_football_data.csv",                 # 과거 결과 자동/CSV
    "sportmonks": "source_sportmonks.csv",                       # 보조 source
    "thesportsdb": "source_thesportsdb.csv",                     # 보조 source
    "proto_markets": "source_proto_markets.csv",                 # 실제 승부식/기준점 수동 입력
    "manual": "source_manual.csv",                               # 감독/부상/라인업/이적/메모
}

STANDARD_FILES = {
    "upcoming_fixtures": "standard_upcoming_fixtures.csv",
    "history_matches": "standard_history_matches.csv",
    "team_form": "standard_team_form.csv",
    "team_home_away": "standard_team_home_away.csv",
    "h2h": "standard_h2h.csv",
    "coaches": "standard_coaches.csv",
    "transfers": "standard_transfers.csv",
    "injuries": "standard_injuries.csv",
    "lineups": "standard_lineups.csv",
    "news_flags": "standard_news_flags.csv",
    "markets": "standard_markets.csv",
}

OUTPUT_FILES = {
    "analysis_scores": "analysis_scores.csv",
    "mobile_recommendations": "mobile_recommendations.csv",
    "hub_send_logs": "hub_send_logs.csv",
    "error_logs": "error_logs.csv",
    "run_logs": "run_logs.csv",
}

LEAGUE_NAMES = {
    "E0": "잉글랜드 프리미어리그", "E1": "잉글랜드 챔피언십",
    "D1": "독일 분데스리가", "D2": "독일 분데스리가2",
    "SP1": "스페인 라리가", "SP2": "스페인 세군다",
    "I1": "이탈리아 세리에A", "I2": "이탈리아 세리에B",
    "F1": "프랑스 리그1", "F2": "프랑스 리그2",
    "N1": "네덜란드 에레디비시", "P1": "포르투갈 프리메이라",
    "B1": "벨기에 주필러리그", "SC0": "스코틀랜드 프리미어십",
}

SPORTS = ["축구", "야구", "농구", "배구", "하키", "e스포츠", "기타"]

MARKET_TEMPLATES = [
    {"market_type": "승무패", "market_label": "승무패", "line": "", "choices": "홈승|무|원정승", "need": "기본"},
    {"market_type": "핸디캡", "market_label": "핸디캡", "line": "+1.0/-1.0", "choices": "홈핸디|원정핸디", "need": "기준점"},
    {"market_type": "언더/오버", "market_label": "언더/오버", "line": "2.5", "choices": "언더|오버", "need": "기준점"},
    {"market_type": "전반", "market_label": "전반", "line": "전반", "choices": "전반홈|전반무|전반원정", "need": "전반자료"},
    {"market_type": "더블찬스", "market_label": "더블찬스", "line": "", "choices": "홈/무|홈/원정|무/원정", "need": "안전형"},
    {"market_type": "SUM", "market_label": "SUM", "line": "합계", "choices": "홀|짝|구간", "need": "특수자료"},
    {"market_type": "승패/승5패", "market_label": "승패/승5패", "line": "점수차", "choices": "대승|승|무|패|대패", "need": "점수차"},
    {"market_type": "한경기조합", "market_label": "한경기조합", "line": "조합", "choices": "승무패+언오버|핸디+언오버", "need": "복합"},
    {"market_type": "한경기구매", "market_label": "한경기 구매", "line": "단일경기", "choices": "가능|불가", "need": "구매방식"},
    {"market_type": "기타", "market_label": "기타", "line": "", "choices": "코너|카드|선수|특수", "need": "특수자료"},
]

# TheSportsDB는 일정표 자동수집용 보조 source입니다.
# 라이브스코어에 의존하지 않고, 오늘/예정 경기 목록을 자동으로 채우는 용도입니다.
THESPORTSDB_DEFAULT_LEAGUES = {
    "EPL": "4328",
    "English Championship": "4329",
    "German Bundesliga": "4331",
    "Italian Serie A": "4332",
    "French Ligue 1": "4334",
    "Spanish La Liga": "4335",
}

COLUMN_MAP = {
    "날짜": "date", "경기일": "date", "일자": "date", "시간": "kickoff_kst", "킥오프": "kickoff_kst", "경기시간": "kickoff_kst",
    "종목": "sport", "스포츠": "sport", "리그": "league", "대회": "league", "국가": "country",
    "홈팀": "home_team", "홈": "home_team", "원정팀": "away_team", "원정": "away_team", "팀1": "home_team", "팀2": "away_team",
    "홈점수": "home_score", "원정점수": "away_score", "스코어홈": "home_score", "스코어원정": "away_score",
    "상태": "status", "출처": "source", "경기ID": "match_id", "경기아이디": "match_id",
    "배당홈": "odds_home", "배당무": "odds_draw", "배당원정": "odds_away", "기준점": "line",
    "시장": "market_type", "승부식": "market_type", "선택지": "choices",
    "팀": "team", "팀명": "team", "감독": "coach", "감독취임일": "coach_start_date", "취임일": "coach_start_date",
    "부상": "injuries", "결장": "missing_players", "출장정지": "suspended_players", "주전부상": "key_injuries",
    "핵심선수": "key_players", "주요선수": "key_players", "영입": "transfers_in", "이적": "transfers_out", "스카우트": "scout_note",
    "라인업": "expected_lineup", "예상라인업": "expected_lineup", "포메이션": "formation", "메모": "note", "뉴스": "news", "공지": "news", "비고": "note",
    "최근5경기": "recent5", "최근10경기": "recent10", "홈승": "home_wins", "홈무": "home_draws", "홈패": "home_losses",
    "원정승": "away_wins", "원정무": "away_draws", "원정패": "away_losses", "상대전적": "h2h_note",
}


def ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def path_for(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def clean_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null", "nat"}:
        return ""
    return text


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    out.columns = [clean_text(c) for c in out.columns]
    out = out.rename(columns={c: COLUMN_MAP.get(c, c) for c in out.columns})
    return out


def normalize_date(raw) -> str:
    text = clean_text(raw)
    if not text:
        return ""
    if " " in text:
        text = text.split(" ")[0]
    for sep in ["/", "."]:
        if sep in text:
            parts = [p.strip() for p in text.split(sep)]
            if len(parts) == 3:
                if len(parts[0]) == 4:
                    y, m, d = parts
                else:
                    d, m, y = parts
                    if len(y) == 2:
                        y = "20" + y
                return f"{y.zfill(4)}-{m.zfill(2)}-{d.zfill(2)}"
    return text


def safe_int(value, default=0) -> int:
    text = clean_text(value)
    if not text:
        return default
    try:
        return int(float(text))
    except Exception:
        return default


def safe_float(value, default=0.0) -> float:
    text = clean_text(value)
    if not text:
        return default
    try:
        return float(text)
    except Exception:
        return default


def read_csv(filename: str) -> pd.DataFrame:
    ensure_data_dir()
    full_path = path_for(filename)
    if not os.path.exists(full_path):
        return pd.DataFrame()
    try:
        return normalize_columns(pd.read_csv(full_path, dtype=str).fillna(""))
    except Exception as exc:
        log_error("read_csv", filename, str(exc))
        return pd.DataFrame()


def write_csv(filename: str, df: pd.DataFrame) -> None:
    ensure_data_dir()
    if df is None:
        df = pd.DataFrame()
    df.to_csv(path_for(filename), index=False, encoding="utf-8-sig")


def merge_csv(filename: str, df_new: pd.DataFrame, subset: List[str]) -> Tuple[int, int]:
    df_new = normalize_columns(df_new)
    if df_new.empty:
        return 0, len(read_csv(filename))
    current = read_csv(filename)
    before = len(current)
    if current.empty:
        total = df_new.copy()
    else:
        total = pd.concat([current, df_new], ignore_index=True).fillna("")
    usable_subset = [c for c in subset if c in total.columns]
    if usable_subset:
        total = total.drop_duplicates(subset=usable_subset, keep="last")
    else:
        total = total.drop_duplicates(keep="last")
    write_csv(filename, total)
    return max(len(total) - before, 0), len(total)


def log_error(stage: str, target: str, message: str) -> None:
    try:
        row = pd.DataFrame([{"time": now_kst(), "stage": stage, "target": target, "message": clean_text(message)[:500]}])
        merge_csv(OUTPUT_FILES["error_logs"], row, ["time", "stage", "target", "message"])
    except Exception:
        pass


def log_run(stage: str, message: str, rows: int = 0) -> None:
    row = pd.DataFrame([{"time": now_kst(), "stage": stage, "message": message, "rows": rows}])
    merge_csv(OUTPUT_FILES["run_logs"], row, ["time", "stage", "message"])


def parse_csv_text(text: str) -> pd.DataFrame:
    if not clean_text(text):
        return pd.DataFrame()
    return normalize_columns(pd.read_csv(StringIO(text)))


def add_source_meta(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    df = normalize_columns(df)
    if df.empty:
        return df
    if "source" not in df.columns:
        df["source"] = source_name
    df["source"] = df["source"].replace("", source_name)
    df["collected_at"] = now_kst()
    return df


def file_count(filename: str) -> int:
    return len(read_csv(filename))


def preview_df(df: pd.DataFrame, rows: int = 80) -> pd.DataFrame:
    if df.empty:
        return df
    return df.tail(rows)


# ---------------------- 일정표 자동수집 ----------------------

def secret_value(key: str, default: str = "") -> str:
    try:
        value = st.secrets.get(key, default)
        return str(value) if value is not None else default
    except Exception:
        return default


def parse_csv_list(text: str) -> List[str]:
    return [x.strip() for x in clean_text(text).replace("\n", ",").split(",") if x.strip()]


def parse_league_id_text(text: str) -> Dict[str, str]:
    """입력 예: EPL=4328,LaLiga=4335 또는 4328,4335"""
    out: Dict[str, str] = {}
    for idx, item in enumerate(parse_csv_list(text)):
        if "=" in item:
            name, league_id = item.split("=", 1)
            out[clean_text(name) or f"league_{idx+1}"] = clean_text(league_id)
        else:
            out[f"league_{idx+1}"] = clean_text(item)
    return {k: v for k, v in out.items() if v}


def kst_time_from_timestamp(timestamp_text: str, fallback_time: str = "") -> Tuple[str, str]:
    ts = clean_text(timestamp_text)
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_kst = dt.astimezone(KST)
            return dt_kst.strftime("%Y-%m-%d"), dt_kst.strftime("%H:%M")
        except Exception:
            pass
    return "", clean_text(fallback_time)[:5]


def normalize_thesportsdb_events(events: List[Dict], source_name: str = "thesportsdb_schedule") -> pd.DataFrame:
    rows = []
    for ev in events or []:
        home = clean_text(ev.get("strHomeTeam"))
        away = clean_text(ev.get("strAwayTeam"))
        if not home or not away:
            continue
        date_from_ts, time_from_ts = kst_time_from_timestamp(ev.get("strTimestamp"), ev.get("strTime"))
        date = date_from_ts or normalize_date(ev.get("dateEvent"))
        kickoff = time_from_ts or clean_text(ev.get("strTime"))[:5]
        if not date:
            continue
        status_raw = clean_text(ev.get("strStatus")) or clean_text(ev.get("strProgress")) or "SCHEDULED"
        home_score = clean_text(ev.get("intHomeScore"))
        away_score = clean_text(ev.get("intAwayScore"))
        # 일정표 source는 예정 경기 중심. 종료/점수 있는 경기는 현재 추천 대상에서 제외되도록 저장만 하되 status를 유지.
        status = "SCHEDULED" if (not home_score and not away_score and not is_finished_status(status_raw)) else status_raw
        match_id = clean_text(ev.get("idEvent")) or f"tsdb_{date}_{home}_{away}".replace(" ", "_")
        rows.append({
            "match_id": match_id,
            "date": date,
            "kickoff_kst": kickoff,
            "sport": clean_text(ev.get("strSport")) or "축구",
            "country": clean_text(ev.get("strCountry")),
            "league": clean_text(ev.get("strLeague")),
            "home_team": home,
            "away_team": away,
            "status": status,
            "source": source_name,
            "home_score": home_score,
            "away_score": away_score,
            "odds_home": "",
            "odds_draw": "",
            "odds_away": "",
            "collected_at": now_kst(),
        })
    return pd.DataFrame(rows)


def fetch_thesportsdb_next_league(league_ids: Dict[str, str], api_key: str = "123", timeout: int = 15) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows, logs = [], []
    api_key = clean_text(api_key) or "123"
    for league_name, league_id in league_ids.items():
        url = f"https://www.thesportsdb.com/api/v1/json/{api_key}/eventsnextleague.php?id={league_id}"
        log = {"time": now_kst(), "source": "thesportsdb_schedule", "league_name": league_name, "league_id": league_id, "url": url.replace(api_key, "***"), "ok": "N", "rows": 0, "message": ""}
        try:
            res = requests.get(url, timeout=timeout, headers={"User-Agent": "MARU-Sports-Analyzer/fixture-auto"})
            log["http_status"] = str(res.status_code)
            if res.status_code != 200:
                log["message"] = f"HTTP {res.status_code}"
                logs.append(log)
                continue
            data = res.json()
            events = data.get("events") or data.get("event") or []
            df = normalize_thesportsdb_events(events, source_name=f"thesportsdb_nextleague_{league_id}")
            if not df.empty:
                rows.append(df)
                log["ok"] = "Y"
                log["rows"] = len(df)
                log["message"] = "일정표 변환 성공"
            else:
                log["message"] = "변환 가능한 일정 없음"
            logs.append(log)
        except Exception as exc:
            log["message"] = str(exc)[:300]
            logs.append(log)
    out = pd.concat(rows, ignore_index=True).drop_duplicates(subset=["match_id"], keep="last") if rows else pd.DataFrame()
    return out, pd.DataFrame(logs)


def normalize_custom_fixture_payload(payload, source_name: str) -> pd.DataFrame:
    if isinstance(payload, list):
        return normalize_thesportsdb_events(payload, source_name=source_name)
    if isinstance(payload, dict):
        for key in ["events", "event", "fixtures", "matches", "data"]:
            value = payload.get(key)
            if isinstance(value, list):
                # 먼저 TheSportsDB 형태를 시도하고, 실패하면 일반 컬럼 매핑으로 처리.
                tsdb_df = normalize_thesportsdb_events(value, source_name=source_name)
                if not tsdb_df.empty:
                    return tsdb_df
                return normalize_columns(pd.DataFrame(value))
    return pd.DataFrame()


def fetch_custom_fixture_urls(urls: List[str], timeout: int = 15) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows, logs = [], []
    for url in urls:
        safe_url = url.split("?")[0] + ("?..." if "?" in url else "")
        log = {"time": now_kst(), "source": "custom_fixture_url", "url": safe_url, "ok": "N", "rows": 0, "message": ""}
        try:
            res = requests.get(url, timeout=timeout, headers={"User-Agent": "MARU-Sports-Analyzer/fixture-auto"})
            log["http_status"] = str(res.status_code)
            if res.status_code != 200:
                log["message"] = f"HTTP {res.status_code}"
                logs.append(log)
                continue
            content_type = res.headers.get("content-type", "").lower()
            if "json" in content_type or res.text.strip().startswith(("{", "[")):
                df = normalize_custom_fixture_payload(res.json(), source_name="custom_fixture_url")
            else:
                df = normalize_columns(pd.read_csv(StringIO(res.content.decode("utf-8", errors="ignore"))))
            if not df.empty and "match_id" not in df.columns:
                df["match_id"] = [f"auto_{normalize_date(r.get('date'))}_{clean_text(r.get('home_team'))}_{clean_text(r.get('away_team'))}".replace(" ", "_") for _, r in df.iterrows()]
            if not df.empty:
                df = add_source_meta(df, "custom_fixture_url")
                rows.append(df)
                log["ok"] = "Y"
                log["rows"] = len(df)
                log["message"] = "일정표 변환 성공"
            else:
                log["message"] = "변환 가능한 일정 없음"
            logs.append(log)
        except Exception as exc:
            log["message"] = str(exc)[:300]
            logs.append(log)
    out = pd.concat(rows, ignore_index=True).drop_duplicates(subset=["match_id"], keep="last") if rows else pd.DataFrame()
    return out, pd.DataFrame(logs)


def quick_collect_fixtures(league_ids: Dict[str, str] = None, custom_urls: List[str] = None) -> Tuple[int, int, pd.DataFrame]:
    """버튼/GitHub Actions 실행용: 일정표를 자동 수집해 source_livescore_fixtures.csv에 저장."""
    league_ids = league_ids or parse_league_id_text(secret_value("THESPORTSDB_LEAGUE_IDS", "")) or THESPORTSDB_DEFAULT_LEAGUES
    api_key = secret_value("THESPORTSDB_API_KEY", "123")
    custom_urls = custom_urls if custom_urls is not None else parse_csv_list(secret_value("AUTO_FIXTURE_URLS", ""))
    frames, logs = [], []
    if league_ids:
        df_tsdb, log_tsdb = fetch_thesportsdb_next_league(league_ids, api_key=api_key)
        if not df_tsdb.empty:
            frames.append(df_tsdb)
        if not log_tsdb.empty:
            logs.append(log_tsdb)
    if custom_urls:
        df_custom, log_custom = fetch_custom_fixture_urls(custom_urls)
        if not df_custom.empty:
            frames.append(df_custom)
        if not log_custom.empty:
            logs.append(log_custom)
    log_df = pd.concat(logs, ignore_index=True) if logs else pd.DataFrame()
    if not log_df.empty:
        merge_csv(OUTPUT_FILES["run_logs"], log_df, ["time", "source", "url"])
    if not frames:
        return 0, file_count(SOURCE_FILES["livescore_fixtures"]), log_df
    df_all = pd.concat(frames, ignore_index=True).fillna("")
    if "match_id" not in df_all.columns:
        df_all["match_id"] = [f"auto_{normalize_date(r.get('date'))}_{clean_text(r.get('home_team'))}_{clean_text(r.get('away_team'))}".replace(" ", "_") for _, r in df_all.iterrows()]
    added, total = merge_csv(SOURCE_FILES["livescore_fixtures"], df_all, ["match_id", "date", "home_team", "away_team"])
    return added, total, log_df

# ---------------------- football-data ----------------------

def auto_season_codes() -> List[str]:
    now = datetime.now(KST)
    start_year = now.year if now.month >= 7 else now.year - 1
    codes = []
    for sy in [start_year + 1, start_year, start_year - 1, start_year - 2, start_year - 3]:
        code = f"{str(sy)[-2:]}{str(sy + 1)[-2:]}"
        if code not in codes:
            codes.append(code)
    for fallback in ["2627", "2526", "2425", "2324", "2223"]:
        if fallback not in codes:
            codes.append(fallback)
    return codes


def football_url_candidates(season: str, league_code: str) -> List[str]:
    return [
        f"https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv",
        f"https://www.football-data.co.uk/mmz4371/{season}/{league_code}.csv",
    ]


def validate_history_rows(df: pd.DataFrame, default_source: str = "") -> pd.DataFrame:
    df = normalize_columns(df)
    if df.empty:
        return pd.DataFrame()
    rename_map = {"Date": "date", "Div": "league_code", "HomeTeam": "home_team", "AwayTeam": "away_team", "FTHG": "home_score", "FTAG": "away_score", "FTR": "result"}
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    required = ["date", "home_team", "away_team", "home_score", "away_score"]
    if any(c not in df.columns for c in required):
        return pd.DataFrame()
    rows = []
    for _, row in df.iterrows():
        date = normalize_date(row.get("date"))
        home = clean_text(row.get("home_team"))
        away = clean_text(row.get("away_team"))
        hs_text = clean_text(row.get("home_score"))
        aw_text = clean_text(row.get("away_score"))
        if not date or not home or not away or hs_text == "" or aw_text == "":
            continue
        hs = safe_int(hs_text, 0)
        aw = safe_int(aw_text, 0)
        league_code = clean_text(row.get("league_code"))
        league = clean_text(row.get("league")) or LEAGUE_NAMES.get(league_code, league_code)
        source = clean_text(row.get("source")) or default_source or "history_source"
        match_id = clean_text(row.get("match_id")) or f"hist_{date}_{league}_{home}_{away}".replace(" ", "_")
        rows.append({"match_id": match_id, "date": date, "sport": clean_text(row.get("sport")) or "축구", "league": league, "league_code": league_code, "home_team": home, "away_team": away, "home_score": str(hs), "away_score": str(aw), "status": clean_text(row.get("status")) or "FT", "source": source, "collected_at": clean_text(row.get("collected_at")) or now_kst()})
    return pd.DataFrame(rows)


def fetch_football_data(seasons: List[str], leagues: List[str], timeout: int = 10) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rows, logs = [], []
    for season in seasons:
        for league_code in leagues:
            league_code = clean_text(league_code).upper()
            for url in football_url_candidates(season, league_code):
                log = {"time": now_kst(), "source": "football-data", "season": season, "league_code": league_code, "url": url, "ok": "N", "rows": 0, "message": ""}
                try:
                    res = requests.get(url, timeout=timeout, headers={"User-Agent": "MARU-Sports-Analyzer/2.0"})
                    log["http_status"] = str(res.status_code)
                    if res.status_code != 200:
                        log["message"] = f"HTTP {res.status_code}"
                        logs.append(log)
                        continue
                    raw = pd.read_csv(StringIO(res.content.decode("utf-8", errors="ignore")))
                    raw["source"] = f"football_data_{season}_{league_code}"
                    raw["league"] = LEAGUE_NAMES.get(league_code, league_code)
                    raw["league_code"] = league_code
                    clean_df = validate_history_rows(raw, default_source=f"football_data_{season}_{league_code}")
                    if clean_df.empty:
                        log["message"] = "변환 가능한 완료 경기 없음"
                        logs.append(log)
                        continue
                    rows.append(clean_df)
                    log["ok"] = "Y"
                    log["rows"] = len(clean_df)
                    log["message"] = "저장 가능"
                    logs.append(log)
                    break
                except Exception as exc:
                    log["message"] = str(exc)[:300]
                    logs.append(log)
    out = pd.concat(rows, ignore_index=True).drop_duplicates(subset=["match_id"], keep="last") if rows else pd.DataFrame()
    return out, pd.DataFrame(logs)

# ---------------------- 표준화 ----------------------

def is_finished_status(status: str) -> bool:
    return clean_text(status).upper() in {"FT", "FINISHED", "END", "COMPLETE", "COMPLETED", "종료", "완료"}


def is_upcoming_status(status: str) -> bool:
    s = clean_text(status).upper()
    return not s or s in {"SCHEDULED", "NS", "PRE", "UPCOMING", "예정", "경기전", "대기"}


def standardize_livescore_fixtures() -> pd.DataFrame:
    src = read_csv(SOURCE_FILES["livescore_fixtures"])
    if src.empty:
        return pd.DataFrame()
    rows = []
    for _, row in src.iterrows():
        date = normalize_date(row.get("date"))
        home = clean_text(row.get("home_team"))
        away = clean_text(row.get("away_team"))
        status = clean_text(row.get("status")) or "SCHEDULED"
        if not date or not home or not away:
            continue
        if clean_text(row.get("home_score")) or clean_text(row.get("away_score")) or is_finished_status(status) or not is_upcoming_status(status):
            continue
        match_id = clean_text(row.get("match_id")) or f"up_{date}_{home}_{away}".replace(" ", "_")
        rows.append({"match_id": match_id, "date": date, "kickoff_kst": clean_text(row.get("kickoff_kst")), "sport": clean_text(row.get("sport")) or "축구", "country": clean_text(row.get("country")), "league": clean_text(row.get("league")), "home_team": home, "away_team": away, "status": "SCHEDULED", "source": clean_text(row.get("source")) or "livescore_fixture", "odds_home": clean_text(row.get("odds_home")), "odds_draw": clean_text(row.get("odds_draw")), "odds_away": clean_text(row.get("odds_away")), "collected_at": clean_text(row.get("collected_at")) or now_kst()})
    return pd.DataFrame(rows).drop_duplicates(subset=["match_id"], keep="last") if rows else pd.DataFrame()


def standardize_history() -> pd.DataFrame:
    dfs = []
    for key in ["football_data", "sportmonks", "thesportsdb", "manual"]:
        hist = validate_history_rows(read_csv(SOURCE_FILES[key]), default_source=key)
        if not hist.empty:
            dfs.append(hist)
    return pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["match_id"], keep="last") if dfs else pd.DataFrame()


def standardize_team_form() -> Tuple[pd.DataFrame, pd.DataFrame]:
    srcs = [read_csv(SOURCE_FILES["livescore_team_form"]), read_csv(SOURCE_FILES["manual"])]
    src = pd.concat([x for x in srcs if not x.empty], ignore_index=True) if any(not x.empty for x in srcs) else pd.DataFrame()
    if src.empty or "team" not in src.columns:
        return pd.DataFrame(), pd.DataFrame()
    form_rows, home_away_rows = [], []
    for _, row in src.iterrows():
        team = clean_text(row.get("team"))
        if not team:
            continue
        form_rows.append({"team": team, "league": clean_text(row.get("league")), "recent5": clean_text(row.get("recent5")), "recent10": clean_text(row.get("recent10")), "note": clean_text(row.get("note")), "source": clean_text(row.get("source")) or "team_form", "updated_at": now_kst()})
        home_away_rows.append({"team": team, "league": clean_text(row.get("league")), "home_wins": safe_int(row.get("home_wins"), 0), "home_draws": safe_int(row.get("home_draws"), 0), "home_losses": safe_int(row.get("home_losses"), 0), "away_wins": safe_int(row.get("away_wins"), 0), "away_draws": safe_int(row.get("away_draws"), 0), "away_losses": safe_int(row.get("away_losses"), 0), "source": clean_text(row.get("source")) or "team_form", "updated_at": now_kst()})
    return pd.DataFrame(form_rows), pd.DataFrame(home_away_rows)


def standardize_h2h() -> pd.DataFrame:
    src = read_csv(SOURCE_FILES["livescore_h2h"])
    if src.empty:
        return pd.DataFrame()
    rows = []
    for _, row in src.iterrows():
        home = clean_text(row.get("home_team"))
        away = clean_text(row.get("away_team"))
        if not home or not away:
            continue
        rows.append({"match_id": clean_text(row.get("match_id")), "home_team": home, "away_team": away, "league": clean_text(row.get("league")), "h2h_note": clean_text(row.get("h2h_note")) or clean_text(row.get("note")), "home_h2h_wins": safe_int(row.get("home_h2h_wins"), 0), "draws": safe_int(row.get("draws"), 0), "away_h2h_wins": safe_int(row.get("away_h2h_wins"), 0), "source": clean_text(row.get("source")) or "h2h", "updated_at": now_kst()})
    return pd.DataFrame(rows)


def standardize_current_manual() -> Dict[str, pd.DataFrame]:
    src = read_csv(SOURCE_FILES["manual"])
    out = {k: pd.DataFrame() for k in ["coaches", "transfers", "injuries", "lineups"]}
    if src.empty or "team" not in src.columns:
        return out
    coaches, transfers, injuries, lineups = [], [], [], []
    for _, row in src.iterrows():
        team = clean_text(row.get("team"))
        if not team:
            continue
        if clean_text(row.get("coach")) or clean_text(row.get("coach_start_date")):
            coaches.append({"team": team, "coach": clean_text(row.get("coach")), "coach_start_date": normalize_date(row.get("coach_start_date")), "tactical_note": clean_text(row.get("note")), "source": clean_text(row.get("source")) or "manual", "updated_at": now_kst()})
        if clean_text(row.get("transfers_in")) or clean_text(row.get("transfers_out")) or clean_text(row.get("scout_note")):
            transfers.append({"team": team, "transfers_in": clean_text(row.get("transfers_in")), "transfers_out": clean_text(row.get("transfers_out")), "scout_note": clean_text(row.get("scout_note")), "source": clean_text(row.get("source")) or "manual", "updated_at": now_kst()})
        if clean_text(row.get("injuries")) or clean_text(row.get("missing_players")) or clean_text(row.get("suspended_players")) or clean_text(row.get("key_injuries")):
            injuries.append({"team": team, "injuries": clean_text(row.get("injuries")), "missing_players": clean_text(row.get("missing_players")), "suspended_players": clean_text(row.get("suspended_players")), "key_injuries": clean_text(row.get("key_injuries")), "source": clean_text(row.get("source")) or "manual", "updated_at": now_kst()})
        if clean_text(row.get("expected_lineup")) or clean_text(row.get("formation")):
            lineups.append({"team": team, "formation": clean_text(row.get("formation")), "expected_lineup": clean_text(row.get("expected_lineup")), "key_players": clean_text(row.get("key_players")), "source": clean_text(row.get("source")) or "manual", "updated_at": now_kst()})
    out["coaches"] = pd.DataFrame(coaches)
    out["transfers"] = pd.DataFrame(transfers)
    out["injuries"] = pd.DataFrame(injuries)
    out["lineups"] = pd.DataFrame(lineups)
    return out


def standardize_news_flags() -> pd.DataFrame:
    srcs = [read_csv(SOURCE_FILES["livescore_news"]), read_csv(SOURCE_FILES["manual"])]
    src = pd.concat([x for x in srcs if not x.empty], ignore_index=True) if any(not x.empty for x in srcs) else pd.DataFrame()
    if src.empty:
        return pd.DataFrame()
    rows = []
    for _, row in src.iterrows():
        team = clean_text(row.get("team"))
        news = clean_text(row.get("news")) or clean_text(row.get("note"))
        if not team and not news:
            continue
        low = news.lower()
        flag = []
        for key, label in [("부상", "부상"), ("결장", "결장"), ("감독", "감독"), ("이적", "이적"), ("영입", "영입"), ("라인업", "라인업"), ("징계", "징계")]:
            if key in news or key in low:
                flag.append(label)
        rows.append({"team": team, "match_id": clean_text(row.get("match_id")), "league": clean_text(row.get("league")), "news": news, "flags": ",".join(flag), "source": clean_text(row.get("source")) or "news", "updated_at": now_kst()})
    return pd.DataFrame(rows)


def build_markets(fixtures: pd.DataFrame) -> pd.DataFrame:
    if fixtures.empty:
        return pd.DataFrame()
    actual = read_csv(SOURCE_FILES["proto_markets"])
    rows = []
    for _, fx in fixtures.iterrows():
        match_id = clean_text(fx.get("match_id"))
        actual_for_match = actual[actual["match_id"].astype(str) == match_id] if not actual.empty and "match_id" in actual.columns else pd.DataFrame()
        if not actual_for_match.empty:
            for _, m in actual_for_match.iterrows():
                rows.append({"match_id": match_id, "date": clean_text(fx.get("date")), "kickoff_kst": clean_text(fx.get("kickoff_kst")), "sport": clean_text(fx.get("sport")), "league": clean_text(fx.get("league")), "home_team": clean_text(fx.get("home_team")), "away_team": clean_text(fx.get("away_team")), "market_type": clean_text(m.get("market_type")), "market_label": clean_text(m.get("market_label")) or clean_text(m.get("market_type")), "line": clean_text(m.get("line")), "choices": clean_text(m.get("choices")), "status": "AVAILABLE_ACTUAL", "source": clean_text(m.get("source")) or "proto_market", "updated_at": now_kst()})
        else:
            for m in MARKET_TEMPLATES:
                rows.append({"match_id": match_id, "date": clean_text(fx.get("date")), "kickoff_kst": clean_text(fx.get("kickoff_kst")), "sport": clean_text(fx.get("sport")), "league": clean_text(fx.get("league")), "home_team": clean_text(fx.get("home_team")), "away_team": clean_text(fx.get("away_team")), "market_type": m["market_type"], "market_label": m["market_label"], "line": m["line"], "choices": m["choices"], "status": "AVAILABLE_TEMPLATE", "source": "market_template", "updated_at": now_kst()})
    return pd.DataFrame(rows)


def run_standardize_all() -> Dict[str, int]:
    result = {}
    upcoming = standardize_livescore_fixtures(); write_csv(STANDARD_FILES["upcoming_fixtures"], upcoming); result["standard_upcoming_fixtures"] = len(upcoming)
    history = standardize_history(); write_csv(STANDARD_FILES["history_matches"], history); result["standard_history_matches"] = len(history)
    team_form, team_home_away = standardize_team_form(); write_csv(STANDARD_FILES["team_form"], team_form); write_csv(STANDARD_FILES["team_home_away"], team_home_away); result["standard_team_form"] = len(team_form); result["standard_team_home_away"] = len(team_home_away)
    h2h = standardize_h2h(); write_csv(STANDARD_FILES["h2h"], h2h); result["standard_h2h"] = len(h2h)
    current = standardize_current_manual()
    for key, df in current.items():
        write_csv(STANDARD_FILES[key], df); result[f"standard_{key}"] = len(df)
    news = standardize_news_flags(); write_csv(STANDARD_FILES["news_flags"], news); result["standard_news_flags"] = len(news)
    markets = build_markets(upcoming); write_csv(STANDARD_FILES["markets"], markets); result["standard_markets"] = len(markets)
    log_run("standardize", "source to standard complete", sum(result.values()))
    return result

# ---------------------- 분석 ----------------------

def team_history(history: pd.DataFrame, team: str, league: str = "") -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame()
    df = history.copy()
    if league and "league" in df.columns:
        league_df = df[df["league"].astype(str) == league]
        if not league_df.empty:
            df = league_df
    mask = (df["home_team"].astype(str) == team) | (df["away_team"].astype(str) == team)
    df = df[mask].copy()
    if "date" in df.columns:
        df = df.sort_values("date", ascending=False)
    return df


def calc_team_stats(history: pd.DataFrame, team: str, league: str = "", n: int = 10, home_away: str = "all") -> Dict:
    df = team_history(history, team, league)
    if df.empty:
        return {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "avg_for": 0.0, "avg_against": 0.0, "points": 0, "form": "자료없음"}
    if home_away == "home":
        df = df[df["home_team"].astype(str) == team]
    elif home_away == "away":
        df = df[df["away_team"].astype(str) == team]
    df = df.head(n)
    wins = draws = losses = gf_total = ga_total = 0
    form = []
    for _, row in df.iterrows():
        hs_text = clean_text(row.get("home_score")); aw_text = clean_text(row.get("away_score"))
        if hs_text == "" or aw_text == "":
            continue
        hs = safe_int(hs_text, 0); aw = safe_int(aw_text, 0)
        if clean_text(row.get("home_team")) == team:
            gf, ga = hs, aw
        elif clean_text(row.get("away_team")) == team:
            gf, ga = aw, hs
        else:
            continue
        gf_total += gf; ga_total += ga
        if gf > ga: wins += 1; form.append("W")
        elif gf == ga: draws += 1; form.append("D")
        else: losses += 1; form.append("L")
    matches = wins + draws + losses
    return {"matches": matches, "wins": wins, "draws": draws, "losses": losses, "gf": gf_total, "ga": ga_total, "avg_for": round(gf_total / matches, 2) if matches else 0.0, "avg_against": round(ga_total / matches, 2) if matches else 0.0, "points": wins * 3 + draws, "form": "-".join(form[:5]) if form else "자료없음"}


def latest_team_row(df: pd.DataFrame, team: str) -> Dict:
    if df.empty or "team" not in df.columns:
        return {}
    rows = df[df["team"].astype(str).str.lower() == team.lower()]
    return rows.iloc[-1].to_dict() if not rows.empty else {}


def count_list_text(text: str) -> int:
    raw = clean_text(text)
    if not raw:
        return 0
    for sep in ["/", "|", ";", "\n"]:
        raw = raw.replace(sep, ",")
    return len([p for p in [x.strip() for x in raw.split(",")] if p])


def team_news_count(news: pd.DataFrame, team: str) -> int:
    if news.empty:
        return 0
    if "team" in news.columns:
        return len(news[news["team"].astype(str).str.lower() == team.lower()])
    return 0


def data_quality(home: str, away: str, hist_points: int, coaches: pd.DataFrame, injuries: pd.DataFrame, lineups: pd.DataFrame, transfers: pd.DataFrame, team_form: pd.DataFrame, home_away: pd.DataFrame, h2h: pd.DataFrame, news: pd.DataFrame) -> Tuple[int, List[str]]:
    score = 0; missing = []
    if hist_points >= 16: score += 25
    elif hist_points >= 8: score += 18
    elif hist_points >= 4: score += 10
    else: missing.append("과거 경기자료 부족")
    checks = [("홈/원정 흐름", home_away, 12), ("최근 팀폼", team_form, 10), ("감독 취임일/전술", coaches, 12), ("부상/결장", injuries, 16), ("예상 라인업", lineups, 16), ("영입/이적/스카우트", transfers, 8)]
    for label, df, weight in checks:
        has_home = bool(latest_team_row(df, home)); has_away = bool(latest_team_row(df, away))
        if has_home and has_away: score += weight
        elif has_home or has_away: score += max(4, weight // 2); missing.append(f"{label} 일부 부족")
        else: missing.append(f"{label} 없음")
    if not h2h.empty: score += 5
    else: missing.append("상대전적 없음")
    if team_news_count(news, home) or team_news_count(news, away): score += 6
    else: missing.append("뉴스/공지 없음")
    return min(score, 100), missing


def analyze_market(fixture: Dict, market: Dict, history: pd.DataFrame, coaches: pd.DataFrame, injuries: pd.DataFrame, lineups: pd.DataFrame, transfers: pd.DataFrame, team_form: pd.DataFrame, home_away: pd.DataFrame, h2h: pd.DataFrame, news: pd.DataFrame) -> Dict:
    home = clean_text(fixture.get("home_team")); away = clean_text(fixture.get("away_team")); league = clean_text(fixture.get("league"))
    market_type = clean_text(market.get("market_type")); line = clean_text(market.get("line"))
    home_all = calc_team_stats(history, home, league, 10, "all"); away_all = calc_team_stats(history, away, league, 10, "all")
    home_home = calc_team_stats(history, home, league, 10, "home"); away_away = calc_team_stats(history, away, league, 10, "away")
    hist_points = home_all["matches"] + away_all["matches"]
    quality, missing = data_quality(home, away, hist_points, coaches, injuries, lineups, transfers, team_form, home_away, h2h, news)
    home_inj = latest_team_row(injuries, home); away_inj = latest_team_row(injuries, away)
    home_missing = count_list_text(home_inj.get("injuries", "")) + count_list_text(home_inj.get("missing_players", "")) + count_list_text(home_inj.get("key_injuries", ""))
    away_missing = count_list_text(away_inj.get("injuries", "")) + count_list_text(away_inj.get("missing_players", "")) + count_list_text(away_inj.get("key_injuries", ""))
    base = {"match_id": clean_text(fixture.get("match_id")), "match": f"{home} vs {away}", "league": league, "date_time": f"{clean_text(fixture.get('date'))} {clean_text(fixture.get('kickoff_kst'))}", "market_type": market_type, "line": line, "auto_buy": "NO", "auto_payment": "NO", "created_at": now_kst()}
    if hist_points < 4 or quality < 35:
        return {**base, "pick": "분석불가", "confidence": 0, "risk": "높음", "data_quality": quality, "missing_data": ", ".join(missing), "basis": "자료가 부족하여 추천하지 않습니다."}
    home_power = home_all["points"] + home_home["points"] + home_all["gf"] - home_all["ga"] - home_missing * 2 + 2
    away_power = away_all["points"] + away_away["points"] + away_all["gf"] - away_all["ga"] - away_missing * 2
    diff = home_power - away_power; total_goal_flow = home_all["avg_for"] + away_all["avg_for"]
    pick = "관망"
    if market_type == "승무패": pick = "홈 우세" if diff >= 5 else "원정 우세" if diff <= -5 else "접전/무 주의"
    elif market_type == "핸디캡": pick = "홈 핸디 우세" if diff >= 3 else "원정 핸디 우세" if diff <= -3 else "핸디캡 관망"
    elif market_type == "언더/오버": pick = "오버 쪽 흐름" if total_goal_flow >= 3.0 else "언더 쪽 흐름" if total_goal_flow <= 2.0 else "언오버 관망"
    elif market_type == "더블찬스": pick = "홈/무 안전형" if diff >= 3 else "무/원정 안전형" if diff <= -3 else "더블찬스 관망"
    elif market_type == "전반": pick = "전반 자료부족 주의"; missing.append("전반 전용 데이터 부족")
    elif market_type in {"SUM", "승패/승5패", "한경기조합", "한경기구매", "기타"}: pick = f"{market_type} 자료부족"; missing.append(f"{market_type} 전용 데이터 부족")
    confidence = int(max(0, min(78, 50 + min(20, abs(diff) * 2) + max(0, quality - 60) // 4)))
    if "관망" in pick or "자료부족" in pick or "주의" in pick: confidence = min(confidence, 58)
    risk = "낮음" if confidence >= 70 and quality >= 75 else "중간" if confidence >= 58 and quality >= 55 else "높음"
    basis = [f"홈 최근폼 {home_all['form']} / 홈경기 {home_home['wins']}승 {home_home['draws']}무 {home_home['losses']}패", f"원정 최근폼 {away_all['form']} / 원정경기 {away_away['wins']}승 {away_away['draws']}무 {away_away['losses']}패", f"득점흐름 {total_goal_flow:.2f}"]
    if home_missing: basis.append(f"홈 결장/부상 입력 {home_missing}건")
    if away_missing: basis.append(f"원정 결장/부상 입력 {away_missing}건")
    return {**base, "pick": pick, "confidence": confidence, "risk": risk, "data_quality": quality, "missing_data": ", ".join(missing), "basis": " / ".join(basis)}


def run_analysis() -> Tuple[pd.DataFrame, pd.DataFrame]:
    fixtures = read_csv(STANDARD_FILES["upcoming_fixtures"]); markets = read_csv(STANDARD_FILES["markets"]); history = read_csv(STANDARD_FILES["history_matches"])
    coaches = read_csv(STANDARD_FILES["coaches"]); injuries = read_csv(STANDARD_FILES["injuries"]); lineups = read_csv(STANDARD_FILES["lineups"]); transfers = read_csv(STANDARD_FILES["transfers"])
    team_form = read_csv(STANDARD_FILES["team_form"]); home_away = read_csv(STANDARD_FILES["team_home_away"]); h2h = read_csv(STANDARD_FILES["h2h"]); news = read_csv(STANDARD_FILES["news_flags"])
    if fixtures.empty or markets.empty:
        return pd.DataFrame(), pd.DataFrame()
    rows = []
    for _, fx in fixtures.iterrows():
        fx_markets = markets[markets["match_id"].astype(str) == clean_text(fx.get("match_id"))]
        for _, market in fx_markets.iterrows():
            rows.append(analyze_market(fx.to_dict(), market.to_dict(), history, coaches, injuries, lineups, transfers, team_form, home_away, h2h, news))
    analysis = pd.DataFrame(rows)
    if analysis.empty:
        return pd.DataFrame(), pd.DataFrame()
    write_csv(OUTPUT_FILES["analysis_scores"], analysis)
    mobile_rows = []
    for _, group in analysis.groupby("match_id", dropna=False):
        g = group.copy(); g["confidence_num"] = pd.to_numeric(g.get("confidence", 0), errors="coerce").fillna(0)
        g["quality_num"] = pd.to_numeric(g.get("data_quality", 0), errors="coerce").fillna(0)
        g = g.sort_values(["confidence_num", "quality_num"], ascending=False)
        for _, row in g.head(3).iterrows():
            mobile_rows.append({"created_at": now_kst(), "match_id": clean_text(row.get("match_id")), "match": clean_text(row.get("match")), "league": clean_text(row.get("league")), "date_time": clean_text(row.get("date_time")), "market_type": clean_text(row.get("market_type")), "line": clean_text(row.get("line")), "pick": clean_text(row.get("pick")), "confidence": clean_text(row.get("confidence")), "risk": clean_text(row.get("risk")), "data_quality": clean_text(row.get("data_quality")), "missing_data": clean_text(row.get("missing_data")), "basis": clean_text(row.get("basis")), "auto_buy": "NO", "auto_payment": "NO"})
    mobile = pd.DataFrame(mobile_rows); write_csv(OUTPUT_FILES["mobile_recommendations"], mobile)
    log_run("analysis", "analysis and mobile cards saved", len(mobile))
    return analysis, mobile

# ---------------------- 허브 ----------------------

def get_hub_url() -> str:
    for key in ["GAS_WEBAPP_URL", "GOOGLE_SHEET_HUB_URL", "SHEET_HUB_URL", "gas_webapp_url"]:
        try:
            val = st.secrets.get(key, "")
            if val:
                return str(val)
        except Exception:
            pass
    return ""


def send_hub(payload_type: str, data: Dict) -> Tuple[bool, str]:
    url = get_hub_url()
    if not url:
        return False, "허브 URL 미설정"
    payload = {"app": "MARU SPORTS ANALYZER", "type": payload_type, "created_at": now_kst(), "data": data}
    try:
        res = requests.post(url, json=payload, timeout=20)
        if 200 <= res.status_code < 300:
            return True, f"전송 성공 HTTP {res.status_code}"
        return False, f"전송 실패 HTTP {res.status_code}: {res.text[:200]}"
    except Exception as exc:
        return False, f"전송 오류: {exc}"


def log_hub_result(payload_type: str, ok: bool, message: str, rows: int) -> None:
    row = pd.DataFrame([{"time": now_kst(), "payload_type": payload_type, "ok": "Y" if ok else "N", "message": message, "rows": rows}])
    merge_csv(OUTPUT_FILES["hub_send_logs"], row, ["time", "payload_type", "message"])


def quick_collect_football_data(default_seasons=None, default_leagues=None) -> Tuple[int, int, pd.DataFrame]:
    """버튼 실행용: football-data 과거자료를 자동 탐색해 source_football_data.csv에 저장."""
    seasons = default_seasons or auto_season_codes()[:4]
    leagues = default_leagues or ["E0", "E1", "D1", "SP1", "I1", "F1"]
    df_new, logs = fetch_football_data(seasons, leagues)
    if not logs.empty:
        merge_csv(OUTPUT_FILES["run_logs"], logs, ["time", "source", "season", "league_code", "url"])
    if df_new.empty:
        return 0, file_count(SOURCE_FILES["football_data"]), logs
    added, total = merge_csv(SOURCE_FILES["football_data"], df_new, ["match_id"])
    return added, total, logs


def quick_build_pipeline() -> Dict[str, int]:
    """버튼 실행용: source -> standard 변환 후 분석/모바일 추천까지 저장."""
    result = run_standardize_all()
    analysis, mobile = run_analysis()
    result["analysis_scores"] = len(analysis)
    result["mobile_recommendations"] = len(mobile)
    return result


def render_action_buttons(prefix: str = "quick") -> None:
    """PC/전체실행 공통 실행 버튼 묶음."""
    st.markdown("### 실행 버튼")
    st.caption("앱 시작 시 자동수집은 하지 않습니다. 아래 버튼 또는 GitHub Actions가 실행할 때만 갱신합니다.")
    c0, c1, c2, c3, c4 = st.columns(5)
    with c0:
        if st.button("① 일정표 자동수집", type="primary", key=f"{prefix}_collect_fixtures"):
            with st.spinner("일정표 자동수집 중... TheSportsDB/설정 URL을 검사합니다."):
                added, total, logs = quick_collect_fixtures()
            if total:
                st.success(f"일정표 source 저장 완료: 신규/정리 {added}건 · 전체 {total}건")
            else:
                st.warning("저장된 일정표가 없습니다. 수집 로그 또는 source URL 설정을 확인하세요.")
            with st.expander("일정표 수집 로그", expanded=True):
                st.dataframe(preview_df(logs, 200), width="stretch")
    with c1:
        if st.button("② 과거자료 자동수집", type="primary", key=f"{prefix}_collect_history"):
            with st.spinner("football-data 시즌/리그/URL 자동 탐색 중..."):
                added, total, logs = quick_collect_football_data()
            if total:
                st.success(f"과거자료 source 저장 완료: 신규/정리 {added}건 · 전체 {total}건")
            else:
                st.warning("저장된 과거자료가 없습니다. 탐색 로그를 확인하세요.")
            with st.expander("과거자료 수집 로그", expanded=False):
                st.dataframe(preview_df(logs, 200), width="stretch")
    with c2:
        if st.button("③ source → standard", type="primary", key=f"{prefix}_standardize"):
            result = run_standardize_all()
            st.success("표준화 완료")
            st.dataframe(pd.DataFrame([{"파일": k, "건수": v} for k, v in result.items()]), width="stretch")
    with c3:
        if st.button("④ 분석/모바일 생성", type="primary", key=f"{prefix}_analysis"):
            analysis, mobile = run_analysis()
            if analysis.empty:
                st.warning("분석 결과가 없습니다. 일정표/승부식/현재자료를 먼저 저장하세요. 과거자료만으로 추천하지 않습니다.")
            else:
                st.success(f"분석 완료: analysis {len(analysis)}건 · mobile {len(mobile)}건")
                show_mobile_cards()
    with c4:
        if st.button("⑤ 전체 실행", type="primary", key=f"{prefix}_run_all"):
            with st.spinner("일정표 수집 → 과거자료 수집 → 표준화 → 분석 → 모바일 추천 생성 중..."):
                fx_added, fx_total, fx_logs = quick_collect_fixtures()
                hist_added, hist_total, hist_logs = quick_collect_football_data()
                result = quick_build_pipeline()
            st.success(f"전체 실행 완료 · 일정표 source {fx_total}건 · 과거자료 source {hist_total}건 · 모바일 {result.get('mobile_recommendations', 0)}건")
            st.dataframe(pd.DataFrame([{"파일": k, "건수": v} for k, v in result.items()]), width="stretch")

def tab_run_all() -> None:
    st.subheader("전체실행")
    st.caption("수집 → 표준화 → 승부식 분석 → 모바일 추천 생성까지 한 곳에서 실행합니다.")
    st.info("라이브스코어는 일정표 기준만 사용합니다. 예정 경기가 없으면 모바일 추천카드는 생성하지 않습니다.")
    render_action_buttons("run_all")
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("일정표 source", file_count(SOURCE_FILES["livescore_fixtures"]))
    c2.metric("과거자료 source", file_count(SOURCE_FILES["football_data"]))
    c3.metric("모바일 추천", file_count(OUTPUT_FILES["mobile_recommendations"]))
    with st.expander("필수 진행 순서", expanded=True):
        st.markdown("""
        1. **전체실행 → 일정표 자동수집**으로 오늘/예정 경기 갱신  
        2. **승부식 탭**에서 실제 승부식/기준점 저장 또는 예정경기 기준 승부식 생성  
        3. **자료 입력 탭**에서 감독·부상·라인업·뉴스 저장  
        4. **전체실행**에서 과거자료 수집/표준화/분석 실행  
        5. **모바일 추천**에서 카드 확인  
        """)

# ---------------------- UI ----------------------

def header() -> None:
    st.markdown("""
    <div style="padding:16px 0 10px 0;">
      <div style="font-size:34px;font-weight:900;">⚽ 마루 스포츠 분석가</div>
      <div style="font-size:15px;color:#6b7280;margin-top:6px;">일정표 기준 → 수집원별 저장 → 표준화 → 승부식 분석 → 모바일 추천카드 → 허브/구글시트</div>
      <div style="margin-top:10px;padding:12px 14px;border-radius:14px;background:#f9fafb;border:1px solid #e5e7eb;font-size:14px;line-height:1.6;">
        <b>원칙:</b> 일정표는 자동수집 우선 · 라이브스코어는 일정표 기준만 · 한 사이트 의존 금지 · football-data는 과거자료 보조 · 감독/부상/라인업/뉴스는 source별 보완 · 자동구매/자동결제 없음
      </div>
    </div>
    """, unsafe_allow_html=True)


def metric_board() -> None:
    cols = st.columns(6)
    cols[0].metric("일정표 source", file_count(SOURCE_FILES["livescore_fixtures"]))
    cols[1].metric("과거자료 source", file_count(SOURCE_FILES["football_data"]))
    cols[2].metric("현재자료 manual", file_count(SOURCE_FILES["manual"]))
    cols[3].metric("예정경기 standard", file_count(STANDARD_FILES["upcoming_fixtures"]))
    cols[4].metric("승부식 standard", file_count(STANDARD_FILES["markets"]))
    cols[5].metric("모바일 카드", file_count(OUTPUT_FILES["mobile_recommendations"]))


def show_table(filename: str, title: str, rows: int = 80) -> None:
    df = read_csv(filename)
    st.markdown(f"**{title}** · {len(df)}건")
    if df.empty:
        st.info("저장된 자료가 없습니다.")
        return
    st.dataframe(preview_df(df, rows), width="stretch")
    st.download_button(f"{title} CSV 다운로드", df.to_csv(index=False).encode("utf-8-sig"), filename, "text/csv", key=f"download_{filename}_{title}")


def save_input_to_source(source_key: str, input_df: pd.DataFrame, subset_default: List[str]) -> None:
    if input_df.empty:
        st.warning("저장할 자료가 없습니다.")
        return
    df = add_source_meta(input_df, source_key)
    subset = [c for c in subset_default if c in df.columns] or list(df.columns[:3])
    added, total = merge_csv(SOURCE_FILES[source_key], df, subset)
    st.success(f"{SOURCE_FILES[source_key]} 저장 완료: 신규/정리 {added}건 · 전체 {total}건")


def tab_pc_monitor() -> None:
    st.subheader("PC 모니터링")
    st.caption("대용량 CSV 전체 표시 금지. 건수와 최근 일부만 보여줍니다.")
    render_action_buttons("pc")
    st.divider()
    rows = []
    for group_name, group in [("source", SOURCE_FILES), ("standard", STANDARD_FILES), ("output", OUTPUT_FILES)]:
        for name, filename in group.items():
            rows.append({"구분": group_name, "이름": name, "파일": filename, "건수": file_count(filename)})
    st.dataframe(pd.DataFrame(rows), width="stretch")
    for filename, title in [(OUTPUT_FILES["error_logs"], "최근 오류 로그"), (OUTPUT_FILES["run_logs"], "실행 로그"), (OUTPUT_FILES["hub_send_logs"], "허브 전송 로그")]:
        with st.expander(title, expanded=False):
            show_table(filename, title, 100)
    with st.expander("모바일 추천 미리보기", expanded=True):
        show_table(OUTPUT_FILES["mobile_recommendations"], "mobile_recommendations", 50)


def csv_input_block(label: str, sample: str, key: str) -> pd.DataFrame:
    st.download_button(f"{label} CSV 양식 다운로드", sample.encode("utf-8-sig"), f"{key}_sample.csv", "text/csv", key=f"down_{key}")
    text = st.text_area(f"{label} CSV 붙여넣기", height=130, placeholder=sample, key=f"text_{key}")
    uploaded = st.file_uploader(f"또는 {label} CSV 업로드", type=["csv"], key=f"upload_{key}")
    if uploaded is not None:
        return normalize_columns(pd.read_csv(uploaded, dtype=str).fillna(""))
    if clean_text(text):
        return parse_csv_text(text)
    return pd.DataFrame()


def tab_fixtures() -> None:
    st.subheader("일정표")
    st.caption("라이브스코어/토토 화면은 경기 일정표 기준만 사용합니다. 매일 수동 입력하지 않도록 자동수집을 먼저 둡니다.")
    st.markdown("### 일정표 자동수집")
    st.info("기본은 TheSportsDB 리그별 예정경기 API를 사용합니다. 필요하면 Streamlit Secrets에 THESPORTSDB_LEAGUE_IDS 또는 AUTO_FIXTURE_URLS를 넣어 다른 일정표 URL도 자동으로 붙일 수 있습니다.")
    league_text = st.text_area("자동수집 리그 ID", value=", ".join([f"{k}={v}" for k, v in THESPORTSDB_DEFAULT_LEAGUES.items()]), height=80)
    custom_url_text = st.text_area("추가 일정표 URL 선택 입력", value=secret_value("AUTO_FIXTURE_URLS", ""), height=70, placeholder="CSV/JSON 일정표 URL을 줄바꿈 또는 쉼표로 입력")
    if st.button("일정표 자동수집 실행", type="primary", key="fixture_auto_collect_tab"):
        with st.spinner("일정표 자동수집 중..."):
            added, total, logs = quick_collect_fixtures(parse_league_id_text(league_text), parse_csv_list(custom_url_text))
        if total:
            st.success(f"일정표 source 저장 완료: 신규/정리 {added}건 · 전체 {total}건")
        else:
            st.warning("자동수집된 일정표가 없습니다. 리그 ID/API 키/URL을 확인하세요.")
        with st.expander("일정표 자동수집 로그", expanded=True):
            st.dataframe(preview_df(logs, 200), width="stretch")
    st.divider()
    st.markdown("### 수동 보완 입력")
    st.caption("자동수집에서 빠진 경기만 보완합니다. 매일 전체를 수동으로 넣는 용도가 아닙니다.")
    sample = """date,kickoff_kst,sport,league,home_team,away_team,status,source,match_id,odds_home,odds_draw,odds_away
2026-07-10,20:00,축구,K리그1,울산,전북,SCHEDULED,livescore_copy,ls_001,1.90,3.25,3.80
2026-07-10,22:00,축구,K리그1,서울,포항,SCHEDULED,livescore_copy,ls_002,2.10,3.10,3.20
"""
    df = csv_input_block("일정표", sample, "fixtures")
    if st.button("일정표 source 저장", type="primary"):
        if not df.empty and "match_id" not in df.columns:
            df["match_id"] = [f"ls_{normalize_date(r.get('date'))}_{clean_text(r.get('home_team'))}_{clean_text(r.get('away_team'))}".replace(" ", "_") for _, r in df.iterrows()]
        save_input_to_source("livescore_fixtures", df, ["match_id", "date", "home_team", "away_team"])
    show_table(SOURCE_FILES["livescore_fixtures"], "source_livescore_fixtures", 80)


def tab_market_photo() -> None:
    st.subheader("승부식")
    st.caption("프로토 승부식 설명판 기준: 승무패/핸디캡/언더오버/전반/한경기조합/SUM/더블찬스/기타.")
    st.dataframe(pd.DataFrame(MARKET_TEMPLATES), width="stretch")
    sample = """match_id,market_type,line,choices,source
ls_001,승무패,,홈승|무|원정승,proto_manual
ls_001,언더/오버,2.5,언더|오버,proto_manual
ls_001,핸디캡,+1.0,홈핸디|원정핸디,proto_manual
"""
    df = csv_input_block("실제 승부식/기준점", sample, "proto_markets")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("실제 승부식 source 저장", type="primary"):
            save_input_to_source("proto_markets", df, ["match_id", "market_type", "line"])
    with c2:
        if st.button("예정경기 기준 승부식 생성"):
            fixtures = read_csv(STANDARD_FILES["upcoming_fixtures"])
            if fixtures.empty:
                st.warning("standard_upcoming_fixtures.csv가 없습니다. 먼저 표준화 실행이 필요합니다.")
            else:
                markets = build_markets(fixtures); write_csv(STANDARD_FILES["markets"], markets); st.success(f"승부식 생성 완료: {len(markets)}건")
    show_table(STANDARD_FILES["markets"], "standard_markets", 100)


def tab_sources() -> None:
    st.subheader("수집원 관리")
    st.caption("사이트마다 분류 저장합니다. football-data는 과거 결과 source 하나일 뿐입니다.")
    st.markdown("### football-data 자동 탐색")
    c1, c2 = st.columns([1, 2])
    with c1:
        season_text = st.text_input("시즌 후보", value=", ".join(auto_season_codes()[:4]))
        selected_leagues = st.multiselect("리그 후보", list(LEAGUE_NAMES.keys()), default=["E0", "E1", "D1", "SP1", "I1", "F1"], format_func=lambda x: f"{x} · {LEAGUE_NAMES.get(x, x)}")
    with c2:
        st.info("URL 수동 복사 금지. 시즌 후보 × 리그 후보 × URL 후보를 자동 검사하고 실패 주소는 건너뜁니다.")
        st.write("자동 시즌 예시:", ", ".join(auto_season_codes()))
    if st.button("football-data 자동 탐색 저장", type="primary"):
        seasons = [s.strip() for s in season_text.split(",") if s.strip()] or auto_season_codes()[:4]
        if not selected_leagues:
            st.warning("리그 후보를 하나 이상 선택하세요.")
        else:
            with st.spinner("football-data 시즌/리그/URL 자동 탐색 중..."):
                df_new, logs = fetch_football_data(seasons, selected_leagues)
            if not logs.empty:
                merge_csv(OUTPUT_FILES["run_logs"], logs, ["time", "source", "season", "league_code", "url"])
            if df_new.empty:
                st.warning("저장 가능한 과거자료가 없습니다. 실패 주소는 로그에 기록됩니다.")
            else:
                added, total = merge_csv(SOURCE_FILES["football_data"], df_new, ["match_id"])
                st.success(f"football-data 자동 탐색 저장 {total}건 · 신규/정리 {added}건 · 실패 주소는 자동 건너뜀")
            with st.expander("탐색 로그", expanded=False):
                st.dataframe(preview_df(logs, 200), width="stretch")

    st.markdown("### 기타 source CSV 저장")
    source_options = ["livescore_team_form", "livescore_h2h", "livescore_news", "sportmonks", "thesportsdb", "manual"]
    source_key = st.selectbox("저장할 source", source_options, format_func=lambda x: SOURCE_FILES[x])
    sample = "team,league,recent5,home_wins,home_draws,home_losses,away_wins,away_draws,away_losses,note\n울산,K리그1,W-W-D-L-W,4,1,0,2,1,2,홈 강세\n"
    df = csv_input_block("선택 source", sample, f"source_{source_key}")
    if st.button("선택 source 저장/추가"):
        save_input_to_source(source_key, df, ["match_id", "team", "date"])
    with st.expander("source 파일 미리보기", expanded=False):
        for _, filename in SOURCE_FILES.items():
            show_table(filename, filename, 40)


def tab_manual_input() -> None:
    st.subheader("자료 입력")
    st.caption("감독 취임일, 선수 영입/스카우트, 주전 부상, 결장, 라인업, 뉴스/공지 메모를 manual source로 저장합니다.")
    sample = """team,coach,coach_start_date,transfers_in,transfers_out,scout_note,injuries,missing_players,suspended_players,key_injuries,formation,expected_lineup,key_players,news,note
울산,홍길동,2026-03-01,공격수A,,신입 공격수 속도 우수,,수비수B,,주전 수비수 결장,4-2-3-1,선발 미확정,공격수A;미드필더C,라인업 발표 대기,라인업 확인 필요
전북,김감독,2025-12-10,,미드필더D,중원 약화 가능,공격수E,,,공격 핵심 부상,4-3-3,선발 미확정,수비수F,원정 수비 불안 뉴스,원정 경기력 확인
"""
    df = csv_input_block("현재상태 manual", sample, "manual_current")
    if st.button("manual source 저장", type="primary"):
        save_input_to_source("manual", df, ["team"])
    show_table(SOURCE_FILES["manual"], "source_manual", 80)


def tab_standard_analysis() -> None:
    st.subheader("표준화/분석")
    st.caption("source 자료를 standard로 변환한 뒤, standard 자료만 읽어서 분석합니다.")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("source → standard 변환", type="primary"):
            result = run_standardize_all(); st.success("표준화 완료"); st.dataframe(pd.DataFrame([{"파일": k, "건수": v} for k, v in result.items()]), width="stretch")
    with c2:
        if st.button("승부식 분석 실행", type="primary"):
            analysis, mobile = run_analysis()
            if analysis.empty: st.warning("분석 결과가 없습니다. 예정 경기 또는 승부식/자료가 부족합니다.")
            else: st.success(f"분석 저장 완료: analysis {len(analysis)}건 · mobile {len(mobile)}건")
    with c3:
        st.info("예정 경기 없으면 추천카드가 만들어지지 않습니다. 과거 경기만으로 현재 추천을 만들지 않습니다.")
    tabs = st.tabs(["예정경기", "과거자료", "팀흐름", "현재자료", "뉴스/H2H", "analysis", "mobile"])
    with tabs[0]: show_table(STANDARD_FILES["upcoming_fixtures"], "standard_upcoming_fixtures", 80)
    with tabs[1]: show_table(STANDARD_FILES["history_matches"], "standard_history_matches", 80)
    with tabs[2]:
        show_table(STANDARD_FILES["team_form"], "standard_team_form", 50); show_table(STANDARD_FILES["team_home_away"], "standard_team_home_away", 50)
    with tabs[3]:
        for key in ["coaches", "transfers", "injuries", "lineups"]: show_table(STANDARD_FILES[key], STANDARD_FILES[key], 50)
    with tabs[4]:
        show_table(STANDARD_FILES["h2h"], "standard_h2h", 50); show_table(STANDARD_FILES["news_flags"], "standard_news_flags", 50)
    with tabs[5]: show_table(OUTPUT_FILES["analysis_scores"], "analysis_scores", 100)
    with tabs[6]: show_mobile_cards()


def card_html(row: Dict) -> str:
    return f"""
    <div style="border:1px solid #e5e7eb;border-radius:16px;padding:16px;margin:10px 0;background:white;box-shadow:0 1px 2px rgba(0,0,0,0.04);">
      <div style="font-size:13px;color:#6b7280;">{clean_text(row.get('league'))} · {clean_text(row.get('date_time'))}</div>
      <div style="font-size:22px;font-weight:900;margin:6px 0;">{clean_text(row.get('match'))}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;">
        <span style="background:#eef2ff;border-radius:999px;padding:6px 10px;">승부식 <b>{clean_text(row.get('market_type'))}</b></span>
        <span style="background:#f3f4f6;border-radius:999px;padding:6px 10px;">기준 <b>{clean_text(row.get('line')) or '-'}</b></span>
        <span style="background:#ecfdf5;border-radius:999px;padding:6px 10px;">추천 <b>{clean_text(row.get('pick'))}</b></span>
        <span style="background:#fff7ed;border-radius:999px;padding:6px 10px;">신뢰도 <b>{clean_text(row.get('confidence'))}%</b></span>
        <span style="background:#fef2f2;border-radius:999px;padding:6px 10px;">위험도 <b>{clean_text(row.get('risk'))}</b></span>
        <span style="background:#f0f9ff;border-radius:999px;padding:6px 10px;">자료충분도 <b>{clean_text(row.get('data_quality'))}%</b></span>
      </div>
      <div style="font-size:14px;line-height:1.55;color:#374151;"><b>근거:</b> {clean_text(row.get('basis'))}</div>
      <div style="font-size:14px;line-height:1.55;color:#b45309;margin-top:4px;"><b>부족자료:</b> {clean_text(row.get('missing_data')) or '없음'}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:8px;">자동구매 없음 · 자동결제 없음 · 사용자가 직접 판단</div>
    </div>
    """


def show_mobile_cards() -> None:
    df = read_csv(OUTPUT_FILES["mobile_recommendations"])
    if df.empty:
        st.info("모바일 추천카드가 없습니다. 예정 경기와 분석자료를 먼저 저장하세요.")
        return
    for _, row in preview_df(df, 30).iterrows():
        st.markdown(card_html(row.to_dict()), unsafe_allow_html=True)
    with st.expander("mobile_recommendations.csv 원자료", expanded=False):
        st.dataframe(preview_df(df, 100), width="stretch")


def tab_mobile() -> None:
    st.subheader("모바일 추천")
    st.caption("최종 확인용입니다. 자동구매/자동결제는 없습니다.")
    show_mobile_cards()


def tab_hub() -> None:
    st.subheader("허브/구글시트 전송")
    st.caption("Streamlit secrets에 GAS_WEBAPP_URL 또는 GOOGLE_SHEET_HUB_URL이 있으면 전송합니다.")
    st.metric("허브 URL", "ON" if get_hub_url() else "OFF")
    send_target = st.selectbox("전송 대상", ["mobile_recommendations", "analysis_scores", "all_standard_counts", "all_source_counts"])
    if st.button("허브/구글시트 전송", type="primary"):
        if send_target == "mobile_recommendations":
            df = read_csv(OUTPUT_FILES["mobile_recommendations"]); data = {"rows": df.to_dict(orient="records")}; rows = len(df)
        elif send_target == "analysis_scores":
            df = read_csv(OUTPUT_FILES["analysis_scores"]); data = {"rows": df.to_dict(orient="records")}; rows = len(df)
        elif send_target == "all_standard_counts":
            rows_list = [{"name": name, "filename": filename, "rows": file_count(filename)} for name, filename in STANDARD_FILES.items()]; data = {"counts": rows_list}; rows = len(rows_list)
        else:
            rows_list = [{"name": name, "filename": filename, "rows": file_count(filename)} for name, filename in SOURCE_FILES.items()]; data = {"counts": rows_list}; rows = len(rows_list)
        ok, msg = send_hub(send_target, data); log_hub_result(send_target, ok, msg, rows)
        if ok: st.success(msg)
        else: st.warning(msg)
    show_table(OUTPUT_FILES["hub_send_logs"], "hub_send_logs", 100)



# ---------------------- 백엔드 진단 / 가상 테스트 ----------------------

def source_required_fields(filename: str) -> List[str]:
    mapping = {
        SOURCE_FILES["livescore_fixtures"]: ["date", "home_team", "away_team"],
        SOURCE_FILES["football_data"]: ["date", "home_team", "away_team", "home_score", "away_score"],
        SOURCE_FILES["proto_markets"]: ["match_id", "market_type"],
        SOURCE_FILES["manual"]: ["team"],
    }
    return mapping.get(filename, [])


def diagnose_file(filename: str, group_name: str) -> Dict:
    df = read_csv(filename)
    required = source_required_fields(filename)
    missing_cols = [c for c in required if c not in df.columns]
    empty_shell = "Y" if (not df.empty and required and missing_cols) else "N"
    if df.empty:
        status = "EMPTY"
        reason = "저장된 자료 없음"
    elif missing_cols:
        status = "SHELL_OR_BAD_COLUMNS"
        reason = "필수 컬럼 부족: " + ", ".join(missing_cols)
    else:
        status = "OK"
        reason = "읽기/필수 컬럼 확인"
    return {
        "time": now_kst(), "group": group_name, "filename": filename, "rows": len(df),
        "columns": ", ".join(list(df.columns)[:30]), "required": ", ".join(required),
        "missing_columns": ", ".join(missing_cols), "empty_shell": empty_shell,
        "status": status, "reason": reason,
    }


def diagnose_current_data() -> pd.DataFrame:
    rows = []
    for group_name, group in [("source", SOURCE_FILES), ("standard", STANDARD_FILES), ("output", OUTPUT_FILES)]:
        for _, filename in group.items():
            rows.append(diagnose_file(filename, group_name))
    report = pd.DataFrame(rows)
    write_csv("backend_diagnosis_report.csv", report)
    return report


def mock_source_data() -> Dict[str, pd.DataFrame]:
    today = datetime.now(KST).strftime("%Y-%m-%d")
    fixtures = pd.DataFrame([
        {"match_id":"mock_001","date":today,"kickoff_kst":"20:00","sport":"축구","league":"가상리그","home_team":"울산","away_team":"전북","status":"SCHEDULED","source":"virtual_test"},
        {"match_id":"mock_002","date":today,"kickoff_kst":"22:00","sport":"축구","league":"가상리그","home_team":"서울","away_team":"포항","status":"SCHEDULED","source":"virtual_test"},
    ])
    history_rows = []
    teams = [("울산","전북"),("서울","포항"),("울산","서울"),("전북","포항")]
    for i in range(24):
        home, away = teams[i % len(teams)]
        history_rows.append({"match_id":f"hist_mock_{i}","date":f"2026-06-{(i%28)+1:02d}","league":"가상리그","home_team":home,"away_team":away,"home_score":str((i*2)%4),"away_score":str((i+1)%3),"status":"FT","source":"virtual_history"})
    history = pd.DataFrame(history_rows)
    markets = pd.DataFrame([
        {"match_id":"mock_001","market_type":"승무패","line":"","choices":"홈승|무|원정승","source":"virtual_proto"},
        {"match_id":"mock_001","market_type":"언더/오버","line":"2.5","choices":"언더|오버","source":"virtual_proto"},
        {"match_id":"mock_001","market_type":"핸디캡","line":"+1.0","choices":"홈핸디|원정핸디","source":"virtual_proto"},
        {"match_id":"mock_002","market_type":"승무패","line":"","choices":"홈승|무|원정승","source":"virtual_proto"},
        {"match_id":"mock_002","market_type":"더블찬스","line":"","choices":"홈/무|무/원정","source":"virtual_proto"},
    ])
    manual = pd.DataFrame([
        {"team":"울산","league":"가상리그","coach":"가상감독A","coach_start_date":"2026-03-01","transfers_in":"공격수A","transfers_out":"","scout_note":"신규 공격수 속도 우수","injuries":"","missing_players":"","suspended_players":"","key_injuries":"","formation":"4-2-3-1","expected_lineup":"주전 대부분 가능","key_players":"공격수A;미드필더B","recent5":"W-W-D-W-L","home_wins":"4","home_draws":"1","home_losses":"0","away_wins":"2","away_draws":"1","away_losses":"2","news":"주전 공격수 선발 가능","note":"가상 테스트"},
        {"team":"전북","league":"가상리그","coach":"가상감독B","coach_start_date":"2025-11-10","transfers_in":"","transfers_out":"미드필더D","scout_note":"중원 약화","injuries":"수비수C","missing_players":"수비수C","suspended_players":"","key_injuries":"주전 수비 결장","formation":"4-3-3","expected_lineup":"수비진 변동","key_players":"공격수E","recent5":"L-D-W-L-L","home_wins":"2","home_draws":"1","home_losses":"2","away_wins":"1","away_draws":"1","away_losses":"3","news":"주전 수비수 부상 결장","note":"가상 테스트"},
        {"team":"서울","league":"가상리그","coach":"가상감독C","coach_start_date":"2026-01-20","transfers_in":"윙어K","transfers_out":"","scout_note":"측면 강화","injuries":"","missing_players":"","suspended_players":"","key_injuries":"","formation":"4-4-2","expected_lineup":"정상","key_players":"윙어K","recent5":"W-D-W-D-W","home_wins":"3","home_draws":"2","home_losses":"0","away_wins":"2","away_draws":"2","away_losses":"1","news":"라인업 정상","note":"가상 테스트"},
        {"team":"포항","league":"가상리그","coach":"가상감독D","coach_start_date":"2024-09-01","transfers_in":"","transfers_out":"공격수Z","scout_note":"득점력 저하 가능","injuries":"공격수M","missing_players":"공격수M","suspended_players":"","key_injuries":"주전 공격 결장","formation":"3-5-2","expected_lineup":"공격수 대체","key_players":"수비수N","recent5":"L-L-D-W-L","home_wins":"1","home_draws":"2","home_losses":"2","away_wins":"1","away_draws":"0","away_losses":"4","news":"공격수 부상","note":"가상 테스트"},
    ])
    h2h = pd.DataFrame([
        {"match_id":"mock_001","home_team":"울산","away_team":"전북","league":"가상리그","h2h_note":"최근 맞대결 홈 우세","home_h2h_wins":"3","draws":"1","away_h2h_wins":"1","source":"virtual_h2h"},
        {"match_id":"mock_002","home_team":"서울","away_team":"포항","league":"가상리그","h2h_note":"서울 근소 우세","home_h2h_wins":"2","draws":"2","away_h2h_wins":"1","source":"virtual_h2h"},
    ])
    news = manual[["team", "league", "news", "note"]].copy()
    return {
        SOURCE_FILES["livescore_fixtures"]: fixtures,
        SOURCE_FILES["football_data"]: history,
        SOURCE_FILES["proto_markets"]: markets,
        SOURCE_FILES["manual"]: manual,
        SOURCE_FILES["livescore_h2h"]: h2h,
        SOURCE_FILES["livescore_news"]: news,
        SOURCE_FILES["livescore_team_form"]: manual,
    }


def run_virtual_backend_test() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """허브/구글시트가 아직 없어도 전체 흐름을 가상 데이터로 검증한다. 실제 data 폴더는 건드리지 않는다."""
    global DATA_DIR
    original_dir = DATA_DIR
    checks = []
    with tempfile.TemporaryDirectory() as tmp:
        DATA_DIR = tmp
        ensure_data_dir()
        for filename, df in mock_source_data().items():
            write_csv(filename, df)
            checks.append({"step":"mock_source_write","target":filename,"ok":"Y","rows":len(df),"message":"가상 source 저장"})
        standard_counts = run_standardize_all()
        for name, rows in standard_counts.items():
            checks.append({"step":"standardize","target":name,"ok":"Y" if rows else "N","rows":rows,"message":"standard 변환"})
        analysis, mobile = run_analysis()
        checks.append({"step":"analysis","target":"analysis_scores.csv","ok":"Y" if len(analysis) else "N","rows":len(analysis),"message":"승부식별 분석 생성"})
        checks.append({"step":"mobile","target":"mobile_recommendations.csv","ok":"Y" if len(mobile) else "N","rows":len(mobile),"message":"모바일 추천카드 생성"})
        payload = {"app":"MARU SPORTS ANALYZER","type":"dry_run_mobile_recommendations","created_at":now_kst(),"data":{"rows":mobile.to_dict(orient="records")}}
        payload_ok = bool(payload["data"]["rows"] and {"match_id","market_type","pick","confidence","risk","data_quality"}.issubset(set(mobile.columns)))
        checks.append({"step":"hub_dry_run","target":"payload_shape","ok":"Y" if payload_ok else "N","rows":len(payload["data"]["rows"]),"message":"허브 payload 구조 검사"})
        diag = diagnose_current_data()
        DATA_DIR = original_dir
    return pd.DataFrame(checks), preview_df(analysis, 20), preview_df(mobile, 20)


def missing_data_summary() -> pd.DataFrame:
    fixtures = read_csv(STANDARD_FILES["upcoming_fixtures"])
    if fixtures.empty:
        return pd.DataFrame([{"item":"예정경기","status":"MISSING","message":"standard_upcoming_fixtures.csv 0건: 일정표 자동수집/표준화 필요"}])
    checks = [
        ("승부식", STANDARD_FILES["markets"], "standard_markets.csv"),
        ("과거자료", STANDARD_FILES["history_matches"], "standard_history_matches.csv"),
        ("감독 취임일", STANDARD_FILES["coaches"], "standard_coaches.csv"),
        ("주전 부상/결장", STANDARD_FILES["injuries"], "standard_injuries.csv"),
        ("예상 라인업", STANDARD_FILES["lineups"], "standard_lineups.csv"),
        ("영입/이적/스카우트", STANDARD_FILES["transfers"], "standard_transfers.csv"),
        ("뉴스/공지", STANDARD_FILES["news_flags"], "standard_news_flags.csv"),
        ("상대전적", STANDARD_FILES["h2h"], "standard_h2h.csv"),
        ("홈/원정 흐름", STANDARD_FILES["team_home_away"], "standard_team_home_away.csv"),
    ]
    rows = []
    for label, filename, full in checks:
        cnt = file_count(filename)
        rows.append({"item": label, "status": "OK" if cnt else "MISSING", "rows": cnt, "message": full + (" 확인됨" if cnt else " 없음")})
    return pd.DataFrame(rows)


def tab_backend_diagnosis() -> None:
    st.subheader("백엔드 진단 / 가상 테스트")
    st.caption("구글시트/허브 설정이 없어도 가상 데이터로 수집→표준화→분석→모바일추천→허브 payload까지 검사합니다.")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("현재 저장자료 진단", type="primary"):
            report = diagnose_current_data()
            st.success("현재 자료 진단 완료")
            st.dataframe(report, width="stretch")
    with c2:
        if st.button("가상 백엔드 전체 테스트", type="primary"):
            checks, analysis, mobile = run_virtual_backend_test()
            if (checks["ok"] == "N").any():
                st.warning("가상 테스트에서 실패 단계가 있습니다.")
            else:
                st.success("가상 테스트 통과: source→standard→analysis→mobile→hub dry-run")
            st.dataframe(checks, width="stretch")
            with st.expander("가상 analysis_scores", expanded=False):
                st.dataframe(analysis, width="stretch")
            with st.expander("가상 mobile_recommendations", expanded=True):
                st.dataframe(mobile, width="stretch")
    with c3:
        if st.button("부족자료 목록 확인", type="primary"):
            st.dataframe(missing_data_summary(), width="stretch")
    st.divider()
    st.markdown("### 허브 상태")
    st.metric("허브 URL", "ON" if get_hub_url() else "OFF")
    st.info("허브 URL이 OFF여도 dry-run payload 검사는 가능합니다. 실제 구글시트 쓰기만 OFF입니다.")
    if st.button("허브 실제 전송 테스트"):
        payload = {"diagnosis": diagnose_current_data().to_dict(orient="records"), "missing": missing_data_summary().to_dict(orient="records")}
        ok, msg = send_hub("backend_diagnosis", payload)
        log_hub_result("backend_diagnosis", ok, msg, len(payload["diagnosis"]))
        if ok:
            st.success(msg)
        else:
            st.warning(msg)
    with st.expander("최근 진단 리포트", expanded=False):
        show_table("backend_diagnosis_report.csv", "backend_diagnosis_report", 100)


def main() -> None:
    st.set_page_config(page_title="마루 스포츠 분석가", page_icon="⚽", layout="wide", initial_sidebar_state="collapsed")
    ensure_data_dir(); header(); metric_board(); st.divider()
    tabs = st.tabs(["전체실행", "PC 모니터링", "일정표", "승부식", "수집원 관리", "자료 입력", "표준화/분석", "모바일 추천", "허브 전송", "백엔드 진단"])
    with tabs[0]: tab_run_all()
    with tabs[1]: tab_pc_monitor()
    with tabs[2]: tab_fixtures()
    with tabs[3]: tab_market_photo()
    with tabs[4]: tab_sources()
    with tabs[5]: tab_manual_input()
    with tabs[6]: tab_standard_analysis()
    with tabs[7]: tab_mobile()
    with tabs[8]: tab_hub()
    with tabs[9]: tab_backend_diagnosis()
    st.divider(); st.caption(f"현재 시간: {now_kst()} · 라이브스코어는 일정표 기준만 · 자동구매/자동결제 없음")


if __name__ == "__main__":
    main()
