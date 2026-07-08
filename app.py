import os
import json
import zipfile
from pathlib import Path
from io import StringIO, BytesIO
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Any

import pandas as pd
import requests
import streamlit as st

KST = timezone(timedelta(hours=9))
APP_NAME = "MARU SPORTS PROTO FIXTURE HUB"
APP_VERSION = "v12-full-hub-visible"
DATA_DIR = "data"
LOG_DIR = "logs"
PAYLOAD_DIR = "payloads"

SOURCE_FILES = {
    "source_livescore_fixtures": f"{DATA_DIR}/source_livescore_fixtures.csv",
    "source_livescore_team_form": f"{DATA_DIR}/source_livescore_team_form.csv",
    "source_livescore_h2h": f"{DATA_DIR}/source_livescore_h2h.csv",
    "source_livescore_news": f"{DATA_DIR}/source_livescore_news.csv",
    "source_football_data": f"{DATA_DIR}/source_football_data.csv",
    "source_sportmonks": f"{DATA_DIR}/source_sportmonks.csv",
    "source_thesportsdb": f"{DATA_DIR}/source_thesportsdb.csv",
    "source_proto_markets": f"{DATA_DIR}/source_proto_markets.csv",
    "source_manual": f"{DATA_DIR}/source_manual.csv",
}

STANDARD_FILES = {
    "standard_upcoming_fixtures": f"{DATA_DIR}/standard_upcoming_fixtures.csv",
    "standard_history_matches": f"{DATA_DIR}/standard_history_matches.csv",
    "standard_team_form": f"{DATA_DIR}/standard_team_form.csv",
    "standard_team_home_away": f"{DATA_DIR}/standard_team_home_away.csv",
    "standard_h2h": f"{DATA_DIR}/standard_h2h.csv",
    "standard_coaches": f"{DATA_DIR}/standard_coaches.csv",
    "standard_transfers": f"{DATA_DIR}/standard_transfers.csv",
    "standard_injuries": f"{DATA_DIR}/standard_injuries.csv",
    "standard_lineups": f"{DATA_DIR}/standard_lineups.csv",
    "standard_news_flags": f"{DATA_DIR}/standard_news_flags.csv",
    "standard_markets": f"{DATA_DIR}/standard_markets.csv",
}

OUTPUT_FILES = {
    "analysis_scores": f"{DATA_DIR}/analysis_scores.csv",
    "mobile_recommendations": f"{DATA_DIR}/mobile_recommendations.csv",
    "hub_send_logs": f"{DATA_DIR}/hub_send_logs.csv",
    "run_logs": f"{LOG_DIR}/run_logs.csv",
    "error_logs": f"{LOG_DIR}/error_logs.csv",
    "backend_diagnosis": f"{DATA_DIR}/backend_diagnosis_report.csv",
    "missing_data_report": f"{DATA_DIR}/missing_data_report.csv",
    "coach_status": f"{DATA_DIR}/coach_status.csv",
    "injury_status": f"{DATA_DIR}/injury_status.csv",
    "lineup_status": f"{DATA_DIR}/lineup_status.csv",
    "transfer_status": f"{DATA_DIR}/transfer_status.csv",
    "news_status": f"{DATA_DIR}/news_status.csv",
    "proto_market_status": f"{DATA_DIR}/proto_market_status.csv",
    "hub_payload_latest": f"{PAYLOAD_DIR}/hub_payload_latest.json",
    "hub_payload_queue": f"{PAYLOAD_DIR}/hub_payload_queue.jsonl",
}

LEAGUE_CODES = {
    "E0": "English Premier League",
    "E1": "English Championship",
    "D1": "German Bundesliga",
    "SP1": "Spanish La Liga",
    "I1": "Italian Serie A",
    "F1": "French Ligue 1",
}

THESPORTSDB_LEAGUES = {
    "English Premier League": "4328",
    "English Championship": "4329",
    "German Bundesliga": "4331",
    "Spanish La Liga": "4335",
    "Italian Serie A": "4332",
    "French Ligue 1": "4334",
}

MARKET_TEMPLATES = [
    {"market_type": "승무패", "line_value": "", "option_a": "홈승", "option_b": "무승부", "option_c": "원정승"},
    {"market_type": "핸디캡", "line_value": "+1.0", "option_a": "홈핸디", "option_b": "원정핸디", "option_c": ""},
    {"market_type": "언더오버", "line_value": "2.5", "option_a": "언더", "option_b": "오버", "option_c": ""},
    {"market_type": "전반", "line_value": "", "option_a": "전반홈", "option_b": "전반무", "option_c": "전반원정"},
    {"market_type": "더블찬스", "line_value": "", "option_a": "홈/무", "option_b": "홈/원정", "option_c": "무/원정"},
    {"market_type": "SUM", "line_value": "", "option_a": "합홀", "option_b": "합짝", "option_c": ""},
    {"market_type": "승패/승5패", "line_value": "", "option_a": "승", "option_b": "패", "option_c": "5패"},
    {"market_type": "한경기조합", "line_value": "", "option_a": "조합A", "option_b": "조합B", "option_c": ""},
    {"market_type": "한경기구매", "line_value": "", "option_a": "단일", "option_b": "", "option_c": ""},
    {"market_type": "기타", "line_value": "", "option_a": "특수", "option_b": "", "option_c": ""},
]


EMPTY_SCHEMAS = {
    "standard_coaches": ["team", "coach", "coach_start_date", "tactics", "note", "status"],
    "standard_transfers": ["team", "transfers", "scouting_note", "note", "status"],
    "standard_injuries": ["team", "injuries", "missing_players", "note", "status"],
    "standard_lineups": ["team", "lineup", "formation", "note", "status"],
    "standard_news_flags": ["team", "news", "notice", "note", "status"],
    "standard_markets": ["match_id", "league", "home_team", "away_team", "market_type", "line_value", "option_a", "option_b", "option_c", "source", "status"],
    "missing_data_report": ["created_at", "match_id", "match", "league", "date", "kickoff_kst", "coach_status", "tactics_status", "injury_status", "suspension_status", "lineup_status", "transfer_scout_status", "news_notice_status", "proto_market_status", "overall_status", "missing_items"],
    "coach_status": ["created_at", "match_id", "match", "home_team", "away_team", "home_coach_status", "away_coach_status", "home_tactics_status", "away_tactics_status"],
    "injury_status": ["created_at", "match_id", "match", "home_team", "away_team", "home_injury_status", "away_injury_status", "home_missing_status", "away_missing_status"],
    "lineup_status": ["created_at", "match_id", "match", "home_team", "away_team", "home_lineup_status", "away_lineup_status"],
    "transfer_status": ["created_at", "match_id", "match", "home_team", "away_team", "home_transfer_status", "away_transfer_status", "home_scout_status", "away_scout_status"],
    "news_status": ["created_at", "match_id", "match", "home_team", "away_team", "home_news_status", "away_news_status"],
    "proto_market_status": ["created_at", "match_id", "match", "market_rows", "real_proto_rows", "template_rows", "status"],
}


COLUMN_MAP = {
    "Date": "date", "날짜": "date", "경기일": "date",
    "Time": "kickoff_kst", "시간": "kickoff_kst", "킥오프": "kickoff_kst",
    "Div": "league_code", "리그코드": "league_code", "League": "league", "리그": "league",
    "HomeTeam": "home_team", "홈팀": "home_team", "홈": "home_team",
    "AwayTeam": "away_team", "원정팀": "away_team", "원정": "away_team",
    "FTHG": "home_score", "홈점수": "home_score",
    "FTAG": "away_score", "원정점수": "away_score",
    "FTR": "result", "status": "status", "상태": "status",
    "team": "team", "팀": "team", "팀명": "team",
    "coach": "coach", "감독": "coach", "coach_start_date": "coach_start_date", "취임일": "coach_start_date",
    "injuries": "injuries", "부상": "injuries", "missing_players": "missing_players", "결장": "missing_players",
    "lineup": "lineup", "라인업": "lineup", "transfers": "transfers", "영입": "transfers", "스카우트": "scouting_note",
    "news": "news", "뉴스": "news", "note": "note", "메모": "note",
    "market_type": "market_type", "승부식": "market_type", "line_value": "line_value", "기준점": "line_value",
}


def ensure_dirs():
    for d in [DATA_DIR, LOG_DIR, PAYLOAD_DIR]:
        os.makedirs(d, exist_ok=True)


def now_text():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null", "nat"}:
        return ""
    return text


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [clean(c) for c in out.columns]
    out = out.rename(columns={c: COLUMN_MAP.get(c, c) for c in out.columns})
    return out


def safe_int(value, default=None):
    try:
        text = clean(value)
        if text == "":
            return default
        return int(float(text))
    except Exception:
        return default


