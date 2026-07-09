import os
import json
import zipfile
import hashlib
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
APP_VERSION = "v19-ticket-matching-premium-mobile"
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
    "sportmonks_status": f"{DATA_DIR}/sportmonks_status.csv",
    "fixture_prediction_results": f"{DATA_DIR}/fixture_prediction_results.csv",
    "prediction_explain": f"{DATA_DIR}/prediction_explain.csv",
    "offline_checklist": f"{DATA_DIR}/offline_checklist.csv",
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
    "sportmonks_status": ["time", "provider", "enabled", "token_detected", "token_preview", "url_template", "safe_final_url", "http_status", "status", "response_data_count", "parsed_rows", "participants_parsed", "message", "response_preview"],
    "fixture_prediction_results": ["created_at", "match_id", "date", "kickoff_kst", "league", "home_team", "away_team", "match", "match_status", "home_score", "away_score", "actual_result", "pred_1x2", "pred_1x2_conf", "pred_1x2_risk", "pred_handicap", "pred_overunder", "pred_doublechance", "main_candidate", "main_confidence", "main_risk", "proto_status", "missing_data"],
    "prediction_explain": ["created_at", "match_id", "date", "kickoff_kst", "league", "home_team", "away_team", "home_team_ko", "away_team_ko", "main_prediction", "confidence", "risk", "recent_form", "home_away_form", "h2h", "why_summary", "missing_data", "final_note"],
    "offline_checklist": ["created_at", "match_id", "date", "kickoff_kst", "league", "home_team_ko", "away_team_ko", "main_prediction", "check_match", "check_time", "check_1x2", "check_handicap", "check_overunder", "check_odds_change", "check_livescore", "check_manual_marking", "auto_buy", "auto_payment"],
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


def get_secret_value(keys: List[str], default: str = "") -> str:
    """Read one of several Streamlit Secret names without crashing outside Streamlit."""
    for key in keys:
        try:
            v = st.secrets.get(key, "")
            if v is not None and str(v).strip() != "":
                return str(v).strip()
        except Exception:
            pass
    return default


def use_slow_api_enabled() -> bool:
    v = get_secret_value(["USE_SLOW_API", "use_slow_api"], "N").upper()
    return v in {"Y", "YES", "TRUE", "1", "ON"}


def get_sportmonks_token() -> str:
    return get_secret_value(["SPORTMONKS_API_TOKEN", "SPORTMONKS_API_KEY", "SPORTS_API_KEY", "sportmonks_api_token", "sports_api_key"], "")


def get_sportmonks_url_template() -> str:
    return get_secret_value([
        "SKYTOTO_SPORTS_API_URL", "SPORTMONKS_API_URL", "sportmonks_api_url"
    ], "https://api.sportmonks.com/v3/football/fixtures/between/{today_dash}/{to_dash}?api_token={api_key}&include=participants;league")


def masked_secret(value: str) -> str:
    value = clean(value)
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return value[:4] + "…" + value[-4:]


def build_sportmonks_url() -> Tuple[str, str]:
    token = get_sportmonks_token()
    today = datetime.now(KST).date()
    to_day = today + timedelta(days=7)
    template = get_sportmonks_url_template()
    final_url = template.replace("{today_dash}", today.isoformat()).replace("{to_dash}", to_day.isoformat()).replace("{api_key}", token)
    safe_url = final_url.replace(token, masked_secret(token)) if token else final_url
    return final_url, safe_url


def sportmonks_secret_status() -> Dict[str, Any]:
    token = get_sportmonks_token()
    template = get_sportmonks_url_template()
    return {
        "enabled": "Y" if use_slow_api_enabled() else "N",
        "token_detected": bool(token),
        "token_preview": masked_secret(token),
        "url_template": template,
    }


def extract_participant_name(p: Dict[str, Any]) -> str:
    for key in ["name", "short_code", "display_name", "common_name"]:
        val = clean(p.get(key))
        if val:
            return val
    return ""