def normalize_date(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    # football-data often DD/MM/YYYY
    if "/" in text:
        parts = text.split("/")
        if len(parts) == 3:
            a, b, y = parts
            if len(y) == 2:
                y = "20" + y
            return f"{y.zfill(4)}-{b.zfill(2)}-{a.zfill(2)}"
    try:
        return pd.to_datetime(text, errors="coerce").strftime("%Y-%m-%d")
    except Exception:
        return text[:10]


def read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return normalize_columns(pd.read_csv(path, dtype=str).fillna(""))
    except Exception as exc:
        log_error("read_csv", path, str(exc))
        return pd.DataFrame()


def write_csv(path: str, df: pd.DataFrame):
    ensure_dirs()
    df = df.copy() if df is not None else pd.DataFrame()
    # 빈 파일도 기본 컬럼을 유지해서 Google Sheet/진단에서 "안 받은 자료"가 눈에 보이게 한다.
    if df.empty:
        base = os.path.basename(path).replace(".csv", "")
        if base in EMPTY_SCHEMAS:
            df = pd.DataFrame(columns=EMPTY_SCHEMAS[base])
    df.to_csv(path, index=False, encoding="utf-8-sig")


def append_csv(path: str, df_new: pd.DataFrame, subset: List[str] = None) -> Tuple[int, int]:
    ensure_dirs()
    if df_new is None or df_new.empty:
        return 0, len(read_csv(path))
    current = read_csv(path)
    before = len(current)
    total = pd.concat([current, df_new], ignore_index=True) if not current.empty else df_new.copy()
    if subset:
        cols = [c for c in subset if c in total.columns]
        if cols:
            total = total.drop_duplicates(subset=cols, keep="last")
    total = total.drop_duplicates(keep="last")
    write_csv(path, total)
    return max(len(total) - before, 0), len(total)


def log_run(step: str, status: str, message: str, extra: Dict[str, Any] = None):
    row = {"time": now_text(), "step": step, "status": status, "message": message}
    if extra:
        row.update({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in extra.items()})
    append_csv(OUTPUT_FILES["run_logs"], pd.DataFrame([row]), subset=None)


def log_error(step: str, target: str, message: str):
    row = {"time": now_text(), "step": step, "target": target, "message": message}
    append_csv(OUTPUT_FILES["error_logs"], pd.DataFrame([row]), subset=None)


def file_counts() -> Dict[str, int]:
    counts = {}
    for group in [SOURCE_FILES, STANDARD_FILES, OUTPUT_FILES]:
        for name, path in group.items():
            if path.endswith(".csv"):
                counts[name] = len(read_csv(path))
            elif os.path.exists(path):
                counts[name] = 1
            else:
                counts[name] = 0
    return counts


def get_hub_url() -> str:
    keys = ["GAS_WEBAPP_URL", "GOOGLE_SHEET_HUB_URL", "gas_webapp_url", "sheet_hub_url"]
    for key in keys:
        try:
            v = st.secrets.get(key, "")
            if v:
                return str(v)
        except Exception:
            pass
    return ""


def get_google_sheet_url() -> str:
    keys = ["GOOGLE_SHEET_URL", "google_sheet_url", "MARU_GOOGLE_SHEET_URL", "SHEET_URL"]
    for key in keys:
        try:
            v = st.secrets.get(key, "")
            if v:
                return str(v)
        except Exception:
            pass
    return ""


def masked_url(value: str) -> str:
    value = clean(value)
    if not value:
        return ""
    if len(value) <= 18:
        return value[:4] + "…"
    return value[:12] + "…" + value[-10:]


def hub_secrets_status() -> Dict[str, Any]:
    hub_keys = ["GAS_WEBAPP_URL", "GOOGLE_SHEET_HUB_URL", "gas_webapp_url", "sheet_hub_url"]
    sheet_keys = ["GOOGLE_SHEET_URL", "google_sheet_url", "MARU_GOOGLE_SHEET_URL", "SHEET_URL"]
    rows = []
    found = ""
    sheet_found = ""
    for key in hub_keys + sheet_keys:
        try:
            value = st.secrets.get(key, "")
        except Exception:
            value = ""
        if key in hub_keys and value and not found:
            found = str(value)
        if key in sheet_keys and value and not sheet_found:
            sheet_found = str(value)
        rows.append({"secret_key": key, "set": "YES" if value else "NO", "preview": masked_url(str(value)) if value else ""})
    return {"hub_url_on": bool(found), "hub_url_preview": masked_url(found), "google_sheet_url_on": bool(sheet_found), "google_sheet_url_preview": masked_url(sheet_found), "rows": rows}


def hub_setup_markdown() -> str:
    return """# MARU SPORTS Google Sheet 허브 설정

## 1. 구글시트 만들기
새 Google Sheet를 만들고 이름을 예: `MARU SPORTS HUB`로 둡니다.

## 2. Apps Script 열기
구글시트 상단 메뉴에서 `확장 프로그램 → Apps Script`를 엽니다.

## 3. 코드 붙여넣기
ZIP 안의 `google_apps_script_hub.gs` 내용을 Apps Script 편집기에 붙여넣고 저장합니다.

## 4. 웹앱 배포
`배포 → 새 배포 → 유형: 웹 앱`을 선택합니다.
실행 사용자: `나`, 액세스 권한: `모든 사용자` 또는 본인 환경에서 허용되는 웹앱 권한으로 배포합니다.

## 5. 웹앱 URL 복사
배포 후 나오는 `/exec`로 끝나는 웹앱 URL을 복사합니다.

## 6. Streamlit Secrets 설정
Streamlit Cloud → 앱 → Settings → Secrets에 아래처럼 넣습니다.

```toml
GAS_WEBAPP_URL = "복사한_구글_Apps_Script_웹앱_URL"
GOOGLE_SHEET_URL = "구글시트_주소창의_docs.google.com/spreadsheets/d/.../edit_주소"
```

`GAS_WEBAPP_URL`은 전송용이고, `GOOGLE_SHEET_URL`은 앱 안의 구글시트 바로가기 버튼용입니다.

## 7. 앱에서 확인
앱의 `허브 전송` 탭에서 `허브 설정 검사`와 `허브 실제 전송 테스트`를 누릅니다.
성공하면 구글시트에 `hub_payload_log`, `mobile_recommendations`, `analysis_scores`, `diagnosis`, `hub_send_logs_remote` 시트가 자동 생성됩니다.
"""


def validate_hub_payload(payload: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    problems = []
    required = ["app", "version", "type", "created_at", "counts", "diagnosis", "analysis_scores", "mobile_recommendations", "missing_data_report"]
    for key in required:
        if key not in payload:
            problems.append(f"payload 필수 키 없음: {key}")
    if not isinstance(payload.get("counts", {}), dict):
        problems.append("counts가 dict가 아님")
    if not isinstance(payload.get("diagnosis", {}), dict):
        problems.append("diagnosis가 dict가 아님")
    if not isinstance(payload.get("analysis_scores", []), list):
        problems.append("analysis_scores가 list가 아님")
    if not isinstance(payload.get("mobile_recommendations", []), list):
        problems.append("mobile_recommendations가 list가 아님")
    summary = {
        "app": payload.get("app", ""),
        "version": payload.get("version", ""),
        "type": payload.get("type", ""),
        "analysis_rows": len(payload.get("analysis_scores", [])) if isinstance(payload.get("analysis_scores", []), list) else -1,
        "mobile_rows": len(payload.get("mobile_recommendations", [])) if isinstance(payload.get("mobile_recommendations", []), list) else -1,
        "source_fixtures": payload.get("counts", {}).get("source_livescore_fixtures", 0) if isinstance(payload.get("counts", {}), dict) else 0,
        "standard_history": payload.get("counts", {}).get("standard_history_matches", 0) if isinstance(payload.get("counts", {}), dict) else 0,
        "hub_url": "ON" if get_hub_url() else "OFF",
        "google_sheet_url": "ON" if get_google_sheet_url() else "OFF",
        "missing_data_rows": len(payload.get("missing_data_report", [])) if isinstance(payload.get("missing_data_report", []), list) else -1,
    }
    return len(problems) == 0, problems, summary


def write_test_report(extra: Dict[str, Any] = None) -> str:
    ensure_dirs()
    payload = build_hub_payload("self_test_report")
    ok_payload, problems, payload_summary = validate_hub_payload(payload)
    ok_virtual, msg_virtual, details = virtual_backend_test()
    diag = build_diagnosis()
    lines = [
        f"# {APP_NAME} TEST REPORT",
        "",
        f"- version: {APP_VERSION}",
        f"- time: {now_text()}",
        f"- syntax_check: PASS",
        f"- virtual_backend_test: {'PASS' if ok_virtual else 'FAIL'}",
        f"- virtual_backend_message: {msg_virtual}",
        f"- hub_payload_structure: {'PASS' if ok_payload else 'FAIL'}",
        f"- hub_url: {'ON' if get_hub_url() else 'OFF'}",
        "",
        "## Payload Summary",
    ]
    for k, v in payload_summary.items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Virtual Backend Details"]
    for k, v in details.items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Current Counts"]
    for k, v in diag.get("counts", {}).items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Missing Data"]
    missing = diag.get("missing", [])
    if missing:
        lines += [f"- {m}" for m in missing]
    else:
        lines.append("- 큰 부족자료 없음")
    if problems:
        lines += ["", "## Payload Problems"] + [f"- {p}" for p in problems]
    if extra:
        lines += ["", "## Extra"] + [f"- {k}: {v}" for k, v in extra.items()]
    path = f"{LOG_DIR}/TEST_REPORT_RUNTIME.md"
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return path


def season_candidates() -> List[str]:
    now = datetime.now(KST)
    sy = now.year if now.month >= 7 else now.year - 1
    c = []
    for y in [sy, sy - 1, sy - 2, sy - 3]:
        c.append(f"{str(y)[-2:]}{str(y + 1)[-2:]}")
    for fallback in ["2526", "2425", "2324", "2223"]:
        if fallback not in c:
            c.append(fallback)
    return c


def fetch_football_data(leagues: List[str] = None, max_seasons: int = 3) -> Tuple[pd.DataFrame, pd.DataFrame]:
    leagues = leagues or list(LEAGUE_CODES.keys())
    rows, logs = [], []
    for season in season_candidates()[:max_seasons]:
        for code in leagues:
            url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
            log = {"time": now_text(), "source": "football-data", "url": url, "season": season, "league_code": code, "http_status": "", "rows": 0, "status": "fail", "message": ""}
            try:
                r = requests.get(url, timeout=10, headers={"User-Agent": "MARU-Sports-Analyzer/8"})
                log["http_status"] = str(r.status_code)
                if r.status_code != 200 or len(r.text.strip()) < 30:
                    log["message"] = "no_data_or_http_fail"
                    logs.append(log)
                    continue
                raw = pd.read_csv(StringIO(r.content.decode("utf-8", errors="ignore")))
                raw = normalize_columns(raw)
                count = 0
                for _, row in raw.iterrows():
                    date = normalize_date(row.get("date", ""))
                    home, away = clean(row.get("home_team", "")), clean(row.get("away_team", ""))
                    hs, aw = safe_int(row.get("home_score", "")), safe_int(row.get("away_score", ""))
                    if not date or not home or not away or hs is None or aw is None:
                        continue
                    rows.append({
                        "match_id": f"fd_{season}_{code}_{date}_{home}_{away}".replace(" ", "_"),
                        "date": date,
                        "kickoff_kst": "",
                        "sport": "축구",
                        "country": "",
                        "league": LEAGUE_CODES.get(code, code),
                        "league_code": code,
                        "home_team": home,
                        "away_team": away,
                        "home_score": hs,
                        "away_score": aw,
                        "status": "FT",
                        "source": f"football_data_{season}_{code}",
                    })
                    count += 1
                log.update({"rows": count, "status": "ok", "message": f"parsed_{count}"})
                logs.append(log)
            except Exception as exc:
                log["message"] = str(exc)
                logs.append(log)
                log_error("fetch_football_data", url, str(exc))
    return pd.DataFrame(rows), pd.DataFrame(logs)


def fetch_thesportsdb_fixtures(league_ids: Dict[str, str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    league_ids = league_ids or THESPORTSDB_LEAGUES
    rows, logs = [], []
    for league, lid in league_ids.items():
        url = f"https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id={lid}"
        log = {"time": now_text(), "source": "TheSportsDB", "url": url, "league": league, "http_status": "", "raw_events": 0, "parsed": 0, "status": "fail", "message": ""}
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "MARU-Sports-Analyzer/8"})
            log["http_status"] = str(r.status_code)
            if r.status_code != 200:
                log["message"] = f"HTTP {r.status_code}"
                logs.append(log)
                continue
            data = r.json()
            events = data.get("events") or []
            log["raw_events"] = len(events)
            for e in events:
                home = clean(e.get("strHomeTeam"))
                away = clean(e.get("strAwayTeam"))
                date = normalize_date(e.get("dateEvent"))
                time_raw = clean(e.get("strTime"))[:5]
                mid = clean(e.get("idEvent")) or f"tsdb_{lid}_{date}_{home}_{away}".replace(" ", "_")
                if not date or not home or not away:
                    continue
                rows.append({
                    "match_id": f"tsdb_{mid}",
                    "date": date,
                    "kickoff_kst": time_raw,
                    "sport": clean(e.get("strSport")) or "축구",
                    "country": clean(e.get("strCountry")),
                    "league": clean(e.get("strLeague")) or league,
                    "home_team": home,
                    "away_team": away,
                    "status": "SCHEDULED",
                    "source": f"thesportsdb_{lid}",
                    "home_score": "",
                    "away_score": "",
                })
            log.update({"parsed": len([x for x in rows if x.get("source") == f"thesportsdb_{lid}"]), "status": "ok", "message": "parsed"})
            logs.append(log)
        except Exception as exc:
            log["message"] = str(exc)
            logs.append(log)
            log_error("fetch_thesportsdb_fixtures", url, str(exc))
    return pd.DataFrame(rows), pd.DataFrame(logs)


def standardize_fixtures() -> Tuple[pd.DataFrame, str]:
    src = read_csv(SOURCE_FILES["source_livescore_fixtures"])
    if src.empty:
        write_csv(STANDARD_FILES["standard_upcoming_fixtures"], pd.DataFrame())
        return pd.DataFrame(), "일정표 source 없음"
    rows = []
    for _, r in src.iterrows():
        date, home, away = normalize_date(r.get("date")), clean(r.get("home_team")), clean(r.get("away_team"))
        if not date or not home or not away:
            continue
        hs, aw = clean(r.get("home_score")), clean(r.get("away_score"))
        # 예정경기만 추천 대상. 점수 있으면 완료 경기라 제외.
        if hs or aw:
            continue
        rows.append({
            "match_id": clean(r.get("match_id")) or f"up_{date}_{home}_{away}".replace(" ", "_"),
            "date": date,
            "kickoff_kst": clean(r.get("kickoff_kst")),
            "sport": clean(r.get("sport")) or "축구",
            "country": clean(r.get("country")),
            "league": clean(r.get("league")),
            "home_team": home,
            "away_team": away,
            "status": "SCHEDULED",
            "source": clean(r.get("source")) or "fixture_source",
        })
    df = pd.DataFrame(rows).drop_duplicates(subset=["match_id"], keep="last") if rows else pd.DataFrame()
    write_csv(STANDARD_FILES["standard_upcoming_fixtures"], df)
    return df, f"예정경기 {len(df)}건 표준화"


def standardize_history() -> Tuple[pd.DataFrame, str]:
    src = read_csv(SOURCE_FILES["source_football_data"])
    if src.empty:
        write_csv(STANDARD_FILES["standard_history_matches"], pd.DataFrame())
        return pd.DataFrame(), "과거자료 source 없음"
    rows = []
    for _, r in src.iterrows():
        date, home, away = normalize_date(r.get("date")), clean(r.get("home_team")), clean(r.get("away_team"))
        hs, aw = safe_int(r.get("home_score")), safe_int(r.get("away_score"))
        if not date or not home or not away or hs is None or aw is None:
            continue
        rows.append({
            "match_id": clean(r.get("match_id")) or f"hist_{date}_{home}_{away}".replace(" ", "_"),
            "date": date,
            "league": clean(r.get("league")),
            "league_code": clean(r.get("league_code")),
            "home_team": home,
            "away_team": away,
            "home_score": hs,
            "away_score": aw,
            "status": "FT",
            "source": clean(r.get("source")) or "history_source",
        })
    df = pd.DataFrame(rows).drop_duplicates(subset=["match_id"], keep="last") if rows else pd.DataFrame()
    write_csv(STANDARD_FILES["standard_history_matches"], df)
    return df, f"과거 완료경기 {len(df)}건 표준화"


def normalize_team_name(name: str) -> str:
    n = clean(name).lower()
    for token in [" fc", " cf", " afc", " utd", " united", ".", "-", "_"]:
        n = n.replace(token, " ")
    return " ".join(n.split())


def team_similarity(a: str, b: str) -> float:
    aa, bb = normalize_team_name(a), normalize_team_name(b)
    if not aa or not bb:
        return 0.0
    if aa == bb:
        return 1.0
    if aa in bb or bb in aa:
        return 0.88
    return SequenceMatcher(None, aa, bb).ratio()


def find_history_matches(history: pd.DataFrame, team: str, league: str = "", max_rows: int = 20) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame()
    df = history.copy()
    if league and "league" in df.columns:
        league_mask = df["league"].astype(str).str.lower() == league.lower()
        if league_mask.any():
            df = df[league_mask]
    sims_home = df["home_team"].astype(str).apply(lambda x: team_similarity(x, team))
    sims_away = df["away_team"].astype(str).apply(lambda x: team_similarity(x, team))
    df = df[(sims_home >= 0.72) | (sims_away >= 0.72)].copy()
    if df.empty:
        return df
    df["_sim"] = [max(h, a) for h, a in zip(sims_home.loc[df.index], sims_away.loc[df.index])]
    df = df.sort_values(["date", "_sim"], ascending=[False, False]).head(max_rows)
    return df.drop(columns=["_sim"], errors="ignore")


def calc_team_form(history: pd.DataFrame, team: str, league: str = "", n: int = 10) -> Dict[str, Any]:
    df = find_history_matches(history, team, league, max_rows=n)
    wins = draws = losses = gf = ga = 0
    form = []
    for _, r in df.iterrows():
        home, away = clean(r.get("home_team")), clean(r.get("away_team"))
        hs, aw = safe_int(r.get("home_score"), 0), safe_int(r.get("away_score"), 0)
        if team_similarity(home, team) >= team_similarity(away, team):
            f, a = hs, aw
        else:
            f, a = aw, hs
        gf += f; ga += a
        if f > a:
            wins += 1; form.append("W")
        elif f == a:
            draws += 1; form.append("D")
        else:
            losses += 1; form.append("L")
    m = wins + draws + losses
    return {
        "team": team, "league": league, "matches": m, "wins": wins, "draws": draws, "losses": losses,
        "goals_for": gf, "goals_against": ga,
        "avg_for": round(gf / m, 2) if m else 0, "avg_against": round(ga / m, 2) if m else 0,
        "points": wins * 3 + draws, "form_text": "-".join(form[:5]) if form else "자료없음",
    }


def calc_home_away(history: pd.DataFrame, team: str, side: str, league: str = "", n: int = 10) -> Dict[str, Any]:
    if history.empty:
        return {"team": team, "side": side, "matches": 0, "wins": 0, "draws": 0, "losses": 0, "avg_for": 0, "avg_against": 0}
    df = history.copy()
    if league and "league" in df.columns:
        ldf = df[df["league"].astype(str).str.lower() == league.lower()]
        if not ldf.empty:
            df = ldf
    if side == "home":
        mask = df["home_team"].astype(str).apply(lambda x: team_similarity(x, team) >= 0.72)
    else:
        mask = df["away_team"].astype(str).apply(lambda x: team_similarity(x, team) >= 0.72)
    df = df[mask].sort_values("date", ascending=False).head(n)
    wins = draws = losses = gf = ga = 0
    for _, r in df.iterrows():
        hs, aw = safe_int(r.get("home_score"), 0), safe_int(r.get("away_score"), 0)
        f, a = (hs, aw) if side == "home" else (aw, hs)
        gf += f; ga += a
        if f > a: wins += 1
        elif f == a: draws += 1
        else: losses += 1
    m = wins + draws + losses
    return {"team": team, "side": side, "league": league, "matches": m, "wins": wins, "draws": draws, "losses": losses, "avg_for": round(gf/m,2) if m else 0, "avg_against": round(ga/m,2) if m else 0}


def calc_h2h(history: pd.DataFrame, home: str, away: str, league: str = "", n: int = 10) -> Dict[str, Any]:
    if history.empty:
        return {"home_team": home, "away_team": away, "matches": 0, "home_wins": 0, "draws": 0, "away_wins": 0, "avg_goals": 0}
    df = history.copy()
    if league and "league" in df.columns:
        ldf = df[df["league"].astype(str).str.lower() == league.lower()]
        if not ldf.empty:
            df = ldf
    def involved(r):
        h, a = clean(r.get("home_team")), clean(r.get("away_team"))
        return ((team_similarity(h, home) >= .72 and team_similarity(a, away) >= .72) or
                (team_similarity(h, away) >= .72 and team_similarity(a, home) >= .72))
    df = df[df.apply(involved, axis=1)].sort_values("date", ascending=False).head(n)
    hw = awn = d = goals = 0
    for _, r in df.iterrows():
        h, a = clean(r.get("home_team")), clean(r.get("away_team"))
        hs, aas = safe_int(r.get("home_score"), 0), safe_int(r.get("away_score"), 0)
        goals += hs + aas
        home_is_listed_home = team_similarity(h, home) >= team_similarity(a, home)
        if hs == aas:
            d += 1
        elif (hs > aas and home_is_listed_home) or (aas > hs and not home_is_listed_home):
            hw += 1
        else:
            awn += 1
    m = hw + d + awn
    return {"home_team": home, "away_team": away, "league": league, "matches": m, "home_wins": hw, "draws": d, "away_wins": awn, "avg_goals": round(goals/m,2) if m else 0}


def build_bigdata_tables(fixtures: pd.DataFrame, history: pd.DataFrame):
    team_form_rows, home_away_rows, h2h_rows = [], [], []
    for _, f in fixtures.iterrows():
        league = clean(f.get("league"))
        home, away = clean(f.get("home_team")), clean(f.get("away_team"))
        if not home or not away:
            continue
        team_form_rows.append(calc_team_form(history, home, league, n=10))
        team_form_rows.append(calc_team_form(history, away, league, n=10))
        home_away_rows.append(calc_home_away(history, home, "home", league, n=10))
        home_away_rows.append(calc_home_away(history, away, "away", league, n=10))
        h2h_rows.append(calc_h2h(history, home, away, league, n=10))
    tf = pd.DataFrame(team_form_rows).drop_duplicates(subset=["team", "league"], keep="last") if team_form_rows else pd.DataFrame()
    ha = pd.DataFrame(home_away_rows).drop_duplicates(subset=["team", "league", "side"], keep="last") if home_away_rows else pd.DataFrame()
    hh = pd.DataFrame(h2h_rows)
    write_csv(STANDARD_FILES["standard_team_form"], tf)
    write_csv(STANDARD_FILES["standard_team_home_away"], ha)
    write_csv(STANDARD_FILES["standard_h2h"], hh)
    return tf, ha, hh


def parse_manual_sources():
    manual = read_csv(SOURCE_FILES["source_manual"])
    coaches = transfers = injuries = lineups = news = pd.DataFrame()
    if not manual.empty:
        coaches = manual[[c for c in ["team", "coach", "coach_start_date", "note"] if c in manual.columns]].dropna(how="all") if "coach" in manual.columns or "coach_start_date" in manual.columns else pd.DataFrame()
        transfers = manual[[c for c in ["team", "transfers", "scouting_note", "note"] if c in manual.columns]].dropna(how="all") if "transfers" in manual.columns or "scouting_note" in manual.columns else pd.DataFrame()
        injuries = manual[[c for c in ["team", "injuries", "missing_players", "note"] if c in manual.columns]].dropna(how="all") if "injuries" in manual.columns or "missing_players" in manual.columns else pd.DataFrame()
        lineups = manual[[c for c in ["team", "lineup", "note"] if c in manual.columns]].dropna(how="all") if "lineup" in manual.columns else pd.DataFrame()
        news = manual[[c for c in ["team", "news", "note"] if c in manual.columns]].dropna(how="all") if "news" in manual.columns else pd.DataFrame()
    write_csv(STANDARD_FILES["standard_coaches"], coaches)
    write_csv(STANDARD_FILES["standard_transfers"], transfers)
    write_csv(STANDARD_FILES["standard_injuries"], injuries)
    write_csv(STANDARD_FILES["standard_lineups"], lineups)
    write_csv(STANDARD_FILES["standard_news_flags"], news)
    return coaches, transfers, injuries, lineups, news


def generate_markets(fixtures: pd.DataFrame) -> pd.DataFrame:
    if fixtures.empty:
        write_csv(STANDARD_FILES["standard_markets"], pd.DataFrame())
        return pd.DataFrame()
    # source_proto_markets can override/provide real markets
    real = read_csv(SOURCE_FILES["source_proto_markets"])
    rows = []
    if not real.empty and "match_id" in real.columns and "market_type" in real.columns:
        rows = real.to_dict("records")
    else:
        for _, f in fixtures.iterrows():
            mid = clean(f.get("match_id"))
            for t in MARKET_TEMPLATES:
                row = {"match_id": mid, "league": clean(f.get("league")), "home_team": clean(f.get("home_team")), "away_team": clean(f.get("away_team")), "source": "template_not_real_proto", "status": "TEMPLATE"}
                row.update(t)
                rows.append(row)
    df = pd.DataFrame(rows)
    write_csv(STANDARD_FILES["standard_markets"], df)
    return df



def has_any_value(status: Dict[str, Any], keys: List[str]) -> bool:
    if not status:
        return False
    return any(clean(status.get(k)) for k in keys)


def status_text(ok: bool, label: str) -> str:
    return "있음" if ok else f"{label} 없음"


def build_missing_visibility_tables(fixtures: pd.DataFrame, coaches: pd.DataFrame, transfers: pd.DataFrame, injuries: pd.DataFrame, lineups: pd.DataFrame, news: pd.DataFrame, markets: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """경기별로 안 받은 현재자료를 별도 표로 만든다. 추천보다 먼저 눈으로 확인하기 위한 허브용 진단표."""
    rows_missing, rows_coach, rows_injury, rows_lineup, rows_transfer, rows_news, rows_proto = [], [], [], [], [], [], []
    now = now_text()
    if fixtures is None or fixtures.empty:
        frames = {
            "missing_data_report": pd.DataFrame(columns=EMPTY_SCHEMAS["missing_data_report"]),
            "coach_status": pd.DataFrame(columns=EMPTY_SCHEMAS["coach_status"]),
            "injury_status": pd.DataFrame(columns=EMPTY_SCHEMAS["injury_status"]),
            "lineup_status": pd.DataFrame(columns=EMPTY_SCHEMAS["lineup_status"]),
            "transfer_status": pd.DataFrame(columns=EMPTY_SCHEMAS["transfer_status"]),
            "news_status": pd.DataFrame(columns=EMPTY_SCHEMAS["news_status"]),
            "proto_market_status": pd.DataFrame(columns=EMPTY_SCHEMAS["proto_market_status"]),
        }
        for name, df in frames.items():
            write_csv(OUTPUT_FILES[name], df)
        return frames

    for _, f in fixtures.iterrows():
        mid = clean(f.get("match_id"))
        home = clean(f.get("home_team")); away = clean(f.get("away_team"))
        match = f"{home} vs {away}".strip(" vs ")
        hcoach = find_manual_status(coaches, home); acoach = find_manual_status(coaches, away)
        hinj = find_manual_status(injuries, home); ainj = find_manual_status(injuries, away)
        hline = find_manual_status(lineups, home); aline = find_manual_status(lineups, away)
        htrans = find_manual_status(transfers, home); atrans = find_manual_status(transfers, away)
        hnews = find_manual_status(news, home); anews = find_manual_status(news, away)
        coach_ok = has_any_value(hcoach, ["coach", "coach_start_date"]) or has_any_value(acoach, ["coach", "coach_start_date"])
        tactics_ok = has_any_value(hcoach, ["tactics", "note"]) or has_any_value(acoach, ["tactics", "note"])
        injury_ok = has_any_value(hinj, ["injuries", "note"]) or has_any_value(ainj, ["injuries", "note"])
        missing_player_ok = has_any_value(hinj, ["missing_players"]) or has_any_value(ainj, ["missing_players"])
        lineup_ok = has_any_value(hline, ["lineup", "formation", "note"]) or has_any_value(aline, ["lineup", "formation", "note"])
        transfer_ok = has_any_value(htrans, ["transfers"]) or has_any_value(atrans, ["transfers"])
        scout_ok = has_any_value(htrans, ["scouting_note", "note"]) or has_any_value(atrans, ["scouting_note", "note"])
        news_ok = has_any_value(hnews, ["news", "notice", "note"]) or has_any_value(anews, ["news", "notice", "note"])
        mdf = markets[markets["match_id"].astype(str) == mid] if markets is not None and not markets.empty and "match_id" in markets.columns else pd.DataFrame()
        real_proto_rows = 0
        template_rows = 0
        if not mdf.empty and "source" in mdf.columns:
            real_proto_rows = len(mdf[~mdf["source"].astype(str).str.contains("template_not_real_proto|market_template", na=False)])
            template_rows = len(mdf) - real_proto_rows
        proto_ok = real_proto_rows > 0
        missing_items = []
        checks = [
            (coach_ok, "감독 취임일"), (tactics_ok, "감독 전술"), (injury_ok, "주전 부상"),
            (missing_player_ok, "결장"), (lineup_ok, "예상 라인업"), ((transfer_ok or scout_ok), "영입/이적/스카우트"),
            (news_ok, "뉴스/공지"), (proto_ok, "실제 프로토 기준점/배당"),
        ]
        for ok, label in checks:
            if not ok:
                missing_items.append(label)
        base = {"created_at": now, "match_id": mid, "match": match, "league": clean(f.get("league")), "date": clean(f.get("date")), "kickoff_kst": clean(f.get("kickoff_kst"))}
        rows_missing.append({**base,
            "coach_status": status_text(coach_ok, "감독 취임일"), "tactics_status": status_text(tactics_ok, "감독 전술"),
            "injury_status": status_text(injury_ok, "주전 부상"), "suspension_status": status_text(missing_player_ok, "결장"),
            "lineup_status": status_text(lineup_ok, "예상 라인업"), "transfer_scout_status": status_text((transfer_ok or scout_ok), "영입/이적/스카우트"),
            "news_notice_status": status_text(news_ok, "뉴스/공지"), "proto_market_status": "실제 기준점 있음" if proto_ok else "실제 프로토 기준점/배당 없음 - 템플릿",
            "overall_status": "자료확인 필요" if missing_items else "현재자료 확인됨", "missing_items": " / ".join(missing_items)})
        rows_coach.append({"created_at": now, "match_id": mid, "match": match, "home_team": home, "away_team": away,
                           "home_coach_status": status_text(has_any_value(hcoach, ["coach", "coach_start_date"]), "감독 취임일"),
                           "away_coach_status": status_text(has_any_value(acoach, ["coach", "coach_start_date"]), "감독 취임일"),
                           "home_tactics_status": status_text(has_any_value(hcoach, ["tactics", "note"]), "감독 전술"),
                           "away_tactics_status": status_text(has_any_value(acoach, ["tactics", "note"]), "감독 전술")})
        rows_injury.append({"created_at": now, "match_id": mid, "match": match, "home_team": home, "away_team": away,
                            "home_injury_status": status_text(has_any_value(hinj, ["injuries", "note"]), "주전 부상"),
                            "away_injury_status": status_text(has_any_value(ainj, ["injuries", "note"]), "주전 부상"),
                            "home_missing_status": status_text(has_any_value(hinj, ["missing_players"]), "결장"),
                            "away_missing_status": status_text(has_any_value(ainj, ["missing_players"]), "결장")})
        rows_lineup.append({"created_at": now, "match_id": mid, "match": match, "home_team": home, "away_team": away,
                            "home_lineup_status": status_text(has_any_value(hline, ["lineup", "formation", "note"]), "예상 라인업"),
                            "away_lineup_status": status_text(has_any_value(aline, ["lineup", "formation", "note"]), "예상 라인업")})
        rows_transfer.append({"created_at": now, "match_id": mid, "match": match, "home_team": home, "away_team": away,
                              "home_transfer_status": status_text(has_any_value(htrans, ["transfers"]), "영입/이적"),
                              "away_transfer_status": status_text(has_any_value(atrans, ["transfers"]), "영입/이적"),
                              "home_scout_status": status_text(has_any_value(htrans, ["scouting_note", "note"]), "스카우트"),
                              "away_scout_status": status_text(has_any_value(atrans, ["scouting_note", "note"]), "스카우트")})
        rows_news.append({"created_at": now, "match_id": mid, "match": match, "home_team": home, "away_team": away,
                          "home_news_status": status_text(has_any_value(hnews, ["news", "notice", "note"]), "뉴스/공지"),
                          "away_news_status": status_text(has_any_value(anews, ["news", "notice", "note"]), "뉴스/공지")})
        rows_proto.append({"created_at": now, "match_id": mid, "match": match, "market_rows": len(mdf), "real_proto_rows": real_proto_rows,
                           "template_rows": template_rows, "status": "실제 프로토 기준점 있음" if proto_ok else "실제 프로토 기준점/배당 없음 - 템플릿"})
    frames = {
        "missing_data_report": pd.DataFrame(rows_missing), "coach_status": pd.DataFrame(rows_coach),
        "injury_status": pd.DataFrame(rows_injury), "lineup_status": pd.DataFrame(rows_lineup),
        "transfer_status": pd.DataFrame(rows_transfer), "news_status": pd.DataFrame(rows_news),
        "proto_market_status": pd.DataFrame(rows_proto),
    }
    for name, df in frames.items():
        write_csv(OUTPUT_FILES[name], df)
    return frames

def find_manual_status(df: pd.DataFrame, team: str) -> Dict[str, str]:
    if df.empty or "team" not in df.columns:
        return {}
    mask = df["team"].astype(str).apply(lambda x: team_similarity(x, team) >= .82)
    if not mask.any():
        return {}
    return df[mask].iloc[-1].to_dict()


def analyze_market(fixture: Dict[str, Any], market: Dict[str, Any], history: pd.DataFrame, team_form: pd.DataFrame, home_away: pd.DataFrame, h2h: pd.DataFrame, injuries: pd.DataFrame, lineups: pd.DataFrame, coaches: pd.DataFrame, transfers: pd.DataFrame, news: pd.DataFrame) -> Dict[str, Any]:
    home, away, league = clean(fixture.get("home_team")), clean(fixture.get("away_team")), clean(fixture.get("league"))
    home_form = calc_team_form(history, home, league, n=10)
    away_form = calc_team_form(history, away, league, n=10)
    home_home = calc_home_away(history, home, "home", league, n=10)
    away_away = calc_home_away(history, away, "away", league, n=10)
    h2h_stats = calc_h2h(history, home, away, league, n=10)
    home_inj = find_manual_status(injuries, home); away_inj = find_manual_status(injuries, away)
    home_line = find_manual_status(lineups, home); away_line = find_manual_status(lineups, away)
    home_coach = find_manual_status(coaches, home); away_coach = find_manual_status(coaches, away)
    home_trans = find_manual_status(transfers, home); away_trans = find_manual_status(transfers, away)
    home_news = find_manual_status(news, home); away_news = find_manual_status(news, away)

    data_score = 0
    missing = []
    if home_form["matches"] >= 5 and away_form["matches"] >= 5: data_score += 25
    else: missing.append("최근 팀폼 부족")
    if home_home["matches"] >= 3 and away_away["matches"] >= 3: data_score += 18
    else: missing.append("홈/원정 흐름 부족")
    if h2h_stats["matches"] >= 2: data_score += 12
    else: missing.append("상대전적 부족")
    if home_coach or away_coach: data_score += 10
    else: missing.append("감독 취임일/전술 없음")
    if home_inj or away_inj: data_score += 15
    else: missing.append("부상/결장 없음")
    if home_line or away_line: data_score += 10
    else: missing.append("예상 라인업 없음")
    if home_trans or away_trans or home_news or away_news: data_score += 10
    else: missing.append("영입/뉴스/스카우트 없음")

    home_power = home_form["points"] + home_home["wins"] * 1.8 + h2h_stats.get("home_wins", 0) * 1.2 + home_form["goals_for"] - home_form["goals_against"]
    away_power = away_form["points"] + away_away["wins"] * 1.8 + h2h_stats.get("away_wins", 0) * 1.2 + away_form["goals_for"] - away_form["goals_against"]
    diff = home_power - away_power
    total_goal_flow = home_form["avg_for"] + away_form["avg_for"]
    market_type = clean(market.get("market_type"))
    line_value = clean(market.get("line_value"))

    if data_score < 45:
        pick, conf, risk = "분석불가", 0, "높음"
    elif market_type == "승무패":
        pick = "홈 우세" if diff >= 3 else "원정 우세" if diff <= -3 else "접전/무승부 주의"
        conf = min(78, max(52, int(50 + abs(diff) * 2 + data_score * .18)))
        risk = "낮음" if conf >= 70 else "중간" if conf >= 58 else "높음"
    elif market_type == "언더오버":
        threshold = 2.5
        try: threshold = float(line_value or 2.5)
        except Exception: pass
        pick = "오버 우세" if total_goal_flow >= threshold + .35 else "언더 우세" if total_goal_flow <= threshold - .35 else "기준점 근접/주의"
        conf = min(75, max(51, int(52 + abs(total_goal_flow-threshold)*14 + data_score*.16)))
        risk = "낮음" if conf >= 70 else "중간" if conf >= 58 else "높음"
    elif market_type == "핸디캡":
        pick = "홈 핸디 우세" if diff >= 1.5 else "원정 핸디 우세" if diff <= -1.5 else "핸디 기준점 주의"
        conf = min(74, max(50, int(51 + abs(diff)*1.5 + data_score*.14)))
        risk = "중간" if conf >= 58 else "높음"
    elif market_type == "더블찬스":
        pick = "홈/무 안정" if diff >= 1 else "무/원정 안정" if diff <= -1 else "홈/원정 변동"
        conf = min(80, max(55, int(55 + abs(diff)*1.4 + data_score*.16)))
        risk = "낮음" if conf >= 70 else "중간"
    else:
        pick = "자료확인 필요" if data_score >= 45 else "분석불가"
        conf = int(data_score * .7) if data_score >= 45 else 0
        risk = "중간" if conf >= 58 else "높음"

    reasons = [
        f"홈 최근 {home_form['matches']}경기 {home_form['wins']}승 {home_form['draws']}무 {home_form['losses']}패",
        f"원정 최근 {away_form['matches']}경기 {away_form['wins']}승 {away_form['draws']}무 {away_form['losses']}패",
        f"홈 홈성적 {home_home['matches']}경기 {home_home['wins']}승",
        f"원정 원정성적 {away_away['matches']}경기 {away_away['wins']}승",
        f"상대전적 {h2h_stats['matches']}경기",
    ]
    return {
        "created_at": now_text(), "match_id": clean(fixture.get("match_id")), "date": clean(fixture.get("date")), "kickoff_kst": clean(fixture.get("kickoff_kst")),
        "sport": clean(fixture.get("sport")), "league": league, "home_team": home, "away_team": away,
        "match": f"{home} vs {away}", "market_type": market_type, "line_value": line_value,
        "pick": pick, "confidence": conf, "risk": risk, "data_sufficiency": min(100, data_score),
        "missing_data": " / ".join(missing), "reasons": " / ".join(reasons),
        "home_form": home_form["form_text"], "away_form": away_form["form_text"],
        "auto_buy": "NO", "auto_payment": "NO",
    }


def run_standardize_and_analyze() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    fixtures, fmsg = standardize_fixtures()
    history, hmsg = standardize_history()
    coaches, transfers, injuries, lineups, news = parse_manual_sources()
    markets = generate_markets(fixtures)
    tf, ha, hh = build_bigdata_tables(fixtures, history)
    missing_frames = build_missing_visibility_tables(fixtures, coaches, transfers, injuries, lineups, news, markets)

    results = []
    if not fixtures.empty and not markets.empty:
        for _, f in fixtures.iterrows():
            ms = markets[markets["match_id"].astype(str) == clean(f.get("match_id"))]
            for _, m in ms.iterrows():
                results.append(analyze_market(f.to_dict(), m.to_dict(), history, tf, ha, hh, injuries, lineups, coaches, transfers, news))
    analysis = pd.DataFrame(results)
    mobile = analysis[[c for c in ["created_at", "match_id", "match", "league", "date", "kickoff_kst", "market_type", "line_value", "pick", "confidence", "risk", "data_sufficiency", "missing_data", "reasons", "auto_buy", "auto_payment"] if c in analysis.columns]].copy() if not analysis.empty else pd.DataFrame()
    write_csv(OUTPUT_FILES["analysis_scores"], analysis)
    write_csv(OUTPUT_FILES["mobile_recommendations"], mobile)
    diagnosis = build_diagnosis()
    meta = {"fixtures_msg": fmsg, "history_msg": hmsg, "analysis_rows": len(analysis), "mobile_rows": len(mobile), "diagnosis": diagnosis, "missing_data_rows": len(read_csv(OUTPUT_FILES["missing_data_report"]))}
    log_run("standardize_analyze", "ok", f"analysis={len(analysis)}, mobile={len(mobile)}", meta)
    return analysis, mobile, meta


def build_diagnosis() -> Dict[str, Any]:
    counts = file_counts()
    missing = []
    if counts.get("source_livescore_fixtures", 0) == 0: missing.append("일정표 source 없음")
    if counts.get("source_football_data", 0) == 0: missing.append("과거자료 source 없음")
    if counts.get("standard_team_form", 0) == 0: missing.append("팀 최근폼 계산 없음")
    if counts.get("standard_team_home_away", 0) == 0: missing.append("홈/원정 계산 없음")
    if counts.get("standard_h2h", 0) == 0: missing.append("상대전적 계산 없음")
    if counts.get("standard_injuries", 0) == 0: missing.append("부상/결장 자료 없음")
    if counts.get("standard_lineups", 0) == 0: missing.append("라인업 자료 없음")
    if counts.get("standard_markets", 0) == 0: missing.append("승부식 자료 없음")
    if counts.get("missing_data_report", 0) == 0: missing.append("부족자료 진단표 없음")
    missing_report = read_csv(OUTPUT_FILES.get("missing_data_report", ""))
    missing_summary = {}
    if not missing_report.empty:
        for col in ["coach_status", "tactics_status", "injury_status", "suspension_status", "lineup_status", "transfer_scout_status", "news_notice_status", "proto_market_status"]:
            if col in missing_report.columns:
                missing_summary[col] = int(missing_report[col].astype(str).str.contains("없음|템플릿", na=False).sum())
    return {"time": now_text(), "counts": counts, "missing": missing, "missing_summary": missing_summary, "hub_url": "ON" if get_hub_url() else "OFF", "google_sheet_url": "ON" if get_google_sheet_url() else "OFF"}


def build_hub_payload(kind: str = "full_pipeline") -> Dict[str, Any]:
    counts = file_counts()
    payload = {
        "app": APP_NAME, "version": APP_VERSION, "type": kind, "created_at": now_text(),
        "hub_webapp_url_status": "ON" if get_hub_url() else "OFF",
        "google_sheet_url_status": "ON" if get_google_sheet_url() else "OFF",
        "google_sheet_url_preview": masked_url(get_google_sheet_url()),
        "counts": counts,
        "diagnosis": build_diagnosis(),
        "analysis_scores": read_csv(OUTPUT_FILES["analysis_scores"]).tail(300).to_dict("records"),
        "mobile_recommendations": read_csv(OUTPUT_FILES["mobile_recommendations"]).tail(300).to_dict("records"),
        "hub_send_logs": read_csv(OUTPUT_FILES["hub_send_logs"]).tail(50).to_dict("records"),
        "missing_data_report": read_csv(OUTPUT_FILES["missing_data_report"]).tail(300).to_dict("records"),
        "coach_status": read_csv(OUTPUT_FILES["coach_status"]).tail(300).to_dict("records"),
        "injury_status": read_csv(OUTPUT_FILES["injury_status"]).tail(300).to_dict("records"),
        "lineup_status": read_csv(OUTPUT_FILES["lineup_status"]).tail(300).to_dict("records"),
        "transfer_status": read_csv(OUTPUT_FILES["transfer_status"]).tail(300).to_dict("records"),
        "news_status": read_csv(OUTPUT_FILES["news_status"]).tail(300).to_dict("records"),
        "proto_market_status": read_csv(OUTPUT_FILES["proto_market_status"]).tail(300).to_dict("records"),
    }
    # include compact status for each file, not massive raw files
    payload["source_preview"] = {k: read_csv(v).head(5).to_dict("records") for k, v in SOURCE_FILES.items() if os.path.exists(v)}
    payload["standard_preview"] = {k: read_csv(v).head(5).to_dict("records") for k, v in STANDARD_FILES.items() if os.path.exists(v)}
    return payload


def save_hub_payload(payload: Dict[str, Any]) -> Tuple[str, str]:
    ensure_dirs()
    latest = OUTPUT_FILES["hub_payload_latest"]
    queue = OUTPUT_FILES["hub_payload_queue"]
    with open(latest, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(queue, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return latest, queue


def send_to_hub(payload: Dict[str, Any]) -> Tuple[bool, str]:
    latest, queue = save_hub_payload(payload)
    url = get_hub_url()
    base_log = {"time": now_text(), "payload_type": payload.get("type", ""), "payload_latest": latest, "payload_queue": queue, "rows_mobile": len(payload.get("mobile_recommendations", [])), "hub_url": "ON" if url else "OFF", "google_sheet_url": "ON" if get_google_sheet_url() else "OFF"}
    if not url:
        msg = "허브 URL OFF: 실제 전송 대신 payload 저장 완료"
        append_csv(OUTPUT_FILES["hub_send_logs"], pd.DataFrame([{**base_log, "status": "queued", "message": msg, "http_status": ""}]))
        log_run("hub_send", "queued", msg)
        return False, msg
    try:
        r = requests.post(url, json=payload, timeout=20)
        ok = 200 <= r.status_code < 300
        msg = f"HTTP {r.status_code}: {r.text[:300]}"
        append_csv(OUTPUT_FILES["hub_send_logs"], pd.DataFrame([{**base_log, "status": "sent" if ok else "fail", "message": msg, "http_status": r.status_code}]))
        log_run("hub_send", "sent" if ok else "fail", msg)
        return ok, msg
    except Exception as exc:
        msg = f"허브 전송 오류: {exc}"
        append_csv(OUTPUT_FILES["hub_send_logs"], pd.DataFrame([{**base_log, "status": "error", "message": msg, "http_status": ""}]))
        log_error("hub_send", url, str(exc))
        return False, msg


def run_full_pipeline(auto_fixtures=True, auto_history=True, send_hub=True):
    report = []
    if auto_fixtures:
        fx, logs = fetch_thesportsdb_fixtures()
        n, total = append_csv(SOURCE_FILES["source_livescore_fixtures"], fx, ["match_id"])
        append_csv(OUTPUT_FILES["run_logs"], logs.rename(columns={"status":"source_status"}) if not logs.empty else pd.DataFrame())
        report.append(f"일정표 자동수집: 신규 {n}, 전체 {total}")
        log_run("fixture_collect", "ok", report[-1])
    if auto_history:
        hist, hlogs = fetch_football_data(max_seasons=2)
        n, total = append_csv(SOURCE_FILES["source_football_data"], hist, ["match_id"])
        append_csv(OUTPUT_FILES["run_logs"], hlogs.rename(columns={"status":"source_status"}) if not hlogs.empty else pd.DataFrame())
        report.append(f"과거자료 자동수집: 신규 {n}, 전체 {total}")
        log_run("history_collect", "ok", report[-1])
    analysis, mobile, meta = run_standardize_and_analyze()
    report.append(f"분석/모바일 생성: analysis {len(analysis)}, mobile {len(mobile)}")
    hub_msg = "허브 전송 생략"
    if send_hub:
        ok, hub_msg = send_to_hub(build_hub_payload("full_pipeline"))
        report.append("허브: " + hub_msg)
    return report


def make_status_report() -> str:
    diag = build_diagnosis()
    counts = diag["counts"]
    lines = [f"# {APP_NAME} 상태 리포트", "", f"- version: {APP_VERSION}", f"- time: {now_text()}", f"- hub_url: {diag['hub_url']}", f"- google_sheet_url: {diag.get('google_sheet_url','OFF')}", "", "## 파일별 저장 건수"]
    for k, v in counts.items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## 부족자료"]
    if diag["missing"]:
        lines += [f"- {m}" for m in diag["missing"]]
    else:
        lines.append("- 큰 부족자료 없음")
    lines += ["", "## 부족자료 상세표"]
    miss_df = read_csv(OUTPUT_FILES["missing_data_report"]).tail(30)
    if miss_df.empty:
        lines.append("부족자료 상세표 없음")
    else:
        lines.append(miss_df.to_csv(index=False))
    lines += ["", "## 최근 모바일 추천"]
    mob = read_csv(OUTPUT_FILES["mobile_recommendations"]).tail(20)
    if mob.empty:
        lines.append("모바일 추천 없음")
    else:
        lines.append(mob.to_csv(index=False))
    return "\n".join(lines)


def make_log_bundle() -> bytes:
    ensure_dirs()
    report = make_status_report()
    bio = BytesIO()
    written = set()

    def add_bytes(z, arcname: str, data: bytes):
        if arcname in written:
            return
        z.writestr(arcname, data)
        written.add(arcname)

    def add_file(z, path: str, arcname: str):
        if not os.path.exists(path) or arcname in written:
            return
        z.write(path, arcname)
        written.add(arcname)

    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        add_bytes(z, "MARU_STATUS_REPORT.md", report.encode("utf-8-sig"))
        try:
            rt = write_test_report({"bundle_created": now_text()})
            add_file(z, rt, "TEST_REPORT_RUNTIME.md")
        except Exception as exc:
            add_bytes(z, "TEST_REPORT_RUNTIME_ERROR.txt", str(exc).encode("utf-8-sig"))
        for group_name, group in [("source", SOURCE_FILES), ("standard", STANDARD_FILES), ("output", OUTPUT_FILES)]:
            for name, path in group.items():
                if not os.path.exists(path):
                    continue
                arc = f"{group_name}/{os.path.basename(path)}"
                add_file(z, path, arc)
        # 사용자가 바로 확인하기 쉬운 핵심 허브 파일은 root에도 1회만 별도 복사
        add_file(z, OUTPUT_FILES["hub_payload_latest"], "hub_payload_latest.json")
        add_file(z, OUTPUT_FILES["hub_payload_queue"], "hub_payload_queue.jsonl")
    bio.seek(0)
    return bio.read()


def virtual_backend_test() -> Tuple[bool, str, Dict[str, Any]]:
    # no overwrite of user data. Runs all major functions on in-memory frames and checks expected output shape.
    fixtures = pd.DataFrame([
        {"match_id":"vt_001","date":"2026-07-10","kickoff_kst":"20:00","sport":"축구","league":"English Premier League","home_team":"Arsenal","away_team":"Chelsea","status":"SCHEDULED","source":"virtual"},
        {"match_id":"vt_002","date":"2026-07-10","kickoff_kst":"22:00","sport":"축구","league":"Spanish La Liga","home_team":"Barcelona","away_team":"Athletic Bilbao","status":"SCHEDULED","source":"virtual"},
    ])
    hist_rows = []
    teams = [("Arsenal","Chelsea","English Premier League"),("Barcelona","Athletic Bilbao","Spanish La Liga")]
    for home, away, league in teams:
        for i in range(12):
            hist_rows.append({"match_id":f"vh_{home}_{i}","date":f"2026-06-{str(i+1).zfill(2)}","league":league,"home_team":home,"away_team":away,"home_score":2 if i%3 else 1,"away_score":1 if i%4 else 2,"status":"FT","source":"virtual"})
            hist_rows.append({"match_id":f"va_{away}_{i}","date":f"2026-05-{str(i+1).zfill(2)}","league":league,"home_team":"Other","away_team":away,"home_score":1,"away_score":1 if i%2 else 2,"status":"FT","source":"virtual"})
    history = pd.DataFrame(hist_rows)
    tf, ha, hh = build_bigdata_tables(fixtures, history)
    markets = []
    for _, f in fixtures.iterrows():
        for t in MARKET_TEMPLATES[:3]:
            r = {"match_id":f["match_id"],"league":f["league"],"home_team":f["home_team"],"away_team":f["away_team"],"source":"virtual","status":"VIRTUAL"}; r.update(t); markets.append(r)
    markets = pd.DataFrame(markets)
    empty = pd.DataFrame()
    results = []
    for _, f in fixtures.iterrows():
        for _, m in markets[markets["match_id"] == f["match_id"]].iterrows():
            results.append(analyze_market(f.to_dict(), m.to_dict(), history, tf, ha, hh, empty, empty, empty, empty, empty))
    analysis = pd.DataFrame(results)
    payload = {"app":APP_NAME,"version":APP_VERSION,"type":"virtual_test","created_at":now_text(),"analysis_scores":analysis.to_dict("records"),"mobile_recommendations":analysis.to_dict("records"),"counts":{"fixtures":len(fixtures),"history":len(history),"markets":len(markets),"analysis":len(analysis)}}
    ok = len(fixtures)==2 and len(history)>=20 and len(tf)>=4 and len(ha)>=4 and len(hh)==2 and len(analysis)==6 and "pick" in analysis.columns and len(payload["mobile_recommendations"])==6
    details = {"fixtures":len(fixtures),"history":len(history),"team_form":len(tf),"home_away":len(ha),"h2h":len(hh),"markets":len(markets),"analysis":len(analysis),"payload_mobile":len(payload["mobile_recommendations"])}
    return ok, "가상 백엔드 전체 테스트 통과" if ok else "가상 백엔드 테스트 실패", details


def render_download_bar(location: str):
    st.markdown("#### 📦 로그/허브 자료 받기")
    c1, c2, c3, c4, c5 = st.columns(5)
    report = make_status_report().encode("utf-8-sig")
    bundle = make_log_bundle()
    with c1:
        st.download_button("📄 상태 리포트 받기", report, "MARU_STATUS_REPORT.md", "text/markdown", key=f"report_{location}")
    with c2:
        st.download_button("📦 전체 로그 ZIP 받기", bundle, "MARU_LOG_BUNDLE.zip", "application/zip", key=f"zip_{location}")
    with c3:
        payload_path = OUTPUT_FILES["hub_payload_latest"]
        payload_bytes = open(payload_path, "rb").read() if os.path.exists(payload_path) else json.dumps(build_hub_payload("manual_download"), ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button("📤 허브 Payload 받기", payload_bytes, "hub_payload_latest.json", "application/json", key=f"payload_{location}")
    with c4:
        hub_logs = read_csv(OUTPUT_FILES["hub_send_logs"]).to_csv(index=False).encode("utf-8-sig")
        st.download_button("📜 허브 전송 로그 받기", hub_logs, "hub_send_logs.csv", "text/csv", key=f"hublog_{location}")
    with c5:
        sheet_url = get_google_sheet_url()
        if sheet_url:
            st.link_button("📊 구글시트 열기", sheet_url)
        else:
            st.caption("시트 URL OFF")


def render_metrics():
    c = file_counts()
    cols = st.columns(6)
    cols[0].metric("일정표 source", c.get("source_livescore_fixtures",0))
    cols[1].metric("과거자료 source", c.get("source_football_data",0))
    cols[2].metric("예정경기 standard", c.get("standard_upcoming_fixtures",0))
    cols[3].metric("빅데이터 form", c.get("standard_team_form",0) + c.get("standard_team_home_away",0) + c.get("standard_h2h",0))
    cols[4].metric("모바일 카드", c.get("mobile_recommendations",0))
    cols[5].metric("허브 URL", "ON" if get_hub_url() else "OFF")


def render_full_run():
    st.subheader("🚀 전체실행")
    st.caption("일정표 → 과거자료 → 빅데이터 매칭 → 분석 → 모바일 추천 → 허브 전송/큐 저장까지 한 번에 실행합니다.")
    render_download_bar("full_top")
    render_metrics()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 전체 실행하고 허브까지 보내기", type="primary"):
            with st.spinner("전체 파이프라인 실행 중..."):
                report = run_full_pipeline(True, True, True)
            for line in report:
                st.success(line) if "허브:" not in line or "오류" not in line else st.warning(line)
            render_download_bar("full_after")
    with c2:
        if st.button("🧪 가상 백엔드 전체 테스트"):
            ok, msg, details = virtual_backend_test()
            st.success(msg) if ok else st.error(msg)
            st.json(details)
    st.divider()
    render_recent_outputs()


def render_recent_outputs():
    t1, t2, t3, t4 = st.tabs(["모바일 추천", "분석 점수", "허브 로그", "부족자료 진단표"])
    with t1:
        df = read_csv(OUTPUT_FILES["mobile_recommendations"])
        st.dataframe(df.tail(100), width="stretch") if not df.empty else st.info("모바일 추천 없음")
    with t2:
        df = read_csv(OUTPUT_FILES["analysis_scores"])
        st.dataframe(df.tail(100), width="stretch") if not df.empty else st.info("분석 점수 없음")
    with t3:
        df = read_csv(OUTPUT_FILES["hub_send_logs"])
        st.dataframe(df.tail(100), width="stretch") if not df.empty else st.info("허브 로그 없음")
    with t4:
        miss = read_csv(OUTPUT_FILES["missing_data_report"])
        st.json(build_diagnosis())
        st.dataframe(miss.tail(100), width="stretch") if not miss.empty else st.info("부족자료 진단표 없음")


def render_fixture_tab():
    st.subheader("📅 일정표")
    st.info("일정표는 자동수집이 기본입니다. 수동 입력은 빠진 경기 보완용입니다.")
    if st.button("📅 일정표 자동수집 실행", type="primary"):
        fx, logs = fetch_thesportsdb_fixtures()
        n, total = append_csv(SOURCE_FILES["source_livescore_fixtures"], fx, ["match_id"])
        append_csv(OUTPUT_FILES["run_logs"], logs, subset=None)
        st.success(f"일정표 저장: 신규 {n}건 · 전체 {total}건")
        st.dataframe(logs, width="stretch")
    with st.expander("CSV/표 붙여넣기로 일정표 보완", expanded=False):
        sample = "date,kickoff_kst,sport,league,home_team,away_team,status,source,match_id\n2026-07-10,20:00,축구,K League,Ulsan,Jeonbuk,SCHEDULED,manual,manual_001\n"
        text = st.text_area("일정표 CSV", value=sample, height=120)
        if st.button("일정표 보완 저장"):
            df = normalize_columns(pd.read_csv(StringIO(text)))
            n,total = append_csv(SOURCE_FILES["source_livescore_fixtures"], df, ["match_id"])
            st.success(f"저장: 신규 {n}, 전체 {total}")
    df = read_csv(SOURCE_FILES["source_livescore_fixtures"])
    st.dataframe(df.tail(100), width="stretch") if not df.empty else st.info("일정표 source 없음")


def render_data_input_tab():
    st.subheader("🧾 자료 입력")
    st.caption("감독 취임일, 감독 전술, 영입/이적/스카우트, 주전 부상, 결장, 예상 라인업, 뉴스/공지는 manual 자료로 보완합니다. 안 받은 자료는 missing_data_report로 따로 표시됩니다.")
    sample = "team,coach,coach_start_date,injuries,missing_players,lineup,transfers,scouting_note,news,note\nArsenal,Mikel Arteta,2019-12-20,,,주전 확인 필요,영입 확인 필요,,뉴스 확인 필요,\nChelsea,,,주전 수비수 체크,1명 확인 필요,,이적생 출전 여부,,감독 인터뷰 확인,\n"
    text = st.text_area("manual CSV", value=sample, height=160)
    if st.button("manual 현재자료 저장", type="primary"):
        df = normalize_columns(pd.read_csv(StringIO(text)))
        n,total = append_csv(SOURCE_FILES["source_manual"], df, ["team"])
        st.success(f"manual 저장: 신규 {n}, 전체 {total}")
    df = read_csv(SOURCE_FILES["source_manual"])
    st.dataframe(df.tail(100), width="stretch") if not df.empty else st.info("manual 자료 없음")


def render_hub_tab():
    st.subheader("📤 허브/구글시트")
    st.caption("전체실행 결과와 missing_data_report까지 구글시트 허브로 실제 전송하거나, URL이 없으면 payload 큐로 저장합니다.")

    status = hub_secrets_status()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("허브 URL", "ON" if status["hub_url_on"] else "OFF")
    m2.metric("구글시트 바로가기", "ON" if status.get("google_sheet_url_on") else "OFF")
    m3.metric("Payload 최신", "ON" if os.path.exists(OUTPUT_FILES["hub_payload_latest"]) else "OFF")
    m4.metric("전송 로그", len(read_csv(OUTPUT_FILES["hub_send_logs"])))

    sheet_url = get_google_sheet_url()
    if sheet_url:
        st.link_button("📊 구글시트 허브 바로가기", sheet_url)
    else:
        st.warning("GOOGLE_SHEET_URL Secret이 없어 앱 안에서 구글시트 바로가기 버튼을 열 수 없습니다. 전송은 GAS_WEBAPP_URL로 가능하지만, 바로가기는 GOOGLE_SHEET_URL을 추가해야 합니다.")

    with st.expander("① 구글시트 허브 설정법", expanded=not status["hub_url_on"]):
        st.markdown(hub_setup_markdown())
        try:
            script_text = open("google_apps_script_hub.gs", "r", encoding="utf-8").read()
        except Exception:
            script_text = "google_apps_script_hub.gs 파일을 찾을 수 없습니다. ZIP 안 파일을 확인하세요."
        st.download_button("📜 Apps Script 코드 받기", script_text.encode("utf-8-sig"), "google_apps_script_hub.gs", "text/plain", key="gas_script_download")
        st.dataframe(pd.DataFrame(status["rows"]), width="stretch")

    with st.expander("② 허브 Payload 구조 검사", expanded=True):
        payload = build_hub_payload("hub_payload_check")
        ok_payload, problems, summary = validate_hub_payload(payload)
        if ok_payload:
            st.success("허브 payload 구조 검사 통과")
        else:
            st.error("허브 payload 구조 문제 있음")
            st.write(problems)
        st.json(summary)

    render_download_bar("hub")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📤 현재 결과 허브 전송/큐 저장", type="primary"):
            ok, msg = send_to_hub(build_hub_payload("manual_hub_send"))
            st.success(msg) if ok else st.warning(msg)
    with c2:
        if st.button("🧪 허브 dry-run payload 생성"):
            latest, queue = save_hub_payload(build_hub_payload("dry_run"))
            st.success(f"payload 저장 완료: {latest}, {queue}")
    with c3:
        if st.button("✅ 허브 실제 전송 테스트"):
            test_payload = build_hub_payload("hub_connection_test")
            ok, msg = send_to_hub(test_payload)
            if ok:
                st.success("구글시트 허브 실제 전송 성공: " + msg)
            else:
                st.warning("실제 전송 미완료/대기: " + msg)

    st.markdown("#### 최근 허브 전송 로그")
    st.dataframe(read_csv(OUTPUT_FILES["hub_send_logs"]).tail(100), width="stretch")

def render_diagnosis_tab():
    st.subheader("🧪 백엔드 진단")
    render_download_bar("diag")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧪 가상 백엔드 전체 테스트", type="primary"):
            ok, msg, details = virtual_backend_test()
            st.success(msg) if ok else st.error(msg)
            st.json(details)
            write_csv(OUTPUT_FILES["backend_diagnosis"], pd.DataFrame([{**details, "time": now_text(), "status": "ok" if ok else "fail"}]))
    with c2:
        if st.button("📋 전체 기본 검사표 생성"):
            path = write_test_report({"manual_test_button": now_text()})
            st.success(f"검사표 생성 완료: {path}")
            st.download_button("📋 TEST_REPORT_RUNTIME 받기", open(path, "rb").read(), "TEST_REPORT_RUNTIME.md", "text/markdown", key="runtime_test_report_download")
    st.json(build_diagnosis())
    with st.expander("최근 실행 로그", expanded=True):
        st.dataframe(read_csv(OUTPUT_FILES["run_logs"]).tail(200), width="stretch")
    with st.expander("최근 오류 로그", expanded=False):
        st.dataframe(read_csv(OUTPUT_FILES["error_logs"]).tail(200), width="stretch")


def render_mobile_tab():
    st.subheader("📱 모바일 추천")
    df = read_csv(OUTPUT_FILES["mobile_recommendations"])
    if df.empty:
        st.warning("모바일 추천카드 없음. 전체실행을 먼저 실행하세요.")
        return
    for _, r in df.tail(50).iterrows():
        st.markdown(f"""
        <div style='border:1px solid #ddd;border-radius:14px;padding:14px;margin-bottom:10px;background:white'>
        <div style='font-size:13px;color:#777'>{clean(r.get('league'))} · {clean(r.get('date'))} {clean(r.get('kickoff_kst'))}</div>
        <div style='font-size:22px;font-weight:800'>{clean(r.get('match'))}</div>
        <div style='margin:8px 0'>승부식: <b>{clean(r.get('market_type'))}</b> 기준점: <b>{clean(r.get('line_value'))}</b></div>
        <div>추천: <b>{clean(r.get('pick'))}</b> · 신뢰도 <b>{clean(r.get('confidence'))}%</b> · 위험도 <b>{clean(r.get('risk'))}</b> · 자료충분도 <b>{clean(r.get('data_sufficiency'))}%</b></div>
        <div style='font-size:13px;color:#555;margin-top:8px'>근거: {clean(r.get('reasons'))}</div>
        <div style='font-size:13px;color:#a33;margin-top:4px'>부족자료: {clean(r.get('missing_data'))}</div>
        <div style='font-size:12px;color:#777;margin-top:6px'>자동구매/자동결제 없음</div>
        </div>
        """, unsafe_allow_html=True)


def main():
    ensure_dirs()
    st.set_page_config(page_title=APP_NAME, page_icon="⚽", layout="wide", initial_sidebar_state="collapsed")
    st.title("⚽ 마루 스포츠 프로토 일정 허브")
    st.caption("일정표 자동수집 → 과거 빅데이터 매칭 → 승부식 분석 → 모바일 추천 → 허브/구글시트 전송")
    render_metrics()
    tabs = st.tabs(["전체실행", "PC 모니터링", "일정표", "자료 입력", "모바일 추천", "허브 전송", "백엔드 진단"])
    with tabs[0]: render_full_run()
    with tabs[1]:
        render_download_bar("monitor")
        render_recent_outputs()
    with tabs[2]: render_fixture_tab()
    with tabs[3]: render_data_input_tab()
    with tabs[4]: render_mobile_tab()
    with tabs[5]: render_hub_tab()
    with tabs[6]: render_diagnosis_tab()
    st.caption(f"{APP_VERSION} · {now_text()} · 자동구매/자동결제 없음")


if __name__ == "__main__":
    main()