def parse_sportmonks_fixture(item: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    participants = item.get("participants") or []
    home = away = ""
    participants_parsed = 0
    if isinstance(participants, list):
        for p in participants:
            if not isinstance(p, dict):
                continue
            name = extract_participant_name(p)
            if name:
                participants_parsed += 1
            meta = p.get("meta") or {}
            loc = clean(meta.get("location") or meta.get("type") or p.get("location")).lower()
            if loc == "home":
                home = name
            elif loc == "away":
                away = name
        if not home and len(participants) >= 1 and isinstance(participants[0], dict):
            home = extract_participant_name(participants[0])
        if not away and len(participants) >= 2 and isinstance(participants[1], dict):
            away = extract_participant_name(participants[1])
    league_obj = item.get("league") or {}
    starting_at = clean(item.get("starting_at") or item.get("starting_at_timestamp") or item.get("date"))
    date = normalize_date(starting_at[:10]) if starting_at else ""
    kickoff = ""
    if len(starting_at) >= 16 and ":" in starting_at:
        kickoff = starting_at[11:16]
    mid = clean(item.get("id") or item.get("fixture_id")) or f"sportmonks_{date}_{home}_{away}".replace(" ", "_")
    row = {
        "match_id": f"sm_{mid}",
        "date": date,
        "kickoff_kst": kickoff,
        "sport": "축구",
        "country": clean(item.get("country") or (league_obj.get("country") if isinstance(league_obj, dict) else "")),
        "league": clean(league_obj.get("name") if isinstance(league_obj, dict) else item.get("league_name")),
        "home_team": home,
        "away_team": away,
        "status": clean((item.get("state") or {}).get("name") if isinstance(item.get("state"), dict) else item.get("status")) or "SCHEDULED",
        "source": "sportmonks",
        "home_score": "",
        "away_score": "",
    }
    return row, participants_parsed


def fetch_sportmonks_fixtures() -> Tuple[pd.DataFrame, pd.DataFrame]:
    status = sportmonks_secret_status()
    final_url, safe_url = build_sportmonks_url()
    log = {
        "time": now_text(),
        "provider": "sportmonks",
        "enabled": status["enabled"],
        "token_detected": status["token_detected"],
        "token_preview": status["token_preview"],
        "url_template": status["url_template"],
        "safe_final_url": safe_url,
        "http_status": "",
        "status": "skipped",
        "response_data_count": 0,
        "parsed_rows": 0,
        "participants_parsed": 0,
        "message": "",
        "response_preview": "",
    }
    if not use_slow_api_enabled():
        log["message"] = "USE_SLOW_API=N 이라 Sportmonks 호출 생략"
        write_csv(OUTPUT_FILES["sportmonks_status"], pd.DataFrame([log]))
        return pd.DataFrame(), pd.DataFrame([log])
    if not get_sportmonks_token():
        log["status"] = "no_token"
        log["message"] = "Sportmonks 키가 비어 있어 호출 생략"
        write_csv(OUTPUT_FILES["sportmonks_status"], pd.DataFrame([log]))
        return pd.DataFrame(), pd.DataFrame([log])
    try:
        r = requests.get(final_url, timeout=12, headers={"User-Agent": "MARU-Sports-Analyzer/13"})
        log["http_status"] = str(r.status_code)
        log["response_preview"] = r.text[:900]
        if not (200 <= r.status_code < 300):
            log["status"] = "http_error"
            log["message"] = f"HTTP {r.status_code}"
            write_csv(OUTPUT_FILES["sportmonks_status"], pd.DataFrame([log]))
            log_error("fetch_sportmonks_fixtures", safe_url, log["message"])
            return pd.DataFrame(), pd.DataFrame([log])
        data = r.json()
        items = data.get("data") if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = []
        log["response_data_count"] = len(items)
        rows = []
        participants_total = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            row, pp = parse_sportmonks_fixture(item)
            participants_total += pp
            if row.get("date") and row.get("home_team") and row.get("away_team"):
                rows.append(row)
        log["parsed_rows"] = len(rows)
        log["participants_parsed"] = participants_total
        if len(items) == 0:
            log["status"] = "empty_data"
            log["message"] = "HTTP 성공, 하지만 data 0건: 날짜/플랜 범위/권한 확인 필요"
        elif rows:
            log["status"] = "ok"
            log["message"] = f"Sportmonks parsed {len(rows)} rows"
        else:
            log["status"] = "parse_zero"
            log["message"] = "data는 있으나 팀명/일정 파싱 0건: participants/include 구조 확인 필요"
        df = pd.DataFrame(rows)
        write_csv(OUTPUT_FILES["sportmonks_status"], pd.DataFrame([log]))
        return df, pd.DataFrame([log])
    except Exception as exc:
        log["status"] = "exception"
        log["message"] = str(exc)
        write_csv(OUTPUT_FILES["sportmonks_status"], pd.DataFrame([log]))
        log_error("fetch_sportmonks_fixtures", safe_url, str(exc))
        return pd.DataFrame(), pd.DataFrame([log])


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
        "option_a": clean(market.get("option_a")), "option_b": clean(market.get("option_b")), "option_c": clean(market.get("option_c")),
        "home_odds": clean(market.get("home_odds") or market.get("odds_home") or market.get("home_win_odds")),
        "draw_odds": clean(market.get("draw_odds") or market.get("odds_draw")),
        "away_odds": clean(market.get("away_odds") or market.get("odds_away") or market.get("away_win_odds")),
        "option_a_odds": clean(market.get("option_a_odds") or market.get("a_odds")),
        "option_b_odds": clean(market.get("option_b_odds") or market.get("b_odds")),
        "option_c_odds": clean(market.get("option_c_odds") or market.get("c_odds")),
        "handicap_home_odds": clean(market.get("handicap_home_odds") or market.get("home_handicap_odds")),
        "handicap_away_odds": clean(market.get("handicap_away_odds") or market.get("away_handicap_odds")),
        "under_odds": clean(market.get("under_odds") or market.get("odds_under")),
        "over_odds": clean(market.get("over_odds") or market.get("odds_over")),
        "source": clean(market.get("source")), "status": clean(market.get("status")),
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
    mobile_cols = [
        "created_at", "match_id", "match", "league", "date", "kickoff_kst", "home_team", "away_team",
        "market_type", "line_value", "option_a", "option_b", "option_c",
        "home_odds", "draw_odds", "away_odds", "option_a_odds", "option_b_odds", "option_c_odds",
        "handicap_home_odds", "handicap_away_odds", "under_odds", "over_odds",
        "source", "status", "pick", "confidence", "risk", "data_sufficiency", "missing_data", "reasons", "auto_buy", "auto_payment"
    ]
    mobile = analysis[[c for c in mobile_cols if c in analysis.columns]].copy() if not analysis.empty else pd.DataFrame()
    write_csv(OUTPUT_FILES["analysis_scores"], analysis)
    write_csv(OUTPUT_FILES["mobile_recommendations"], mobile)
    fixture_board = build_fixture_prediction_results(fixtures, analysis)
    explain, checklist = build_prediction_explain_tables(fixtures, analysis)
    diagnosis = build_diagnosis()
    meta = {"fixtures_msg": fmsg, "history_msg": hmsg, "analysis_rows": len(analysis), "mobile_rows": len(mobile), "fixture_board_rows": len(fixture_board), "prediction_explain_rows": len(explain), "offline_checklist_rows": len(checklist), "diagnosis": diagnosis, "missing_data_rows": len(read_csv(OUTPUT_FILES["missing_data_report"]))}
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
    return {"time": now_text(), "counts": counts, "missing": missing, "missing_summary": missing_summary, "hub_url": "ON" if get_hub_url() else "OFF", "google_sheet_url": "ON" if get_google_sheet_url() else "OFF", "sportmonks": sportmonks_secret_status()}


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
        "fixture_prediction_results": read_csv(OUTPUT_FILES["fixture_prediction_results"]).tail(500).to_dict("records"),
        "prediction_explain": read_csv(OUTPUT_FILES["prediction_explain"]).tail(500).to_dict("records"),
        "offline_checklist": read_csv(OUTPUT_FILES["offline_checklist"]).tail(500).to_dict("records"),
        "hub_send_logs": read_csv(OUTPUT_FILES["hub_send_logs"]).tail(50).to_dict("records"),
        "missing_data_report": read_csv(OUTPUT_FILES["missing_data_report"]).tail(300).to_dict("records"),
        "coach_status": read_csv(OUTPUT_FILES["coach_status"]).tail(300).to_dict("records"),
        "injury_status": read_csv(OUTPUT_FILES["injury_status"]).tail(300).to_dict("records"),
        "lineup_status": read_csv(OUTPUT_FILES["lineup_status"]).tail(300).to_dict("records"),
        "transfer_status": read_csv(OUTPUT_FILES["transfer_status"]).tail(300).to_dict("records"),
        "news_status": read_csv(OUTPUT_FILES["news_status"]).tail(300).to_dict("records"),
        "proto_market_status": read_csv(OUTPUT_FILES["proto_market_status"]).tail(300).to_dict("records"),
        "sportmonks_status": read_csv(OUTPUT_FILES["sportmonks_status"]).tail(100).to_dict("records"),
        "sportmonks_secret_status": sportmonks_secret_status(),
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
        # 1) Sportmonks는 느린 API라 USE_SLOW_API=Y 및 키가 있을 때만 호출. 실패해도 기존 일정표 수집은 계속 진행.
        sm_fx, sm_logs = fetch_sportmonks_fixtures()
        sm_new, sm_total = append_csv(SOURCE_FILES["source_sportmonks"], sm_fx, ["match_id"])
        if not sm_fx.empty:
            append_csv(SOURCE_FILES["source_livescore_fixtures"], sm_fx, ["match_id"])
        append_csv(OUTPUT_FILES["run_logs"], sm_logs.rename(columns={"status":"source_status"}) if not sm_logs.empty else pd.DataFrame())
        report.append(f"Sportmonks 수집: 신규 {sm_new}, 전체 {sm_total} · {clean(sm_logs.iloc[-1].get('message')) if not sm_logs.empty else '로그 없음'}")
        log_run("sportmonks_collect", "ok", report[-1])

        # 2) 기존 TheSportsDB 일정표 자동수집은 그대로 유지
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
    lines += ["", "## Sportmonks 상태"]
    sm_status = read_csv(OUTPUT_FILES["sportmonks_status"]).tail(20)
    if sm_status.empty:
        lines.append("Sportmonks 상태 로그 없음")
    else:
        lines.append(sm_status.to_csv(index=False))
    lines += ["", "## 분석보기/오프라인 체크표"]
    exp = read_csv(OUTPUT_FILES["prediction_explain"]).tail(30)
    if exp.empty:
        lines.append("분석보기 자료 없음")
    else:
        lines.append(exp.to_csv(index=False))
    chk = read_csv(OUTPUT_FILES["offline_checklist"]).tail(30)
    if chk.empty:
        lines.append("오프라인 체크표 없음")
    else:
        lines.append(chk.to_csv(index=False))
    lines += ["", "## 라이브스코어식 전체 경기 예상/결과"]
    board = read_csv(OUTPUT_FILES["fixture_prediction_results"]).tail(30)
    if board.empty:
        lines.append("전체 경기 예상/결과표 없음")
    else:
        lines.append(board.to_csv(index=False))
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
    details = {"fixtures":len(fixtures),"history":len(history),"team_form":len(tf),"home_away":len(ha),"h2h":len(hh),"markets":len(markets),"analysis":len(analysis),"payload_mobile":len(payload["mobile_recommendations"]),"sportmonks_function":"present"}
    return ok, "가상 백엔드 전체 테스트 통과" if ok else "가상 백엔드 테스트 실패", details



# =========================
# v14 화면 정리 / 모바일 추천 헬퍼
# =========================
KOR_COLUMNS = {
    "created_at": "생성시간", "match_id": "경기ID", "match": "경기", "league": "리그", "date": "경기일",
    "kickoff_kst": "시간", "market_type": "승부식", "line_value": "기준점", "pick": "추천",
    "confidence": "신뢰도", "risk": "위험도", "data_sufficiency": "자료충분도", "missing_data": "부족자료",
    "reasons": "추천근거", "auto_buy": "자동구매", "auto_payment": "자동결제",
    "home_team": "홈팀", "away_team": "원정팀", "sport": "종목", "status": "상태", "source": "자료출처",
}

MARKET_ORDER = ["승무패", "핸디캡", "언더오버", "전반", "더블찬스", "SUM", "승패/승5패", "한경기조합", "한경기구매", "기타"]


def ko_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    cols = [c for c in ["date", "kickoff_kst", "league", "match", "market_type", "line_value", "pick", "confidence", "risk", "data_sufficiency", "missing_data", "reasons", "auto_buy", "auto_payment"] if c in out.columns]
    if cols:
        out = out[cols]
    return out.rename(columns={c: KOR_COLUMNS.get(c, c) for c in out.columns})


def num_value(v, default=0) -> int:
    try:
        return int(float(clean(v)))
    except Exception:
        return default


def recommendation_grade(row: Dict[str, Any]) -> str:
    pick = clean(row.get("pick"))
    risk = clean(row.get("risk"))
    conf = num_value(row.get("confidence"), 0)
    suff = num_value(row.get("data_sufficiency"), 0)
    if pick in {"", "분석불가"}:
        return "제외"
    if "자료확인" in pick:
        return "C-자료확인"
    # 실제 프로토/부상/라인업이 없으면 강추천 대신 참고용으로 묶는다.
    if conf >= 75 and risk == "낮음":
        return "A-참고용"
    if conf >= 65 and risk in {"낮음", "중간"}:
        return "B-참고용"
    if suff < 50:
        return "C-자료부족"
    return "C-주의"


def sort_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy().fillna("")
    out["_confidence"] = out.get("confidence", "0").apply(lambda x: num_value(x, 0))
    out["_sufficiency"] = out.get("data_sufficiency", "0").apply(lambda x: num_value(x, 0))
    out["_risk_rank"] = out.get("risk", "").map({"낮음": 0, "중간": 1, "높음": 2}).fillna(3)
    out["_pick_rank"] = out.get("pick", "").apply(lambda x: 9 if clean(x) in {"분석불가", "자료확인 필요", ""} else 0)
    out["_market_rank"] = out.get("market_type", "").apply(lambda x: MARKET_ORDER.index(x) if x in MARKET_ORDER else 99)
    out = out.sort_values(["date", "_pick_rank", "_risk_rank", "_confidence", "_sufficiency", "_market_rank"], ascending=[True, True, True, False, False, True])
    return out.drop(columns=[c for c in out.columns if c.startswith("_")], errors="ignore")


def best_proto_candidates(df: pd.DataFrame, limit: int = 12) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = sort_recommendations(df)
    if out.empty:
        return out
    out = out[~out.get("pick", "").isin(["분석불가", "자료확인 필요", ""])]
    out = out[out.get("risk", "") != "높음"]
    out["grade"] = out.apply(lambda r: recommendation_grade(r.to_dict()), axis=1)
    return out.head(limit)


def market_summary_for_match(match_df: pd.DataFrame) -> List[Dict[str, str]]:
    rows = []
    if match_df is None or match_df.empty:
        return rows
    for market in MARKET_ORDER:
        part = match_df[match_df.get("market_type", "") == market]
        if part.empty:
            continue
        r = part.iloc[0]
        rows.append({
            "승부식": clean(r.get("market_type")),
            "기준점/핸디": clean(r.get("line_value")) or "-",
            "추천": clean(r.get("pick")) or "-",
            "신뢰도": clean(r.get("confidence")) or "0",
            "위험도": clean(r.get("risk")) or "-",
            "등급": recommendation_grade(r.to_dict()),
        })
    return rows




def actual_result_text(row: Dict[str, Any]) -> str:
    hs = clean(row.get("home_score"))
    aw = clean(row.get("away_score"))
    if hs == "" or aw == "":
        return "예정"
    try:
        h = int(float(hs)); a = int(float(aw))
    except Exception:
        return "결과확인"
    if h > a:
        return "홈승"
    if h < a:
        return "원정승"
    return "무승부"


def normalize_match_key(row: Dict[str, Any]) -> str:
    mid = clean(row.get("match_id"))
    if mid:
        return mid
    return f"{normalize_date(row.get('date'))}_{clean(row.get('home_team'))}_{clean(row.get('away_team'))}".replace(" ", "_")


def pick_market_row(match_df: pd.DataFrame, market: str) -> Dict[str, Any]:
    if match_df is None or match_df.empty or "market_type" not in match_df.columns:
        return {}
    part = match_df[match_df["market_type"].astype(str) == market].copy()
    if part.empty:
        return {}
    # 분석불가보다는 실제 후보/자료확인 순으로 하나만 고른다.
    # 일부 테스트/외부 원본에는 date 컬럼이 없을 수 있어 정렬 필드를 보강한다.
    for c in ["date", "kickoff_kst", "data_sufficiency", "confidence", "risk", "pick"]:
        if c not in part.columns:
            part[c] = ""
    part = sort_recommendations(part)
    return part.iloc[0].to_dict()


def best_match_candidate(match_df: pd.DataFrame) -> Dict[str, Any]:
    if match_df is None or match_df.empty:
        return {}
    cand = best_proto_candidates(match_df, 1)
    if not cand.empty:
        return cand.iloc[0].to_dict()
    # 후보가 하나도 없으면 1X2 또는 첫 줄을 표시한다.
    r = pick_market_row(match_df, "승무패")
    if r:
        return r
    return match_df.iloc[0].to_dict()


def build_fixture_prediction_results(fixtures: pd.DataFrame = None, analysis: pd.DataFrame = None) -> pd.DataFrame:
    """라이브스코어식 전체 경기판: 매일 전체 경기의 예상과 실제 결과를 한 줄로 만든다."""
    if fixtures is None:
        src = read_csv(SOURCE_FILES["source_livescore_fixtures"])
        std = read_csv(STANDARD_FILES["standard_upcoming_fixtures"])
        fixtures = pd.concat([src, std], ignore_index=True) if not src.empty or not std.empty else pd.DataFrame()
    if analysis is None:
        analysis = read_csv(OUTPUT_FILES["analysis_scores"])
    if fixtures is None or fixtures.empty:
        write_csv(OUTPUT_FILES["fixture_prediction_results"], pd.DataFrame())
        return pd.DataFrame()

    fixtures = fixtures.copy().fillna("")
    # 필요한 필드가 없는 소스도 안전하게 보정
    for c in ["match_id", "date", "kickoff_kst", "league", "home_team", "away_team", "status", "home_score", "away_score", "source"]:
        if c not in fixtures.columns:
            fixtures[c] = ""
    fixtures["match_id"] = fixtures.apply(lambda r: normalize_match_key(r.to_dict()), axis=1)
    fixtures["date"] = fixtures["date"].apply(normalize_date)
    fixtures = fixtures[(fixtures["date"].astype(str) != "") & (fixtures["home_team"].astype(str) != "") & (fixtures["away_team"].astype(str) != "")]
    if fixtures.empty:
        write_csv(OUTPUT_FILES["fixture_prediction_results"], pd.DataFrame())
        return pd.DataFrame()
    fixtures = fixtures.drop_duplicates(subset=["match_id"], keep="last")
    rows = []
    analysis = analysis.copy().fillna("") if analysis is not None and not analysis.empty else pd.DataFrame()
    for _, f in fixtures.sort_values(["date", "kickoff_kst", "league", "home_team"]).iterrows():
        fd = f.to_dict()
        mid = clean(fd.get("match_id"))
        mdf = analysis[analysis.get("match_id", pd.Series(dtype=str)).astype(str) == mid] if not analysis.empty and "match_id" in analysis.columns else pd.DataFrame()
        one = pick_market_row(mdf, "승무패")
        hcap = pick_market_row(mdf, "핸디캡")
        uo = pick_market_row(mdf, "언더오버")
        dc = pick_market_row(mdf, "더블찬스")
        main = best_match_candidate(mdf)
        real_any = False
        if not mdf.empty:
            real_any = any(is_real_proto_row(r.to_dict()) for _, r in mdf.iterrows())
        rows.append({
            "created_at": now_text(),
            "match_id": mid,
            "date": normalize_date(fd.get("date")),
            "kickoff_kst": clean(fd.get("kickoff_kst")),
            "league": clean(fd.get("league")),
            "home_team": clean(fd.get("home_team")),
            "away_team": clean(fd.get("away_team")),
            "match": f"{clean(fd.get('home_team'))} vs {clean(fd.get('away_team'))}",
            "match_status": clean(fd.get("status")) or ("FT" if clean(fd.get("home_score")) or clean(fd.get("away_score")) else "SCHEDULED"),
            "home_score": clean(fd.get("home_score")),
            "away_score": clean(fd.get("away_score")),
            "actual_result": actual_result_text(fd),
            "pred_1x2": compact_pick_text(one) if one else "분석대기",
            "pred_1x2_conf": clean(one.get("confidence")) if one else "0",
            "pred_1x2_risk": clean(one.get("risk")) if one else "-",
            "pred_handicap": compact_pick_text(hcap) if hcap else "-",
            "pred_overunder": compact_pick_text(uo) if uo else "-",
            "pred_doublechance": compact_pick_text(dc) if dc else "-",
            "main_candidate": compact_pick_text(main) if main else "분석대기",
            "main_confidence": clean(main.get("confidence")) if main else "0",
            "main_risk": clean(main.get("risk")) if main else "-",
            "proto_status": "실제배당" if real_any else "배당미연동",
            "missing_data": clean(main.get("missing_data")) if main else "분석자료 없음",
        })
    out = pd.DataFrame(rows)
    write_csv(OUTPUT_FILES["fixture_prediction_results"], out)
    return out

def compact_status_text(diag: Dict[str, Any]) -> str:
    counts = diag.get("counts", {}) if isinstance(diag, dict) else {}
    return (
        f"추천 {counts.get('mobile_recommendations',0)}건 · "
        f"분석 {counts.get('analysis_scores',0)}건 · "
        f"허브 {diag.get('hub_url','OFF')} · "
        f"시트 {diag.get('google_sheet_url','OFF')} · "
        f"오류 {counts.get('error_logs',0)}건"
    )


# =========================
# v15 Galaxy S26 Ultra compact mobile card helpers
# =========================
KOR_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def date_label_kr(date_text: str) -> str:
    d = clean(date_text)
    try:
        dt = datetime.strptime(d[:10], "%Y-%m-%d")
        return dt.strftime("%m/%d") + f" {KOR_WEEKDAYS[dt.weekday()]}"
    except Exception:
        return d


def first_value(row: Dict[str, Any], keys: List[str]) -> str:
    for k in keys:
        v = clean(row.get(k))
        if v:
            return v
    return ""


def odds_or_dash(row: Dict[str, Any], keys: List[str]) -> str:
    return first_value(row, keys) or "-"


def is_real_proto_row(row: Dict[str, Any]) -> bool:
    src = clean(row.get("source"))
    status = clean(row.get("status"))
    joined = f"{src} {status}".lower()
    return bool(joined) and not any(x in joined for x in ["template", "not_real", "market_template"])


def short_market_code(market: str, line: str) -> str:
    m = clean(market)
    lv = clean(line)
    if m == "승무패":
        return "1X2"
    if m == "핸디캡":
        return f"H{lv}" if lv else "H"
    if m == "언더오버":
        return f"U/O{lv}" if lv else "U/O"
    if m == "더블찬스":
        return "DC"
    if m == "전반":
        return "전반"
    if m == "SUM":
        return "SUM"
    if m == "승패/승5패":
        return "승5패"
    if m == "한경기조합":
        return "조합"
    if m == "한경기구매":
        return "단일"
    return m[:6] if m else "-"


def compact_pick_text(row: Dict[str, Any]) -> str:
    pick = clean(row.get("pick")) or "-"
    pick = pick.replace(" 우세", "").replace(" 안정", "").replace("자료확인 필요", "확인")
    pick = pick.replace("홈 핸디", "홈H").replace("원정 핸디", "원정H")
    pick = pick.replace("홈/무", "홈무").replace("무/원정", "무원")
    conf = clean(row.get("confidence")) or "0"
    risk = clean(row.get("risk")) or "-"
    risk_short = {"낮음":"낮", "중간":"중", "높음":"높"}.get(risk, risk)
    return f"{pick} {conf} {risk_short}"


def compact_odds_text(row: Dict[str, Any]) -> str:
    m = clean(row.get("market_type"))
    if m == "승무패":
        h = odds_or_dash(row, ["home_odds", "option_a_odds", "odds_home", "home_win_odds"])
        d = odds_or_dash(row, ["draw_odds", "option_b_odds", "odds_draw"])
        a = odds_or_dash(row, ["away_odds", "option_c_odds", "odds_away", "away_win_odds"])
        return f"{h} / {d} / {a}"
    if m == "핸디캡":
        h = odds_or_dash(row, ["handicap_home_odds", "home_handicap_odds", "option_a_odds"])
        a = odds_or_dash(row, ["handicap_away_odds", "away_handicap_odds", "option_b_odds"])
        return f"{h} / {a}"
    if m == "언더오버":
        u = odds_or_dash(row, ["under_odds", "odds_under", "option_a_odds"])
        o = odds_or_dash(row, ["over_odds", "odds_over", "option_b_odds"])
        return f"U {u} / O {o}"
    a = odds_or_dash(row, ["option_a_odds", "home_odds"])
    b = odds_or_dash(row, ["option_b_odds", "draw_odds"])
    c = odds_or_dash(row, ["option_c_odds", "away_odds"])
    vals = [x for x in [a,b,c] if x and x != "-"]
    return " / ".join(vals) if vals else "-"


def compact_market_line(row: Dict[str, Any]) -> str:
    code = short_market_code(row.get("market_type"), row.get("line_value"))
    odds = compact_odds_text(row)
    if odds.replace(" ", "") in {"-", "-/-", "-/-/-", "U-/O-"}:
        odds = "배당미연동"
    pick = compact_pick_text(row)
    grade = recommendation_grade(row)
    grade = grade.replace("-참고용", "").replace("C-", "")
    return f"<div class='mline'><span class='mcode'>{html_escape(code)}</span><span class='odds'>{html_escape(odds)}</span><span class='arrow'>→</span><span class='pick'>{html_escape(pick)}</span><span class='grade'>{html_escape(grade)}</span></div>"


def html_escape(v: Any) -> str:
    return str(clean(v)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def split_match_teams(row: Dict[str, Any]) -> Tuple[str, str]:
    home = clean(row.get("home_team"))
    away = clean(row.get("away_team"))
    if home or away:
        return home or "홈", away or "원정"
    match = clean(row.get("match"))
    if " vs " in match:
        a,b = match.split(" vs ", 1)
        return a.strip(), b.strip()
    return match or "홈", "원정"




# =========================
# v17 한글 팀명 / 분석보기 / 오프라인 체크표
# =========================
TEAM_KO_MAP = {
    "Udinese": "우디네세", "Como": "코모", "Angers": "앙제", "Lille": "릴",
    "Bayern Munich": "바이에른 뮌헨", "Bayern": "바이에른 뮌헨", "Stuttgart": "슈투트가르트",
    "Barcelona": "바르셀로나", "Athletic Bilbao": "빌바오", "Arsenal": "아스널",
    "Coventry City": "코벤트리", "Wolverhampton Wanderers": "울버햄튼", "Blackburn Rovers": "블랙번",
    "Blackburn Rover": "블랙번", "Chelsea": "첼시", "Manchester United": "맨체스터 유나이티드",
    "Manchester City": "맨체스터 시티", "Liverpool": "리버풀", "Tottenham Hotspur": "토트넘",
    "Real Madrid": "레알 마드리드", "Atletico Madrid": "아틀레티코 마드리드",
    "Inter Milan": "인터 밀란", "AC Milan": "AC 밀란", "Juventus": "유벤투스",
    "Paris Saint-Germain": "파리 생제르맹", "PSG": "파리 생제르맹",
}

LEAGUE_KO_MAP = {
    "Italian Serie A": "세리에 A", "French Ligue 1": "리그 1", "German Bundesliga": "분데스리가",
    "Spanish La Liga": "라리가", "English Premier League": "프리미어리그",
    "English Championship": "챔피언십", "English League Championship": "챔피언십",
}


def ko_team(name: Any) -> str:
    text = clean(name)
    return TEAM_KO_MAP.get(text, text)


def ko_league(name: Any) -> str:
    text = clean(name)
    return LEAGUE_KO_MAP.get(text, text)


def safe_key(*parts: Any) -> str:
    raw = "_".join(clean(p) for p in parts)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]
    return digest


def split_reasons(reasons: str) -> Dict[str, str]:
    chunks = [x.strip() for x in clean(reasons).split("/") if x.strip()]
    out = {"recent_form": "자료 없음", "home_away_form": "자료 없음", "h2h": "자료 없음"}
    recent = [x for x in chunks if x.startswith("홈 최근") or x.startswith("원정 최근")]
    homeaway = [x for x in chunks if "홈성적" in x or "원정성적" in x]
    h2h = [x for x in chunks if "상대전적" in x]
    if recent:
        out["recent_form"] = " / ".join(recent)
    if homeaway:
        out["home_away_form"] = " / ".join(homeaway)
    if h2h:
        out["h2h"] = " / ".join(h2h)
    return out


def why_summary_from_row(row: Dict[str, Any]) -> str:
    pick = clean(row.get("pick")) or "자료확인"
    reasons = split_reasons(clean(row.get("reasons")))
    bits = []
    rf = reasons.get("recent_form", "")
    ha = reasons.get("home_away_form", "")
    h2h = reasons.get("h2h", "")
    if rf and rf != "자료 없음":
        bits.append("최근폼 반영")
    if ha and ha != "자료 없음":
        bits.append("홈/원정 흐름 반영")
    if h2h and h2h != "자료 없음":
        bits.append("상대전적 반영")
    if not bits:
        bits.append("자료 부족으로 참고용")
    return f"{pick}: " + " · ".join(bits)


def build_prediction_explain_tables(fixtures: pd.DataFrame = None, analysis: pd.DataFrame = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if fixtures is None:
        fixtures = read_csv(STANDARD_FILES["standard_upcoming_fixtures"])
    if analysis is None:
        analysis = read_csv(OUTPUT_FILES["analysis_scores"])
    if fixtures is None or fixtures.empty:
        write_csv(OUTPUT_FILES["prediction_explain"], pd.DataFrame())
        write_csv(OUTPUT_FILES["offline_checklist"], pd.DataFrame())
        return pd.DataFrame(), pd.DataFrame()
    fixtures = fixtures.copy().fillna("")
    if analysis is None:
        analysis = pd.DataFrame()
    analysis = analysis.copy().fillna("") if not analysis.empty else pd.DataFrame()
    exp_rows, chk_rows = [], []
    for _, f in fixtures.iterrows():
        fd = f.to_dict()
        mid = normalize_match_key(fd)
        mdf = analysis[analysis.get("match_id", pd.Series(dtype=str)).astype(str) == mid] if not analysis.empty and "match_id" in analysis.columns else pd.DataFrame()
        main = best_match_candidate(mdf)
        one = pick_market_row(mdf, "승무패")
        hcap = pick_market_row(mdf, "핸디캡")
        uo = pick_market_row(mdf, "언더오버")
        reasons = split_reasons(clean(main.get("reasons"))) if main else {"recent_form":"자료 없음","home_away_form":"자료 없음","h2h":"자료 없음"}
        home_ko, away_ko = ko_team(fd.get("home_team")), ko_team(fd.get("away_team"))
        main_pred = compact_pick_text(main) if main else "분석대기"
        final_note = "자동구매/자동결제 없음 · 오프라인에서 직접 확인 후 수동 체크"
        exp_rows.append({
            "created_at": now_text(), "match_id": mid, "date": normalize_date(fd.get("date")), "kickoff_kst": clean(fd.get("kickoff_kst")),
            "league": ko_league(fd.get("league")), "home_team": clean(fd.get("home_team")), "away_team": clean(fd.get("away_team")),
            "home_team_ko": home_ko, "away_team_ko": away_ko, "main_prediction": main_pred,
            "confidence": clean(main.get("confidence")) if main else "0", "risk": clean(main.get("risk")) if main else "-",
            "recent_form": reasons.get("recent_form", "자료 없음"), "home_away_form": reasons.get("home_away_form", "자료 없음"),
            "h2h": reasons.get("h2h", "자료 없음"), "why_summary": why_summary_from_row(main) if main else "분석자료 부족",
            "missing_data": clean(main.get("missing_data")) if main else "분석자료 없음", "final_note": final_note,
        })
        chk_rows.append({
            "created_at": now_text(), "match_id": mid, "date": normalize_date(fd.get("date")), "kickoff_kst": clean(fd.get("kickoff_kst")),
            "league": ko_league(fd.get("league")), "home_team_ko": home_ko, "away_team_ko": away_ko, "main_prediction": main_pred,
            "check_match": f"경기명 확인: {home_ko} vs {away_ko}",
            "check_time": f"시간 확인: {clean(fd.get('kickoff_kst')) or '-'}",
            "check_1x2": f"승무패 확인: {compact_pick_text(one) if one else '분석대기'}",
            "check_handicap": f"핸디캡 확인: {compact_pick_text(hcap) if hcap else '분석대기'}",
            "check_overunder": f"언더/오버 확인: {compact_pick_text(uo) if uo else '분석대기'}",
            "check_odds_change": "현장/공식 화면 배당 변동 확인",
            "check_livescore": "라이브스코어 상태 확인",
            "check_manual_marking": "오프라인에서 직접 마킹 완료 확인",
            "auto_buy": "NO", "auto_payment": "NO",
        })
    exp = pd.DataFrame(exp_rows)
    chk = pd.DataFrame(chk_rows)
    write_csv(OUTPUT_FILES["prediction_explain"], exp)
    write_csv(OUTPUT_FILES["offline_checklist"], chk)
    return exp, chk


def render_match_detail_expander(match_df: pd.DataFrame, context: str, match_label: str = ""):
    if match_df is None or match_df.empty:
        return
    first = match_df.iloc[0].to_dict()
    mid = clean(first.get("match_id")) or safe_key(context, match_label, clean(first.get("match")))
    main = best_match_candidate(match_df)
    reasons = split_reasons(clean(main.get("reasons"))) if main else {}
    home, away = split_match_teams(first)
    home_ko, away_ko = ko_team(home), ko_team(away)
    title = f"🔍 분석보기 / 오프라인 체크표 — {home_ko} vs {away_ko}"
    with st.expander(title, expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("AI 예상", clean(main.get("pick")) or "분석대기")
        c2.metric("신뢰도", clean(main.get("confidence")) or "0")
        c3.metric("위험도", clean(main.get("risk")) or "-")
        st.markdown("**왜 이렇게 예상했나**")
        st.write(why_summary_from_row(main) if main else "분석자료가 부족합니다.")
        st.markdown("**근거**")
        st.write(f"- 최근폼: {reasons.get('recent_form', '자료 없음')}")
        st.write(f"- 홈/원정: {reasons.get('home_away_form', '자료 없음')}")
        st.write(f"- 상대전적: {reasons.get('h2h', '자료 없음')}")
        st.write(f"- 부족자료: {clean(main.get('missing_data')) or '없음'}")
        st.caption("자동구매/자동결제 없음 · 오프라인 판매점에서 직접 확인 후 수동 체크")
        st.markdown("**오프라인 수동 구매 체크표**")
        checks = [
            f"경기명 확인: {home_ko} vs {away_ko}",
            f"시간 확인: {clean(first.get('kickoff_kst')) or '-'}",
            "승무패 번호/배당 확인",
            "핸디캡 기준점 확인",
            "언더/오버 기준점 확인",
            "배당 변동 확인",
            "라이브스코어 상태 확인",
            "내가 직접 마킹 완료",
        ]
        for idx, item in enumerate(checks):
            st.checkbox(item, key=f"chk_{context}_{safe_key(mid, idx, item)}")
        detail = match_df.copy()
        detail["등급"] = detail.apply(lambda r: recommendation_grade(r.to_dict()), axis=1)
        cols = [c for c in ["market_type","line_value","pick","confidence","risk","data_sufficiency","등급","reasons","missing_data"] if c in detail.columns]
        if cols:
            st.dataframe(detail[cols].rename(columns={**KOR_COLUMNS, "등급":"등급"}), width="stretch", hide_index=True)

def mobile_card_css():
    st.markdown("""
<style>
.block-container {padding-top: 1.0rem; padding-left: 0.75rem; padding-right: 0.75rem;}
.maru-mobile-wrap {max-width: 520px; margin: 0 auto;}
.date-head {font-weight: 900; font-size: 1.15rem; margin: 1.1rem 0 .45rem 0; padding: .55rem .75rem; border-radius: 14px; background: #f1f3f5;}
.league-head {font-weight: 800; font-size: .92rem; color: #415a77; margin: .55rem 0 .25rem 0;}
.proto-card {border: 1px solid #d8dee4; border-radius: 16px; padding: 10px 10px 8px 10px; margin: 8px 0; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.05);}
.proto-top {display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom: 6px;}
.proto-time {font-size: .86rem; font-weight:800; color:#495057; white-space:nowrap;}
.proto-badge {font-size:.72rem; border-radius: 999px; padding: 3px 8px; background:#eef2ff; color:#364fc7; font-weight:800; white-space:nowrap;}
.teams {display:flex; align-items:center; justify-content:space-between; gap: 6px; font-size: 1.05rem; font-weight: 900; margin: 6px 0 8px 0;}
.team {width:43%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.team.away {text-align:right;}
.vs {font-size:.8rem; color:#868e96; width:14%; text-align:center; font-weight:800;}
.mline {display:grid; grid-template-columns: 56px minmax(94px,1fr) 16px minmax(76px,1fr) 48px; gap: 4px; align-items:center; font-size:.86rem; border-top:1px solid #eef0f2; padding: 5px 0; line-height:1.15;}
.mcode {font-weight:900; color:#0b7285; white-space:nowrap;}
.odds {font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color:#212529; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.arrow {color:#adb5bd; text-align:center;}
.pick {font-weight:900; color:#c92a2a; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.grade {font-size:.72rem; color:#495057; text-align:right; white-space:nowrap;}
.notice {font-size:.75rem; color:#868e96; margin-top:4px;}
@media (max-width: 430px) {
  .block-container {padding-left:.45rem; padding-right:.45rem;}
  .teams {font-size:.98rem;}
  .mline {grid-template-columns: 50px minmax(70px,1fr) 12px minmax(64px,1fr) 36px; font-size:.78rem; gap:3px;}
  .proto-card {padding: 9px 8px 7px 8px; border-radius:14px;}
  .proto-badge {font-size:.66rem; padding:2px 6px;}
  .grade {font-size:.66rem;}
}
</style>
""", unsafe_allow_html=True)

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
    diag = build_diagnosis()
    counts = diag.get("counts", {})
    st.markdown("### 🖥️ PC 모니터링 대시보드")
    st.caption("복잡한 영어 로그는 숨기고, 지금 필요한 상태만 크게 보여줍니다.")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("앱 상태", "정상" if counts.get("error_logs",0) == 0 else "오류")
    c2.metric("허브", diag.get("hub_url", "OFF"))
    c3.metric("구글시트", diag.get("google_sheet_url", "OFF"))
    c4.metric("추천", counts.get("mobile_recommendations", 0))
    c5.metric("분석", counts.get("analysis_scores", 0))
    c6.metric("부족자료", counts.get("missing_data_report", 0))

    sm = read_csv(OUTPUT_FILES["sportmonks_status"])
    if not sm.empty:
        last = sm.tail(1).iloc[0].to_dict()
        st.info(f"Sportmonks: 키 {'ON' if str(last.get('token_detected')).lower() in {'true','1','y','yes'} else 'OFF'} · HTTP {clean(last.get('http_status')) or '-'} · 상태 {clean(last.get('status')) or '-'} · 수집 {clean(last.get('parsed_rows')) or '0'}건")
    else:
        sm_status = sportmonks_secret_status()
        st.info(f"Sportmonks: 키 {'ON' if sm_status.get('token_detected') else 'OFF'} · 느린API {sm_status.get('enabled')} · 아직 진단로그 없음")

def render_full_run():
    st.subheader("🚀 전체 실행")
    st.caption("버튼은 단순하게, 상세 로그는 접어둡니다. 최종 목적은 프로토 승부식 후보를 날짜별로 정리하는 것입니다.")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🚀 전체 실행 + 허브 전송", type="primary", use_container_width=True):
            with st.spinner("수집 → 분석 → 모바일 추천 → 허브/구글시트 전송 중..."):
                report = run_full_pipeline(True, True, True)
            st.success("전체 실행 완료")
            with st.expander("실행 상세 보기", expanded=False):
                for line in report:
                    st.write(line)
            render_download_bar("full_after")
    with c2:
        if st.button("📱 모바일 추천 보기", use_container_width=True):
            st.session_state["jump_mobile_notice"] = True
            st.info("위 탭에서 '모바일 추천'을 누르면 날짜별 카드로 볼 수 있습니다.")
    with c3:
        if st.button("📊 구글시트 열기", use_container_width=True):
            url = get_google_sheet_url()
            if url:
                st.link_button("구글시트 허브 바로가기", url)
            else:
                st.warning("GOOGLE_SHEET_URL이 없습니다.")
    with c4:
        if st.button("🧪 고급 진단", use_container_width=True):
            st.session_state["show_advanced_on_home"] = True
    st.divider()
    render_clean_dashboard()
    if st.session_state.get("show_advanced_on_home"):
        with st.expander("고급 진단/원문 로그", expanded=True):
            render_recent_outputs()

def render_clean_dashboard():
    diag = build_diagnosis()
    counts = diag.get("counts", {})
    st.markdown("### ✅ 오늘 한눈에 보기")
    st.success(compact_status_text(diag))

    rec = read_csv(OUTPUT_FILES["mobile_recommendations"])
    best = best_proto_candidates(rec, 8)
    if best.empty:
        st.warning("아직 보여줄 추천 후보가 없습니다. 전체 실행을 먼저 누르세요.")
    else:
        st.markdown("#### 🎯 프로토 승부식 우선 후보")
        show = best.copy()
        show["등급"] = show.apply(lambda r: recommendation_grade(r.to_dict()), axis=1)
        cols = [c for c in ["date","kickoff_kst","league","match","market_type","line_value","pick","confidence","risk","data_sufficiency","등급"] if c in show.columns]
        st.dataframe(show[cols].rename(columns={**KOR_COLUMNS, "등급":"등급"}), width="stretch", hide_index=True)

    with st.expander("숨김: 자료 수집/저장 건수", expanded=False):
        status_rows = [
            {"항목":"일정표", "건수":counts.get("source_livescore_fixtures",0)},
            {"항목":"과거자료", "건수":counts.get("source_football_data",0)},
            {"항목":"Sportmonks", "건수":counts.get("source_sportmonks",0)},
            {"항목":"실제 프로토 기준점/배당", "건수":counts.get("source_proto_markets",0)},
            {"항목":"감독/전술", "건수":counts.get("standard_coaches",0)},
            {"항목":"부상/결장", "건수":counts.get("standard_injuries",0)},
            {"항목":"예상 라인업", "건수":counts.get("standard_lineups",0)},
            {"항목":"뉴스/공지", "건수":counts.get("standard_news_flags",0)},
        ]
        st.dataframe(pd.DataFrame(status_rows), width="stretch", hide_index=True)

    miss = read_csv(OUTPUT_FILES["missing_data_report"])
    if not miss.empty:
        with st.expander("숨김: 부족자료 상세", expanded=False):
            st.dataframe(ko_df(miss.tail(100)), width="stretch", hide_index=True)

def render_recent_outputs():
    st.subheader("🔎 고급 원문 확인")
    st.caption("평소에는 접어두고, 오류 찾을 때만 열어봅니다.")
    with st.expander("모바일 추천 원문", expanded=False):
        df = read_csv(OUTPUT_FILES["mobile_recommendations"])
        st.dataframe(ko_df(df.tail(150)), width="stretch", hide_index=True) if not df.empty else st.info("모바일 추천 없음")
    with st.expander("분석 점수 원문", expanded=False):
        df = read_csv(OUTPUT_FILES["analysis_scores"])
        st.dataframe(ko_df(df.tail(150)), width="stretch", hide_index=True) if not df.empty else st.info("분석 점수 없음")
    with st.expander("허브 전송 로그", expanded=False):
        df = read_csv(OUTPUT_FILES["hub_send_logs"])
        st.dataframe(df.tail(100), width="stretch", hide_index=True) if not df.empty else st.info("허브 로그 없음")
    with st.expander("부족자료 진단표", expanded=False):
        miss = read_csv(OUTPUT_FILES["missing_data_report"])
        st.dataframe(ko_df(miss.tail(100)), width="stretch", hide_index=True) if not miss.empty else st.info("부족자료 진단표 없음")

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
    st.markdown("#### Sportmonks 상태")
    st.json(sportmonks_secret_status())
    st.dataframe(read_csv(OUTPUT_FILES["sportmonks_status"]).tail(100), width="stretch")

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
    with st.expander("Sportmonks API 진단", expanded=True):
        st.json(sportmonks_secret_status())
        if st.button("🐒 Sportmonks API 단독 테스트"):
            sm_fx, sm_logs = fetch_sportmonks_fixtures()
            n,total = append_csv(SOURCE_FILES["source_sportmonks"], sm_fx, ["match_id"])
            if not sm_fx.empty:
                append_csv(SOURCE_FILES["source_livescore_fixtures"], sm_fx, ["match_id"])
            st.success(f"Sportmonks 저장: 신규 {n}, 전체 {total}") if not sm_fx.empty else st.warning("Sportmonks 저장 0건 - 아래 상태 로그를 확인하세요")
            st.dataframe(sm_logs, width="stretch")
        st.dataframe(read_csv(OUTPUT_FILES["sportmonks_status"]).tail(200), width="stretch")
    with st.expander("최근 오류 로그", expanded=False):
        st.dataframe(read_csv(OUTPUT_FILES["error_logs"]).tail(200), width="stretch")




def livescore_board_css():
    st.markdown("""
<style>
.live-wrap {max-width: 760px; margin: 0 auto;}
.live-date {font-weight:900; font-size:1.25rem; margin:1rem 0 .55rem 0; padding:.55rem .75rem; border-radius:14px; background:#f1f3f5;}
.live-league {font-weight:850; font-size:.96rem; color:#334e68; margin:.65rem 0 .25rem 0;}
.live-card {border:1px solid #d8dee4; border-radius:16px; background:#fff; padding:10px 12px; margin:8px 0; box-shadow:0 1px 4px rgba(0,0,0,.05);}
.live-top {display:flex; align-items:center; justify-content:space-between; gap:8px; font-size:.82rem; color:#495057; font-weight:800;}
.live-teams {display:grid; grid-template-columns:1fr 70px 1fr; gap:8px; align-items:center; font-weight:950; font-size:1.05rem; margin:7px 0;}
.live-home {overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.live-away {overflow:hidden; text-overflow:ellipsis; white-space:nowrap; text-align:right;}
.live-score {text-align:center; font-weight:950; color:#0b7285;}
.live-result {display:grid; grid-template-columns:80px 1fr; gap:5px; font-size:.84rem; border-top:1px solid #eef0f2; padding-top:6px; margin-top:6px;}
.live-label {font-weight:900; color:#0b7285;}
.live-value {font-weight:800; color:#212529; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.live-sub {font-size:.74rem; color:#868e96; margin-top:5px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.live-pill {border-radius:999px; padding:3px 8px; font-weight:900; background:#eef2ff; color:#364fc7; white-space:nowrap;}
@media(max-width:430px){.live-wrap{max-width:100%;}.live-card{padding:9px 9px}.live-teams{grid-template-columns:1fr 56px 1fr; font-size:.96rem}.live-result{grid-template-columns:66px 1fr; font-size:.78rem}.live-pill{font-size:.72rem;padding:2px 6px}}
</style>
""", unsafe_allow_html=True)


def render_livescore_board_tab():
    st.subheader("📅 전체 경기 예상/결과 — 라이브스코어식")
    st.caption("매일 전체 경기마다 양팀, 예정/결과, AI 예상, 핸디/오버를 한 화면에서 확인합니다. 추천만 뽑는 화면이 아니라 전체 일정판입니다.")
    livescore_board_css()
    board = read_csv(OUTPUT_FILES["fixture_prediction_results"])
    analysis_all = read_csv(OUTPUT_FILES["analysis_scores"])
    if board.empty:
        # 예전 데이터가 있을 수 있으니 즉시 재생성 시도
        board = build_fixture_prediction_results()
    if board.empty:
        st.warning("전체 경기 예상/결과표가 없습니다. 먼저 전체실행을 눌러주세요.")
        return
    board = board.fillna("").sort_values(["date", "kickoff_kst", "league", "home_team"])
    dates = sorted([d for d in board.get("date", pd.Series(dtype=str)).unique() if clean(d)])
    c1, c2, c3 = st.columns([1.1, 1.1, .8])
    with c1:
        selected_dates = st.multiselect("날짜", dates, default=dates[:3] if len(dates)>3 else dates, label_visibility="collapsed")
    with c2:
        mode = st.selectbox("보기", ["전체 경기", "예정 경기", "결과 있는 경기", "분석가능 우선"], label_visibility="collapsed")
    with c3:
        limit = st.number_input("경기수", min_value=5, max_value=200, value=80, step=5, label_visibility="collapsed")
    view = board[board["date"].isin(selected_dates)] if selected_dates else board
    if mode == "예정 경기":
        view = view[view.get("actual_result", "") == "예정"]
    elif mode == "결과 있는 경기":
        view = view[view.get("actual_result", "") != "예정"]
    elif mode == "분석가능 우선":
        view = view[~view.get("main_candidate", "").isin(["분석대기", "분석불가 0 높", "확인 0 높"])]
    view = view.head(int(limit))
    st.markdown("<div class='live-wrap'>", unsafe_allow_html=True)
    for date in sorted(view["date"].unique()):
        day = view[view["date"] == date]
        st.markdown(f"<div class='live-date'>📅 {html_escape(date_label_kr(date))} 전체 경기 {len(day)}개</div>", unsafe_allow_html=True)
        for league in sorted(day["league"].unique()):
            ldf = day[day["league"] == league]
            st.markdown(f"<div class='live-league'>🏆 {html_escape(ko_league(league) or '리그 미확인')}</div>", unsafe_allow_html=True)
            for _, r in ldf.iterrows():
                rd = r.to_dict()
                hs = clean(rd.get("home_score")); aw = clean(rd.get("away_score"))
                score = f"{hs}:{aw}" if hs != "" and aw != "" else "예정"
                result = clean(rd.get("actual_result")) or "예정"
                status = clean(rd.get("match_status")) or "SCHEDULED"
                badge = result if result != "예정" else clean(rd.get("main_candidate")) or "분석대기"
                st.markdown(f"""
<div class='live-card'>
  <div class='live-top'><span>⏱ {html_escape(clean(rd.get('kickoff_kst')) or '-')} · {html_escape(status)}</span><span class='live-pill'>{html_escape(badge)}</span></div>
  <div class='live-teams'><div class='live-home'>{html_escape(ko_team(rd.get('home_team')))}</div><div class='live-score'>{html_escape(score)}</div><div class='live-away'>{html_escape(ko_team(rd.get('away_team')))}</div></div>
  <div class='live-result'><div class='live-label'>예상</div><div class='live-value'>1X2 {html_escape(rd.get('pred_1x2'))} · H {html_escape(rd.get('pred_handicap'))} · U/O {html_escape(rd.get('pred_overunder'))}</div></div>
  <div class='live-result'><div class='live-label'>결과</div><div class='live-value'>{html_escape(result)}</div></div>
  <div class='live-sub'>{html_escape(rd.get('proto_status'))} · {html_escape(rd.get('missing_data'))}</div>
</div>
""", unsafe_allow_html=True)
                mdf = analysis_all[analysis_all.get("match_id", pd.Series(dtype=str)).astype(str) == clean(rd.get("match_id"))] if not analysis_all.empty and "match_id" in analysis_all.columns else pd.DataFrame()
                if not mdf.empty:
                    render_match_detail_expander(mdf, "live", clean(rd.get("match")))
    st.markdown("</div>", unsafe_allow_html=True)
    with st.expander("숨김: 전체 경기 예상/결과 원본", expanded=False):
        show_cols = [c for c in ["date","kickoff_kst","league","home_team","away_team","home_score","away_score","actual_result","pred_1x2","pred_handicap","pred_overunder","main_candidate","proto_status","missing_data"] if c in board.columns]
        st.dataframe(board[show_cols], width="stretch", hide_index=True)

def render_mobile_tab():
    st.subheader("📱 모바일 추천 — Galaxy S26 Ultra 압축 프로토 카드")
    st.caption("경기 날짜별 → 리그별 → 양팀/승무패/핸디/언더오버를 한 카드에 압축 표시합니다. 자동구매/자동결제는 없습니다.")
    mobile_card_css()
    df = read_csv(OUTPUT_FILES["mobile_recommendations"])
    if df.empty:
        st.warning("모바일 추천카드 없음. 전체실행을 먼저 실행하세요.")
        return

    df = sort_recommendations(df).fillna("")
    dates = sorted([d for d in df.get("date", pd.Series(dtype=str)).unique() if clean(d)])

    top_cols = st.columns([1.1, 1.1, .9])
    with top_cols[0]:
        selected_dates = st.multiselect("날짜", dates, default=dates[:2] if len(dates) > 2 else dates, label_visibility="collapsed")
    with top_cols[1]:
        grade_filter = st.selectbox("보기", ["우선 후보", "전체", "자료확인 포함"], label_visibility="collapsed")
    with top_cols[2]:
        max_matches = st.number_input("경기수", min_value=3, max_value=50, value=20, step=1, label_visibility="collapsed")

    view = df[df["date"].isin(selected_dates)] if selected_dates else df
    if grade_filter == "우선 후보":
        view = view[(view.get("risk", "") != "높음") & (~view.get("pick", "").isin(["분석불가", "자료확인 필요", ""]))]
    elif grade_filter == "전체":
        view = view[~view.get("pick", "").isin(["분석불가", ""])]

    if view.empty:
        st.info("선택한 조건에 맞는 추천이 없습니다. '자료확인 포함'으로 바꿔보세요.")
        return

    # 경기 단위 제한: 한 경기 안에서는 주요 승부식을 모두 보여준다.
    key_cols = ["date", "league", "kickoff_kst", "match"]
    match_keys = view[key_cols].drop_duplicates().head(int(max_matches))
    allowed = set(tuple(x) for x in match_keys[key_cols].astype(str).values.tolist())
    view = view[view[key_cols].astype(str).apply(lambda r: tuple(r.values.tolist()) in allowed, axis=1)]

    st.markdown("<div class='maru-mobile-wrap'>", unsafe_allow_html=True)
    for date in sorted(view["date"].unique()):
        day_df = view[view["date"] == date]
        st.markdown(f"<div class='date-head'>📅 {html_escape(date_label_kr(date))}</div>", unsafe_allow_html=True)
        for league in sorted(day_df["league"].unique()):
            league_df = day_df[day_df["league"] == league]
            st.markdown(f"<div class='league-head'>🏆 {html_escape(ko_league(league))}</div>", unsafe_allow_html=True)
            for (kickoff, match), mdf in league_df.groupby(["kickoff_kst", "match"], dropna=False, sort=True):
                mdf = mdf.copy()
                # 주요 시장 먼저. 너무 길어지지 않게 기본 1X2/H/UO/DC만 먼저 보이고, 나머지는 접기에서 본다.
                major = mdf[mdf["market_type"].isin(["승무패", "핸디캡", "언더오버", "더블찬스"])]
                if major.empty:
                    major = mdf.head(4)
                candidate = best_proto_candidates(mdf, 1)
                if not candidate.empty:
                    r0 = candidate.iloc[0].to_dict()
                    badge = f"{short_market_code(r0.get('market_type'), r0.get('line_value'))} {compact_pick_text(r0)}"
                    card_grade = recommendation_grade(r0)
                else:
                    badge = "자료확인"
                    card_grade = "C-자료확인"
                home, away = split_match_teams(mdf.iloc[0].to_dict())
                home, away = ko_team(home), ko_team(away)
                real_any = any(is_real_proto_row(r.to_dict()) for _, r in mdf.iterrows())
                proto_state = "실배당" if real_any else "배당미연동"
                market_html = "".join(compact_market_line(r.to_dict()) for _, r in major.iterrows())
                notice_bits = []
                if not real_any:
                    notice_bits.append("실제 프로토 배당 미연동")
                miss = clean(mdf.iloc[0].get("missing_data"))
                if miss:
                    short_miss = miss.replace("감독 취임일/전술 없음 / ", "").replace("영입/뉴스/스카우트 없음", "영입/뉴스 없음")
                    notice_bits.append(short_miss)
                notice = " · ".join(notice_bits[:2])
                st.markdown(f"""
<div class='proto-card'>
  <div class='proto-top'>
    <div class='proto-time'>⏱ {html_escape(kickoff)}</div>
    <div class='proto-badge'>{html_escape(badge)} · {html_escape(card_grade)} · {html_escape(proto_state)}</div>
  </div>
  <div class='teams'><div class='team home'>{html_escape(home)}</div><div class='vs'>VS</div><div class='team away'>{html_escape(away)}</div></div>
  {market_html}
  <div class='notice'>{html_escape(notice)}</div>
</div>
""", unsafe_allow_html=True)
                render_match_detail_expander(mdf, "mobile", str(match))
                extra = mdf[~mdf["market_type"].isin(["승무패", "핸디캡", "언더오버", "더블찬스"])]
                if not extra.empty:
                    with st.expander(f"숨김: {match} 기타 승부식/근거", expanded=False):
                        extra_rows = []
                        for _, r in extra.iterrows():
                            rd = r.to_dict()
                            extra_rows.append({
                                "승부식": short_market_code(rd.get("market_type"), rd.get("line_value")),
                                "배당": compact_odds_text(rd),
                                "추천": compact_pick_text(rd),
                                "등급": recommendation_grade(rd),
                            })
                        st.dataframe(pd.DataFrame(extra_rows), width="stretch", hide_index=True)
                        detail = mdf.copy()
                        detail["등급"] = detail.apply(lambda r: recommendation_grade(r.to_dict()), axis=1)
                        cols = [c for c in ["market_type","line_value","pick","confidence","risk","data_sufficiency","등급","reasons","missing_data"] if c in detail.columns]
                        st.dataframe(detail[cols].rename(columns={**KOR_COLUMNS, "등급":"등급"}), width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("숨김: 모바일 추천 원본 전체", expanded=False):
        st.dataframe(ko_df(df), width="stretch", hide_index=True)

def get_app_mode():
    """URL ?mode=mobile 이면 모바일 전용 화면으로 완전 분기한다."""
    try:
        params = st.query_params
        mode = params.get("mode", "pc")
        if isinstance(mode, list):
            mode = mode[0] if mode else "pc"
        return str(mode).lower().strip()
    except Exception:
        try:
            params = st.experimental_get_query_params()
            mode = params.get("mode", ["pc"])[0]
            return str(mode).lower().strip()
        except Exception:
            return "pc"



def mobile_only_css():
    st.markdown("""
<style>
:root { --maru-bg:#050b12; --maru-card:#0d1724; --maru-card2:#101f31; --maru-line:#1d3f59; --maru-green:#67e84a; --maru-green2:#20c25d; --maru-text:#f5f8fb; --maru-sub:#9fb6cb; --maru-warn:#ffd76a; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {visibility:hidden !important; height:0 !important;}
[data-testid="stHeader"] {background: transparent !important; height:0px !important;}
.stApp {background: radial-gradient(circle at 20% 0%, #0b2b22 0%, #050b12 42%, #03070d 100%) !important; color: var(--maru-text) !important;}
.block-container {padding-top:.35rem !important; padding-left:.55rem !important; padding-right:.55rem !important; max-width:640px !important;}
.maru-hero {border:1px solid #24506e; border-radius:22px; padding:15px 14px; margin:2px 0 10px 0; background:linear-gradient(135deg,#071421,#0c2236 56%,#0b2f22); box-shadow:0 8px 28px rgba(0,0,0,.28);} 
.maru-hero-title {font-size:1.42rem; font-weight:1000; letter-spacing:-.04em; color:#fff; line-height:1.18;}
.maru-hero-title b {color:var(--maru-green);}
.maru-hero-sub {font-size:.78rem; color:#b9d0e4; margin-top:5px; font-weight:700;}
.maru-status-strip {display:flex; flex-wrap:wrap; gap:6px; margin-top:10px;}
.maru-status-pill {border:1px solid #27624a; border-radius:999px; background:#0b2f22; color:#dfffe8; padding:5px 9px; font-size:.72rem; font-weight:900;}
.maru-status-pill.warn {border-color:#755c22;background:#2d240c;color:#ffe8a0;}
.step-tabs {display:grid; grid-template-columns:1fr 1fr 1fr; gap:7px; margin:10px 0 12px 0;}
.step-pill {border-radius:14px; padding:9px 5px; text-align:center; background:#101e2e; border:1px solid #1e3b57; color:#bed1e3; font-size:.82rem; font-weight:950;}
.step-pill.active {background:linear-gradient(135deg,#23bd5c,#70ec48); color:#06120a; border:none;}
.date-row {display:flex; gap:7px; margin:8px 0 10px; overflow:auto; padding-bottom:2px;}
.date-chip {white-space:nowrap; border-radius:999px; padding:7px 12px; background:#101e2e; border:1px solid #1e3b57; color:#bed1e3; font-size:.82rem; font-weight:900;}
.date-chip.on {background:#63e64e;color:#06120a;border:none;}
.match-count {font-size:.85rem; color:#c7d9e9; font-weight:900; margin:8px 0 6px;}
.league-title {font-size:.88rem; font-weight:1000; color:#b8dcff; margin:12px 0 6px;}
.ticket-card {border:1px solid #213d57; background:linear-gradient(180deg,#0f1c2b,#08131e); border-radius:18px; padding:10px 11px; margin:8px 0; box-shadow:0 6px 18px rgba(0,0,0,.23);}
.ticket-top {display:flex; justify-content:space-between; align-items:center; gap:8px; color:#91aac0; font-size:.72rem; font-weight:850;}
.ticket-teams {display:grid; grid-template-columns:1fr 45px 1fr; gap:7px; align-items:center; margin:9px 0 7px;}
.team-name {font-size:1.02rem; font-weight:1000; color:#fff; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;}
.team-away {text-align:right;}
.vs-badge {text-align:center; font-size:.73rem; color:#92a7ba; font-weight:900;}
.market-grid {display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; margin-top:7px;}
.market-box {border:1px solid #223b51; background:#0a1521; border-radius:12px; padding:7px 4px; text-align:center; min-height:58px;}
.market-label {font-size:.62rem; color:#9eb4c7; font-weight:900;}
.market-value {font-size:.82rem; color:#fff; font-weight:1000; margin-top:2px;}
.market-note {font-size:.62rem; color:#68e862; font-weight:900; margin-top:2px;}
.ai-line {display:flex; justify-content:space-between; align-items:center; gap:8px; margin-top:8px; padding:8px 9px; border-radius:12px; background:#0b2d1c; color:#dfffe0; font-size:.78rem; font-weight:950;}
.ai-line .risk {color:#ffdd78;}
.card-actions {display:grid; grid-template-columns:1fr 1fr; gap:7px; margin-top:8px;}
.action-mini {border-radius:11px; padding:8px 6px; text-align:center; font-size:.75rem; font-weight:950; background:#173b28; color:#9cff9b; border:1px solid #2a7345;}
.action-mini.secondary {background:#101e2e;color:#c9ddf0;border-color:#264862;}
.stExpander {border:1px solid #1e3b57 !important; border-radius:14px !important; background:#0b1420 !important;}
.stExpander summary {font-weight:900 !important; color:#e5f2ff !important;}
div[data-testid="stMetric"] {background:#0d1724; border:1px solid #213d57; border-radius:12px; padding:8px;}
.check-panel {border:1px solid #37602e; background:#101b14; border-radius:14px; padding:10px; margin:8px 0;}
.check-title {font-weight:1000; color:#9aff76; margin-bottom:6px;}
.summary-ticket {border:1px dashed #e5c27b; border-radius:14px; padding:9px; background:#1f1a10; color:#ffe9b7; margin:8px 0; font-size:.82rem; font-weight:850;}
.footer-note {text-align:center; color:#9fb6cb; font-size:.72rem; padding:16px 0 4px;}
/* Streamlit 기본 버튼을 모바일 앱 버튼처럼 */
.stButton button {border-radius:12px !important; font-weight:900 !important;}
@media(max-width:430px){.block-container{padding-left:.45rem!important;padding-right:.45rem!important}.maru-hero-title{font-size:1.28rem}.market-grid{gap:4px}.market-box{padding:6px 2px}.team-name{font-size:.98rem}.ai-line{font-size:.72rem}.step-pill{font-size:.76rem}}
</style>
""", unsafe_allow_html=True)


def _market_for_card(mdf: pd.DataFrame, market_name: str):
    if mdf is None or mdf.empty:
        return None
    row = pick_market_row(mdf, market_name)
    return row if row else None


def _market_box_html(label: str, row: dict, fallback: str = "분석대기") -> str:
    if row:
        pick = compact_pick_text(row)
        conf = clean(row.get("confidence")) or "0"
        risk = clean(row.get("risk")) or "-"
        return f"<div class='market-box'><div class='market-label'>{html_escape(label)}</div><div class='market-value'>{html_escape(pick)}</div><div class='market-note'>신뢰 {html_escape(conf)} · {html_escape(risk)}</div></div>"
    return f"<div class='market-box'><div class='market-label'>{html_escape(label)}</div><div class='market-value'>{html_escape(fallback)}</div><div class='market-note'>자료확인</div></div>"


def _ticket_summary_box() -> str:
    return """
<div class='summary-ticket'>
  <b>실물 티켓 매칭용 요약</b><br>
  선택 경기 수 · 예상 배당률 · 총투표금액은 현장/공식 용지와 직접 대조합니다.<br>
  자동구매/자동결제 없음 · 오프라인 수동 체크 전용
</div>
"""


def render_premium_match_expanders(mdf: pd.DataFrame, context: str, match_label: str):
    if mdf is None or mdf.empty:
        return
    first = mdf.iloc[0].to_dict()
    main = best_match_candidate(mdf)
    reasons = split_reasons(clean(main.get("reasons"))) if main else {}
    home, away = split_match_teams(first)
    home_ko, away_ko = ko_team(home), ko_team(away)
    mid = clean(first.get("match_id")) or safe_key(context, match_label, home_ko, away_ko)
    with st.expander(f"🔎 분석 이유 펼치기 — {home_ko} vs {away_ko}", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("AI 예상", clean(main.get("pick")) if main else "분석대기")
        c2.metric("신뢰도", clean(main.get("confidence")) if main else "0")
        c3.metric("위험도", clean(main.get("risk")) if main else "-")
        st.markdown("**왜 이렇게 예상되나?**")
        st.write(why_summary_from_row(main) if main else "분석자료가 부족합니다.")
        st.markdown("**핵심 근거**")
        st.write(f"- 최근폼: {reasons.get('recent_form', '자료 없음')}")
        st.write(f"- 홈/원정 성적: {reasons.get('home_away_form', '자료 없음')}")
        st.write(f"- 상대전적: {reasons.get('h2h', '자료 없음')}")
        st.write(f"- 부족자료: {clean(main.get('missing_data')) if main else '자료 없음'}")
        st.caption("분석 이유는 기본 숨김이며, 필요할 때만 펼쳐서 확인합니다.")
    with st.expander(f"🧾 오프라인 수동 구매 체크표 — {home_ko} vs {away_ko}", expanded=False):
        st.markdown(_ticket_summary_box(), unsafe_allow_html=True)
        st.markdown("<div class='check-panel'><div class='check-title'>직접 확인 후 체크</div>", unsafe_allow_html=True)
        checks = [
            f"경기명 확인: {home_ko} vs {away_ko}",
            f"시간 확인: {clean(first.get('kickoff_kst')) or '-'}",
            "승무패 번호/배당 확인",
            "핸디캡 기준점/배당 확인",
            "언더/오버 기준점/배당 확인",
            "라이브스코어 상태 확인",
            "내가 직접 마킹 완료",
        ]
        for idx, item in enumerate(checks):
            st.checkbox(item, key=f"v19_chk_{context}_{safe_key(mid, idx, item)}")
        st.markdown("</div>", unsafe_allow_html=True)
        st.info("자동구매/자동결제 없음. 오프라인에서 직접 확인 후 수동 구매 체크만 지원합니다.")


def render_mobile_premium_ticket_app():
    mobile_only_css()
    diag = build_diagnosis()
    counts = diag.get("counts", {})
    st.markdown(f"""
<div class='maru-hero'>
  <div class='maru-hero-title'>모바일은 보기 편하게,<br><b>실물 티켓과 맞춰 확인</b></div>
  <div class='maru-hero-sub'>전체 경기 → 분석 보기 → 결과 확인 → 오프라인 수동 체크</div>
  <div class='maru-status-strip'>
    <span class='maru-status-pill'>허브 {diag.get('hub_url','OFF')}</span>
    <span class='maru-status-pill'>시트 {diag.get('google_sheet_url','OFF')}</span>
    <span class='maru-status-pill'>추천 {counts.get('mobile_recommendations',0)}건</span>
    <span class='maru-status-pill'>전체경기 {counts.get('fixture_prediction_results',0)}건</span>
    <span class='maru-status-pill warn'>자동구매 없음</span>
  </div>
</div>
<div class='step-tabs'>
  <div class='step-pill active'>1 전체 경기</div>
  <div class='step-pill'>2 분석 보기</div>
  <div class='step-pill'>3 수동 체크</div>
</div>
""", unsafe_allow_html=True)

    board = read_csv(OUTPUT_FILES["fixture_prediction_results"])
    analysis_all = read_csv(OUTPUT_FILES["analysis_scores"])
    if board.empty:
        board = build_fixture_prediction_results()
    if board.empty or analysis_all.empty:
        st.warning("자료가 부족합니다. PC에서 전체실행 + 허브 저장을 먼저 실행하세요.")
        return
    board = board.fillna("").sort_values(["date", "kickoff_kst", "league", "home_team"])
    analysis_all = analysis_all.fillna("")
    dates = sorted([d for d in board.get("date", pd.Series(dtype=str)).unique() if clean(d)])
    if not dates:
        st.warning("날짜 데이터가 없습니다.")
        return
    # 모바일에서는 기본으로 전체 날짜를 보여주되, 칩으로 날짜 감각을 준다.
    chip_html = "".join([f"<span class='date-chip {'on' if i==0 else ''}'>{html_escape(date_label_kr(d))}</span>" for i,d in enumerate(dates[:5])])
    st.markdown(f"<div class='date-row'>{chip_html}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='match-count'>전체 경기 {len(board)}건 · 현재 표시 {min(len(board), 80)}건</div>", unsafe_allow_html=True)
    view = board.head(80)
    for date in sorted(view["date"].unique()):
        day = view[view["date"] == date]
        st.markdown(f"<div class='league-title'>📅 {html_escape(date_label_kr(date))} · 전체 경기 {len(day)}건</div>", unsafe_allow_html=True)
        for league in sorted(day["league"].unique()):
            ldf = day[day["league"] == league]
            st.markdown(f"<div class='league-title'>🏆 {html_escape(ko_league(league) or '리그 미확인')}</div>", unsafe_allow_html=True)
            for _, rd_ser in ldf.iterrows():
                rd = rd_ser.to_dict()
                match_id = clean(rd.get("match_id"))
                mdf = analysis_all[analysis_all.get("match_id", pd.Series(dtype=str)).astype(str) == match_id] if "match_id" in analysis_all.columns else pd.DataFrame()
                if mdf.empty:
                    continue
                first = mdf.iloc[0].to_dict()
                home, away = split_match_teams(first)
                home_ko, away_ko = ko_team(home or rd.get("home_team")), ko_team(away or rd.get("away_team"))
                one = _market_for_card(mdf, "승무패")
                hcap = _market_for_card(mdf, "핸디캡")
                uo = _market_for_card(mdf, "언더오버")
                main = best_match_candidate(mdf)
                main_text = compact_pick_text(main) if main else clean(rd.get("main_candidate")) or "분석대기"
                conf = clean(main.get("confidence")) if main else "0"
                risk = clean(main.get("risk")) if main else "-"
                score = "예정"
                hs, aw = clean(rd.get("home_score")), clean(rd.get("away_score"))
                if hs != "" and aw != "": score = f"{hs}:{aw}"
                st.markdown(f"""
<div class='ticket-card'>
  <div class='ticket-top'><span>⏱ {html_escape(clean(rd.get('kickoff_kst')) or '-')} · {html_escape(clean(rd.get('match_status')) or 'SCHEDULED')}</span><span>{html_escape(score)}</span></div>
  <div class='ticket-teams'><div class='team-name'>{html_escape(home_ko)}</div><div class='vs-badge'>VS</div><div class='team-name team-away'>{html_escape(away_ko)}</div></div>
  <div class='market-grid'>
    {_market_box_html('승무패', one)}
    {_market_box_html('핸디캡', hcap)}
    {_market_box_html('언더/오버', uo)}
  </div>
  <div class='ai-line'><span>AI 추천: {html_escape(main_text)}</span><span>신뢰 {html_escape(conf)} · <span class='risk'>위험 {html_escape(risk)}</span></span></div>
  <div class='card-actions'><div class='action-mini'>분석 보기</div><div class='action-mini secondary'>오프라인 체크</div></div>
</div>
""", unsafe_allow_html=True)
                render_mobile_ticket_expanders(mdf, "v19mobile", f"{home_ko}_{away_ko}")
    st.markdown("<div class='footer-note'>PC는 확인용 · 모바일은 실제 사용용 · 기존 기능 유지 · 허브 저장 확인 · 자동구매/자동결제 없음</div>", unsafe_allow_html=True)


def render_mobile_ticket_expanders(mdf: pd.DataFrame, context: str, match_label: str):
    # 모바일에서 더 짧게 보이도록 전용 펼침을 사용한다.
    if mdf is None or mdf.empty:
        return
    first = mdf.iloc[0].to_dict()
    main = best_match_candidate(mdf)
    reasons = split_reasons(clean(main.get("reasons"))) if main else {}
    home, away = split_match_teams(first)
    home_ko, away_ko = ko_team(home), ko_team(away)
    mid = clean(first.get("match_id")) or safe_key(context, match_label)
    with st.expander(f"🔍 분석 이유 보기 — {home_ko} vs {away_ko}", expanded=False):
        st.write(f"**AI 예상:** {compact_pick_text(main) if main else '분석대기'}")
        st.write(f"**왜:** {why_summary_from_row(main) if main else '분석자료 부족'}")
        st.write(f"- 최근폼: {reasons.get('recent_form', '자료 없음')}")
        st.write(f"- 홈/원정: {reasons.get('home_away_form', '자료 없음')}")
        st.write(f"- 상대전적: {reasons.get('h2h', '자료 없음')}")
        st.write(f"- 부족자료: {clean(main.get('missing_data')) if main else '자료 없음'}")
    with st.expander(f"🧾 실물 티켓 대조 / 오프라인 수동 체크 — {home_ko} vs {away_ko}", expanded=False):
        st.markdown(_ticket_summary_box(), unsafe_allow_html=True)
        checks = [
            f"경기명 확인: {home_ko} vs {away_ko}",
            f"시간 확인: {clean(first.get('kickoff_kst')) or '-'}",
            "승무패 번호/배당 확인",
            "핸디캡 기준점/배당 확인",
            "언더/오버 기준점/배당 확인",
            "라이브스코어 상태 확인",
            "내가 직접 마킹 완료",
        ]
        for idx, item in enumerate(checks):
            st.checkbox(item, key=f"v19_mobile_ticket_{safe_key(mid, idx, item)}")
        st.warning("자동구매/자동결제 없음 · 오프라인 판매점에서 직접 확인 후 수동 구매")


def render_mobile_only_app():
    render_mobile_premium_ticket_app()
    st.caption(f"{APP_VERSION} · 모바일 전용 티켓 매칭 모드 · 자동구매/자동결제 없음 · 오프라인 수동 확인")

def main():
    ensure_dirs()
    st.set_page_config(page_title=APP_NAME, page_icon="⚽", layout="wide", initial_sidebar_state="collapsed")
    mode = get_app_mode()
    if mode in ["mobile", "m", "phone"]:
        render_mobile_only_app()
        return

    st.title("⚽ 마루 스포츠 프로토 일정 허브")
    st.caption("일정표 자동수집 → 과거 빅데이터 매칭 → 승부식 분석 → 모바일 추천 → 허브/구글시트 전송")
    render_metrics()
    tabs = st.tabs(["대시보드", "전체 경기", "PC 모니터링", "일정표", "자료 입력", "모바일 추천", "허브 전송", "백엔드 진단"])
    with tabs[0]: render_full_run()
    with tabs[1]: render_livescore_board_tab()
    with tabs[2]:
        render_download_bar("monitor")
        render_recent_outputs()
    with tabs[3]: render_fixture_tab()
    with tabs[4]: render_data_input_tab()
    with tabs[5]: render_mobile_tab()
    with tabs[6]: render_hub_tab()
    with tabs[7]: render_diagnosis_tab()
    st.caption(f"{APP_VERSION} · {now_text()} · 자동구매/자동결제 없음 · 기존 기능 유지 + 모바일 전용 mode 분리")


if __name__ == "__main__":
    main()
