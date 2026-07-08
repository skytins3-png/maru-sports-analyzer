# -*- coding: utf-8 -*-
"""
MARU SPORTS ANALYZER
사이트별 분류 저장 + 표준화 + 허브/구글시트 중심 구조판

원칙
- source_* 파일: 수집원별 원본/중간 자료 저장
- standard_* 파일: 분석 엔진이 읽는 표준 자료
- 추천카드: standard_upcoming_fixtures.csv 의 예정 경기만 대상
- 샘플/TEST/가짜 추천카드 없음
- 자료 부족 시 자료부족/분석불가 표시
- 자동구매/자동결제 없음
"""

from __future__ import annotations

import json
import os
import re
import traceback
from io import StringIO
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st

APP_NAME = "MARU SPORTS ANALYZER"
DATA_DIR = Path(os.getenv("MARU_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

FILES: Dict[str, List[str]] = {
    "source_football_data.csv": [
        "source", "collected_at", "league", "season", "match_date", "home_team", "away_team",
        "home_score", "away_score", "result", "raw_json", "note"
    ],
    "source_sportmonks.csv": [
        "source", "collected_at", "league", "season", "match_date", "home_team", "away_team",
        "fixture_id", "status", "raw_json", "note"
    ],
    "source_thesportsdb.csv": [
        "source", "collected_at", "league", "season", "match_date", "home_team", "away_team",
        "event_id", "status", "raw_json", "note"
    ],
    "source_manual.csv": [
        "source", "collected_at", "match_date", "league", "home_team", "away_team", "data_type",
        "team", "manager", "player", "status", "formation", "memo", "reliability"
    ],
    "standard_history_matches.csv": [
        "standard_type", "updated_at", "match_date", "league", "season", "home_team", "away_team",
        "home_score", "away_score", "result", "source_refs", "quality_note"
    ],
    "standard_upcoming_fixtures.csv": [
        "standard_type", "updated_at", "fixture_id", "match_date", "league", "season", "home_team", "away_team",
        "source_refs", "status", "quality_note"
    ],
    "standard_team_status.csv": [
        "standard_type", "updated_at", "match_date", "league", "team", "manager", "key_players",
        "tactics", "memo", "source_refs", "reliability"
    ],
    "standard_injuries.csv": [
        "standard_type", "updated_at", "match_date", "league", "team", "player", "status", "memo", "source_refs", "reliability"
    ],
    "standard_lineups.csv": [
        "standard_type", "updated_at", "match_date", "league", "team", "formation", "expected_lineup", "memo", "source_refs", "reliability"
    ],
    "analysis_scores.csv": [
        "analyzed_at", "fixture_id", "match_date", "league", "home_team", "away_team", "direction",
        "confidence", "risk", "data_sufficiency", "missing_data", "reason", "analysis_status"
    ],
    "mobile_recommendations.csv": [
        "created_at", "fixture_id", "match_date", "league", "match_name", "recommendation",
        "confidence", "risk", "data_sufficiency", "missing_data", "notice", "manual_decision_only"
    ],
    "hub_send_logs.csv": [
        "sent_at", "target", "file_name", "row_count", "status", "message"
    ],
    "error_logs.csv": [
        "time", "where", "status", "message", "trace"
    ],
}

SOURCE_FILES = ["source_football_data.csv", "source_sportmonks.csv", "source_thesportsdb.csv", "source_manual.csv"]
STANDARD_FILES = [
    "standard_history_matches.csv", "standard_upcoming_fixtures.csv", "standard_team_status.csv",
    "standard_injuries.csv", "standard_lineups.csv"
]
OUTPUT_FILES = ["analysis_scores.csv", "mobile_recommendations.csv", "hub_send_logs.csv", "error_logs.csv"]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return date.today().isoformat()


def file_path(name: str) -> Path:
    return DATA_DIR / name


def ensure_files() -> None:
    for name, cols in FILES.items():
        p = file_path(name)
        if not p.exists():
            pd.DataFrame(columns=cols).to_csv(p, index=False, encoding="utf-8-sig")


def read_csv(name: str) -> pd.DataFrame:
    ensure_files()
    p = file_path(name)
    try:
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
    except Exception:
        df = pd.DataFrame(columns=FILES[name])
    for col in FILES[name]:
        if col not in df.columns:
            df[col] = ""
    return df[FILES[name]]


def write_csv(name: str, df: pd.DataFrame) -> None:
    for col in FILES[name]:
        if col not in df.columns:
            df[col] = ""
    df[FILES[name]].to_csv(file_path(name), index=False, encoding="utf-8-sig")


def append_rows(name: str, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    old = read_csv(name)
    new = pd.DataFrame(rows)
    merged = pd.concat([old, new], ignore_index=True)
    write_csv(name, merged)
    return len(rows)


def log_error(where: str, message: str, trace: str = "") -> None:
    append_rows("error_logs.csv", [{
        "time": now_str(), "where": where, "status": "error", "message": str(message), "trace": trace[-3000:]
    }])


def clean_team(x: Any) -> str:
    return re.sub(r"\s+", " ", str(x or "").strip())


def parse_date(x: Any) -> str:
    s = str(x or "").strip()
    if not s:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except Exception:
            pass
    try:
        return pd.to_datetime(s, errors="coerce").date().isoformat()
    except Exception:
        return s[:10]


def safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)[:5000]
    except Exception:
        return str(obj)[:5000]


def dedupe(df: pd.DataFrame, subset: List[str]) -> pd.DataFrame:
    if df.empty:
        return df
    use_subset = [c for c in subset if c in df.columns]
    if not use_subset:
        return df.drop_duplicates()
    return df.drop_duplicates(subset=use_subset, keep="last")



FOOTBALL_DATA_LEAGUES = {
    "E0": "England Premier League",
    "E1": "England Championship",
    "D1": "Germany Bundesliga",
    "SP1": "Spain LaLiga",
    "I1": "Italy Serie A",
    "F1": "France Ligue 1",
    "N1": "Netherlands Eredivisie",
    "P1": "Portugal Primeira Liga",
    "B1": "Belgium First Division A",
    "SC0": "Scotland Premiership",
}


def football_data_season_candidates() -> List[str]:
    """현재 날짜 기준으로 football-data 시즌 코드를 자동 생성한다. 예: 2026/27 -> 2627."""
    y = date.today().year
    start = y if date.today().month >= 7 else y - 1
    out = []
    for sy in [start, start - 1, start - 2, start - 3]:
        code = f"{str(sy)[-2:]}{str(sy + 1)[-2:]}"
        if code not in out:
            out.append(code)
    return out


def football_data_url_candidates(season: str, league_code: str) -> List[str]:
    # football-data는 시기별 폴더명이 달라진 적이 있어 후보를 순차 검사한다. 실패하면 다음 주소로 자동 이동.
    return [
        f"https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv",
        f"https://www.football-data.co.uk/mmz4371/{season}/{league_code}.csv",
    ]


def collect_football_data_auto(league_codes: List[str], season_codes: List[str]) -> Tuple[int, str, pd.DataFrame]:
    """리그/시즌 후보를 자동 순회한다. 사용자가 URL을 복사하지 않아도 되는 자동 수집기."""
    total_rows = []
    logs = []
    for season in season_codes:
        for code in league_codes:
            code = str(code).strip().upper()
            league_name = FOOTBALL_DATA_LEAGUES.get(code, code)
            saved_for_pair = False
            for url in football_data_url_candidates(season, code):
                log = {
                    "source": "football-data.co.uk", "collected_at": now_str(), "league": league_name,
                    "season": season, "match_date": "", "home_team": "", "away_team": "",
                    "home_score": "", "away_score": "", "result": "", "raw_json": "",
                    "note": f"TRY {url}",
                }
                try:
                    resp = requests.get(url, timeout=12, headers={"User-Agent": "MARU-Sports-Analyzer"})
                    if resp.status_code != 200 or not resp.text.strip():
                        log["note"] = f"SKIP HTTP {resp.status_code}: {url}"
                        logs.append(log)
                        continue
                    df = pd.read_csv(StringIO(resp.text))
                    rows = []
                    for _, r in df.iterrows():
                        home = clean_team(r.get("HomeTeam", ""))
                        away = clean_team(r.get("AwayTeam", ""))
                        if not home or not away:
                            continue
                        hs_raw = r.get("FTHG", "")
                        as_raw = r.get("FTAG", "")
                        hs = "" if pd.isna(hs_raw) else str(hs_raw)
                        aas = "" if pd.isna(as_raw) else str(as_raw)
                        # football-data는 완료 경기 위주다. 점수 없는 행은 과거결과 표준화에서 제외된다.
                        rows.append({
                            "source": "football-data.co.uk",
                            "collected_at": now_str(),
                            "league": league_name,
                            "season": season,
                            "match_date": parse_date(r.get("Date", "")),
                            "home_team": home,
                            "away_team": away,
                            "home_score": hs,
                            "away_score": aas,
                            "result": str(r.get("FTR", "")),
                            "raw_json": safe_json(r.to_dict()),
                            "note": f"AUTO_OK {url}",
                        })
                    if rows:
                        total_rows.extend(rows)
                        log["note"] = f"OK {len(rows)} rows: {url}"
                        logs.append(log)
                        saved_for_pair = True
                        break
                    log["note"] = f"SKIP no rows: {url}"
                    logs.append(log)
                except Exception as e:
                    log["note"] = f"SKIP error: {e} | {url}"
                    logs.append(log)
                    continue
            if not saved_for_pair:
                logs.append({
                    "source": "football-data.co.uk", "collected_at": now_str(), "league": league_name,
                    "season": season, "match_date": "", "home_team": "", "away_team": "",
                    "home_score": "", "away_score": "", "result": "", "raw_json": "",
                    "note": f"NO_VALID_URL_FOR {season}/{code}",
                })
    n = append_rows("source_football_data.csv", total_rows)
    append_rows("source_football_data.csv", logs)  # 로그도 같은 source 파일에 note로 남겨 PC 모니터링 가능
    log_df = pd.DataFrame(logs)
    return n, f"football-data 자동 탐색 저장 {n}건 · 실패 주소는 자동 건너뜀", log_df

# --------------------------- 수집원별 저장 ---------------------------

def collect_football_data_csv(url: str, league: str, season: str) -> Tuple[int, str]:
    """football-data.co.uk CSV URL을 source_football_data.csv에 저장한다. 과거 결과 수집원일 뿐 고정 수집원이 아니다."""
    if not url.strip():
        return 0, "CSV URL이 비어 있습니다."
    try:
        df = pd.read_csv(url)
        rows = []
        for _, r in df.iterrows():
            home = clean_team(r.get("HomeTeam", ""))
            away = clean_team(r.get("AwayTeam", ""))
            if not home or not away:
                continue
            hs = str(r.get("FTHG", "") if pd.notna(r.get("FTHG", "")) else "")
            aas = str(r.get("FTAG", "") if pd.notna(r.get("FTAG", "")) else "")
            result = str(r.get("FTR", ""))
            rows.append({
                "source": "football-data.co.uk",
                "collected_at": now_str(),
                "league": league.strip(),
                "season": season.strip(),
                "match_date": parse_date(r.get("Date", "")),
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": aas,
                "result": result,
                "raw_json": safe_json(r.to_dict()),
                "note": "history/result source only",
            })
        n = append_rows("source_football_data.csv", rows)
        return n, f"football-data 원본 {n}건 저장"
    except Exception as e:
        log_error("collect_football_data_csv", str(e), traceback.format_exc())
        return 0, f"football-data 수집 실패: {e}"


def collect_sportmonks(api_token: str, start_date: str, end_date: str) -> Tuple[int, str]:
    """Sportmonks 가능 범위 저장. 무료 플랜에서 빈 data가 나오면 원본 상태만 기록하지 않고 오류 로그에 남긴다."""
    if not api_token.strip():
        return 0, "Sportmonks API token이 없습니다."
    try:
        url = f"https://api.sportmonks.com/v3/football/fixtures/between/{start_date}/{end_date}"
        params = {"api_token": api_token.strip(), "include": "participants;league"}
        res = requests.get(url, params=params, timeout=25)
        payload = res.json() if "application/json" in res.headers.get("content-type", "") else {"text": res.text[:3000]}
        data = payload.get("data", []) if isinstance(payload, dict) else []
        rows = []
        for item in data:
            participants = item.get("participants") or []
            home, away = "", ""
            for p in participants:
                meta = p.get("meta") or {}
                loc = str(meta.get("location", "")).lower()
                if loc == "home":
                    home = p.get("name", "")
                elif loc == "away":
                    away = p.get("name", "")
            league = ""
            if isinstance(item.get("league"), dict):
                league = item["league"].get("name", "")
            rows.append({
                "source": "sportmonks",
                "collected_at": now_str(),
                "league": league,
                "season": str(item.get("season_id", "")),
                "match_date": parse_date(item.get("starting_at", "")),
                "home_team": clean_team(home),
                "away_team": clean_team(away),
                "fixture_id": str(item.get("id", "")),
                "status": str(item.get("state_id", item.get("status", ""))),
                "raw_json": safe_json(item),
                "note": "source stored separately",
            })
        n = append_rows("source_sportmonks.csv", rows)
        if n == 0:
            log_error("collect_sportmonks", "HTTP success but no usable fixtures", safe_json(payload))
        return n, f"Sportmonks 원본 {n}건 저장"
    except Exception as e:
        log_error("collect_sportmonks", str(e), traceback.format_exc())
        return 0, f"Sportmonks 수집 실패: {e}"


def collect_thesportsdb(league_id: str, season: str) -> Tuple[int, str]:
    """TheSportsDB 이벤트 보조 자료 저장. 무료 공개 API 구조 기준."""
    if not league_id.strip():
        return 0, "TheSportsDB league_id가 없습니다."
    try:
        url = "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php"
        params = {"id": league_id.strip(), "s": season.strip()}
        res = requests.get(url, params=params, timeout=25)
        payload = res.json()
        events = payload.get("events") or []
        rows = []
        for e in events:
            rows.append({
                "source": "thesportsdb",
                "collected_at": now_str(),
                "league": e.get("strLeague", ""),
                "season": season.strip(),
                "match_date": parse_date(e.get("dateEvent", "")),
                "home_team": clean_team(e.get("strHomeTeam", "")),
                "away_team": clean_team(e.get("strAwayTeam", "")),
                "event_id": str(e.get("idEvent", "")),
                "status": str(e.get("strStatus", "")),
                "raw_json": safe_json(e),
                "note": "team/event auxiliary source",
            })
        n = append_rows("source_thesportsdb.csv", rows)
        return n, f"TheSportsDB 원본 {n}건 저장"
    except Exception as e:
        log_error("collect_thesportsdb", str(e), traceback.format_exc())
        return 0, f"TheSportsDB 수집 실패: {e}"


# --------------------------- 표준화 ---------------------------

def build_standard_tables() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    updated = now_str()

    # 과거 경기: football-data 중심 + 다른 source 중 점수가 있으면 보조 확장 가능
    fd = read_csv("source_football_data.csv")
    hist_rows = []
    for _, r in fd.iterrows():
        if not r.get("match_date") or not r.get("home_team") or not r.get("away_team"):
            continue
        if str(r.get("home_score", "")).strip() == "" or str(r.get("away_score", "")).strip() == "":
            continue
        hist_rows.append({
            "standard_type": "history_match",
            "updated_at": updated,
            "match_date": r.get("match_date", ""),
            "league": r.get("league", ""),
            "season": r.get("season", ""),
            "home_team": r.get("home_team", ""),
            "away_team": r.get("away_team", ""),
            "home_score": r.get("home_score", ""),
            "away_score": r.get("away_score", ""),
            "result": r.get("result", ""),
            "source_refs": "source_football_data.csv",
            "quality_note": "past result only; not recommendation target",
        })
    hist = dedupe(pd.DataFrame(hist_rows), ["match_date", "league", "home_team", "away_team"])
    write_csv("standard_history_matches.csv", hist)
    counts["standard_history_matches.csv"] = len(hist)

    # 예정 경기: Sportmonks + TheSportsDB에서 점수 없는 미래/예정 경기만 표준화
    upcoming_rows = []
    for fname in ["source_sportmonks.csv", "source_thesportsdb.csv"]:
        src = read_csv(fname)
        for _, r in src.iterrows():
            md = r.get("match_date", "")
            home = r.get("home_team", "")
            away = r.get("away_team", "")
            if not md or not home or not away:
                continue
            # 과거 경기 현재 추천 방지: 오늘 이전은 추천 대상에서 제외
            if md < today_str():
                continue
            fid = r.get("fixture_id", "") or r.get("event_id", "") or f"{fname}:{md}:{home}:{away}"
            upcoming_rows.append({
                "standard_type": "upcoming_fixture",
                "updated_at": updated,
                "fixture_id": str(fid),
                "match_date": md,
                "league": r.get("league", ""),
                "season": r.get("season", ""),
                "home_team": home,
                "away_team": away,
                "source_refs": fname,
                "status": r.get("status", ""),
                "quality_note": "recommendation target candidate",
            })
    upcoming = dedupe(pd.DataFrame(upcoming_rows), ["match_date", "league", "home_team", "away_team"])
    write_csv("standard_upcoming_fixtures.csv", upcoming)
    counts["standard_upcoming_fixtures.csv"] = len(upcoming)

    # 수동 입력 표준화: 감독/팀상태, 부상, 라인업 분리
    manual = read_csv("source_manual.csv")
    team_rows, injury_rows, lineup_rows = [], [], []
    for _, r in manual.iterrows():
        dtype = str(r.get("data_type", "")).lower()
        source_ref = "source_manual.csv"
        if dtype in ["manager", "team", "team_status", "tactics", "memo"]:
            team_rows.append({
                "standard_type": "team_status",
                "updated_at": updated,
                "match_date": r.get("match_date", ""),
                "league": r.get("league", ""),
                "team": r.get("team", ""),
                "manager": r.get("manager", ""),
                "key_players": r.get("player", ""),
                "tactics": r.get("formation", ""),
                "memo": r.get("memo", ""),
                "source_refs": source_ref,
                "reliability": r.get("reliability", "manual"),
            })
        elif dtype in ["injury", "injuries", "suspension", "absence", "out"]:
            injury_rows.append({
                "standard_type": "injury",
                "updated_at": updated,
                "match_date": r.get("match_date", ""),
                "league": r.get("league", ""),
                "team": r.get("team", ""),
                "player": r.get("player", ""),
                "status": r.get("status", ""),
                "memo": r.get("memo", ""),
                "source_refs": source_ref,
                "reliability": r.get("reliability", "manual"),
            })
        elif dtype in ["lineup", "formation", "expected_lineup"]:
            lineup_rows.append({
                "standard_type": "lineup",
                "updated_at": updated,
                "match_date": r.get("match_date", ""),
                "league": r.get("league", ""),
                "team": r.get("team", ""),
                "formation": r.get("formation", ""),
                "expected_lineup": r.get("player", ""),
                "memo": r.get("memo", ""),
                "source_refs": source_ref,
                "reliability": r.get("reliability", "manual"),
            })
    team_df = dedupe(pd.DataFrame(team_rows), ["match_date", "league", "team", "manager", "memo"])
    inj_df = dedupe(pd.DataFrame(injury_rows), ["match_date", "league", "team", "player", "status"])
    lin_df = dedupe(pd.DataFrame(lineup_rows), ["match_date", "league", "team", "formation", "expected_lineup"])
    write_csv("standard_team_status.csv", team_df)
    write_csv("standard_injuries.csv", inj_df)
    write_csv("standard_lineups.csv", lin_df)
    counts["standard_team_status.csv"] = len(team_df)
    counts["standard_injuries.csv"] = len(inj_df)
    counts["standard_lineups.csv"] = len(lin_df)
    return counts


# --------------------------- 분석/추천 ---------------------------

def latest_team_rows(df: pd.DataFrame, team: str, match_date: str, league: str) -> pd.DataFrame:
    if df.empty:
        return df
    cond = df["team"].astype(str).str.lower().eq(team.lower())
    if "league" in df.columns and league:
        cond &= (df["league"].astype(str).eq(league) | df["league"].astype(str).eq(""))
    if "match_date" in df.columns:
        cond &= (df["match_date"].astype(str).eq(match_date) | df["match_date"].astype(str).eq(""))
    return df[cond]


def recent_form_points(history: pd.DataFrame, team: str, before_date: str, limit: int = 5) -> Tuple[int, int, str]:
    if history.empty or not team:
        return 0, 0, "최근경기 없음"
    h = history.copy()
    h = h[h["match_date"].astype(str) < before_date]
    h = h[(h["home_team"].astype(str).str.lower() == team.lower()) | (h["away_team"].astype(str).str.lower() == team.lower())]
    h = h.sort_values("match_date", ascending=False).head(limit)
    pts = 0
    played = 0
    for _, r in h.iterrows():
        played += 1
        home = r.get("home_team", "")
        res = str(r.get("result", ""))
        if team.lower() == str(home).lower():
            pts += 3 if res == "H" else 1 if res == "D" else 0
        else:
            pts += 3 if res == "A" else 1 if res == "D" else 0
    return pts, played, f"최근 {played}경기 {pts}점"


def analyze_and_create_mobile() -> Tuple[int, int]:
    fixtures = read_csv("standard_upcoming_fixtures.csv")
    history = read_csv("standard_history_matches.csv")
    team_status = read_csv("standard_team_status.csv")
    injuries = read_csv("standard_injuries.csv")
    lineups = read_csv("standard_lineups.csv")

    analysis_rows: List[Dict[str, Any]] = []
    mobile_rows: List[Dict[str, Any]] = []

    # 샘플 금지: 예정 경기가 없으면 결과 파일을 비워 자료부족 상태를 명확히 함
    if fixtures.empty:
        write_csv("analysis_scores.csv", pd.DataFrame(columns=FILES["analysis_scores.csv"]))
        write_csv("mobile_recommendations.csv", pd.DataFrame(columns=FILES["mobile_recommendations.csv"]))
        return 0, 0

    fixtures = fixtures[fixtures["match_date"].astype(str) >= today_str()].copy()

    for _, fx in fixtures.iterrows():
        fid = fx.get("fixture_id", "")
        md = fx.get("match_date", "")
        league = fx.get("league", "")
        home = fx.get("home_team", "")
        away = fx.get("away_team", "")
        match_name = f"{home} vs {away}"

        missing = []
        home_team = latest_team_rows(team_status, home, md, league)
        away_team = latest_team_rows(team_status, away, md, league)
        home_inj = latest_team_rows(injuries, home, md, league)
        away_inj = latest_team_rows(injuries, away, md, league)
        home_line = latest_team_rows(lineups, home, md, league)
        away_line = latest_team_rows(lineups, away, md, league)

        if home_team.empty or away_team.empty:
            missing.append("감독/팀상태")
        if home_inj.empty and away_inj.empty:
            missing.append("부상/결장")
        if home_line.empty or away_line.empty:
            missing.append("예상라인업")

        hp, hp_n, hp_note = recent_form_points(history, home, md)
        ap, ap_n, ap_note = recent_form_points(history, away, md)
        if hp_n < 3 or ap_n < 3:
            missing.append("최근/과거경기 부족")

        evidence_score = 0
        if not (home_team.empty or away_team.empty):
            evidence_score += 25
        if not (home_line.empty or away_line.empty):
            evidence_score += 25
        if not (home_inj.empty and away_inj.empty):
            evidence_score += 15
        if hp_n >= 3 and ap_n >= 3:
            evidence_score += 25
        if md and home and away:
            evidence_score += 10

        data_suff = min(100, evidence_score)

        # 자료 부족 시 추천 방향을 강제로 만들지 않음
        if data_suff < 55:
            direction = "자료부족/분석불가"
            confidence = 0
            risk = "높음"
            status = "insufficient_data"
            reason = f"필수/중요 자료 부족: {', '.join(missing) if missing else '확인 필요'}"
        else:
            diff = hp - ap
            if diff >= 4:
                direction = "홈팀 우세 후보"
            elif diff <= -4:
                direction = "원정팀 우세 후보"
            else:
                direction = "박빙/관망 후보"
            confidence = min(85, max(45, 50 + abs(diff) * 4 + int(data_suff / 10)))
            risk = "낮음" if confidence >= 75 and data_suff >= 75 else "중간" if confidence >= 60 else "높음"
            status = "analyzed"
            reason = f"{home}: {hp_note} / {away}: {ap_note}; 자료충분도 {data_suff}%"

        missing_text = ", ".join(dict.fromkeys(missing))
        analysis_rows.append({
            "analyzed_at": now_str(),
            "fixture_id": fid,
            "match_date": md,
            "league": league,
            "home_team": home,
            "away_team": away,
            "direction": direction,
            "confidence": str(confidence),
            "risk": risk,
            "data_sufficiency": str(data_suff),
            "missing_data": missing_text,
            "reason": reason,
            "analysis_status": status,
        })
        mobile_rows.append({
            "created_at": now_str(),
            "fixture_id": fid,
            "match_date": md,
            "league": league,
            "match_name": match_name,
            "recommendation": direction,
            "confidence": str(confidence),
            "risk": risk,
            "data_sufficiency": str(data_suff),
            "missing_data": missing_text,
            "notice": "자동구매 없음. 사용자가 직접 판단.",
            "manual_decision_only": "Y",
        })

    analysis_df = dedupe(pd.DataFrame(analysis_rows), ["fixture_id", "match_date", "home_team", "away_team"])
    mobile_df = dedupe(pd.DataFrame(mobile_rows), ["fixture_id", "match_date", "match_name"])
    write_csv("analysis_scores.csv", analysis_df)
    write_csv("mobile_recommendations.csv", mobile_df)
    return len(analysis_df), len(mobile_df)


# --------------------------- 허브 전송 ---------------------------

def get_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return os.getenv(name, default)


def send_file_to_hub(file_name: str, hub_url: str) -> Tuple[bool, str]:
    if not hub_url.strip():
        return False, "허브 URL이 비어 있습니다."
    df = read_csv(file_name)
    payload = {
        "app": APP_NAME,
        "sent_at": now_str(),
        "file_name": file_name,
        "row_count": len(df),
        "columns": list(df.columns),
        "rows": df.fillna("").to_dict(orient="records"),
    }
    try:
        res = requests.post(hub_url.strip(), json=payload, timeout=30)
        ok = 200 <= res.status_code < 300
        msg = f"HTTP {res.status_code}: {res.text[:500]}"
        append_rows("hub_send_logs.csv", [{
            "sent_at": now_str(), "target": "google_sheet_hub", "file_name": file_name,
            "row_count": str(len(df)), "status": "success" if ok else "error", "message": msg
        }])
        return ok, msg
    except Exception as e:
        log_error("send_file_to_hub", str(e), traceback.format_exc())
        append_rows("hub_send_logs.csv", [{
            "sent_at": now_str(), "target": "google_sheet_hub", "file_name": file_name,
            "row_count": str(len(df)), "status": "error", "message": str(e)
        }])
        return False, str(e)


# --------------------------- UI ---------------------------

def inject_css() -> None:
    st.markdown(
        """
        <style>
        .main .block-container {padding-top: 1.2rem; max-width: 1200px;}
        .big-card {border:1px solid #ddd; border-radius:16px; padding:16px; margin:10px 0; background:#fff;}
        .mobile-card {border:2px solid #222; border-radius:18px; padding:18px; margin:14px 0; background:#fafafa;}
        .danger {color:#b00020; font-weight:800;}
        .ok {color:#146c2e; font-weight:800;}
        .muted {color:#666;}
        [data-testid="stMetricValue"] {font-size: 1.6rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_row(names: List[str]) -> None:
    cols = st.columns(len(names))
    for c, name in zip(cols, names):
        c.metric(name.replace(".csv", ""), len(read_csv(name)))


def show_df(name: str, height: int = 280) -> None:
    df = read_csv(name)
    st.caption(f"{name} / {len(df)}건")
    st.dataframe(df.tail(300), use_container_width=True, height=height)
    st.download_button(
        label=f"{name} 다운로드",
        data=df.to_csv(index=False, encoding="utf-8-sig"),
        file_name=name,
        mime="text/csv",
        key=f"download_{name}",
    )


def tab_pc_monitoring() -> None:
    st.subheader("PC 모니터링 / 확인")
    st.write("수집원별 저장 건수, 표준화 결과, 분석 점수, 허브 전송 상태를 확인합니다.")
    metric_row(SOURCE_FILES)
    metric_row(STANDARD_FILES)
    metric_row(OUTPUT_FILES)

    c1, c2, c3 = st.columns(3)
    if c1.button("① 표준화 실행", use_container_width=True):
        counts = build_standard_tables()
        st.success(f"표준화 완료: {counts}")
    if c2.button("② 분석/모바일추천 생성", use_container_width=True):
        a, m = analyze_and_create_mobile()
        if m == 0:
            st.warning("예정 경기 없음 또는 자료 부족: 가짜 추천카드는 만들지 않았습니다.")
        else:
            st.success(f"분석 {a}건 / 모바일 추천카드 {m}건 생성")
    if c3.button("③ 전체 실행", use_container_width=True):
        counts = build_standard_tables()
        a, m = analyze_and_create_mobile()
        st.success(f"표준화 {counts} / 분석 {a}건 / 모바일 {m}건")

    st.divider()
    view = st.selectbox("확인할 파일", SOURCE_FILES + STANDARD_FILES + OUTPUT_FILES, index=0)
    show_df(view)


def tab_mobile() -> None:
    st.subheader("모바일 추천카드")
    st.caption("자동구매 없음 · 자동결제 없음 · 사용자가 직접 판단")
    df = read_csv("mobile_recommendations.csv")
    if df.empty:
        st.warning("현재 추천카드가 없습니다. 예정 경기 표준화 후 분석을 실행해야 합니다. 샘플/TEST 카드는 표시하지 않습니다.")
        return
    df = df[df["match_date"].astype(str) >= today_str()].sort_values(["match_date", "league", "match_name"])
    if df.empty:
        st.warning("현재 이후 예정 경기 추천카드가 없습니다. 과거 경기는 추천카드 대상에서 제외했습니다.")
        return
    for _, r in df.iterrows():
        rec = r.get("recommendation", "")
        risk = r.get("risk", "")
        suff = r.get("data_sufficiency", "")
        conf = r.get("confidence", "")
        missing = r.get("missing_data", "") or "없음"
        st.markdown(
            f"""
            <div class="mobile-card">
              <h3>{r.get('match_name','')}</h3>
              <div class="muted">{r.get('match_date','')} · {r.get('league','')}</div>
              <p><b>추천 방향:</b> {rec}</p>
              <p><b>신뢰도:</b> {conf}% · <b>위험도:</b> {risk} · <b>자료충분도:</b> {suff}%</p>
              <p><b>부족한 자료:</b> {missing}</p>
              <p class="danger">자동구매 없음 / 직접 판단 전용</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def tab_sources() -> None:
    st.subheader("수집원 관리")
    st.write("football-data는 과거결과 수집원 중 하나일 뿐입니다. Sportmonks, TheSportsDB, 수동 자료와 분리 저장합니다.")

    with st.expander("football-data 자동 탐색 → source_football_data.csv", expanded=True):
        st.caption("URL을 수동 복사하지 않습니다. 시즌/리그 후보를 앱이 만들고, 안 되는 주소는 자동으로 건너뜁니다.")
        default_seasons = football_data_season_candidates()
        fd_seasons_text = st.text_input("자동 시즌 후보", value=", ".join(default_seasons))
        fd_codes = st.multiselect(
            "자동 탐색 리그",
            options=list(FOOTBALL_DATA_LEAGUES.keys()),
            default=["E0", "E1", "D1", "SP1", "I1", "F1"],
            format_func=lambda x: f"{x} · {FOOTBALL_DATA_LEAGUES.get(x, x)}",
        )
        st.write("탐색 방식: `시즌 후보 × 리그 후보 × URL 후보` 순서로 검사 → 실패하면 다음 후보 → 성공 자료만 source에 저장")
        if st.button("football-data 자동 탐색 저장", use_container_width=True):
            seasons = [x.strip() for x in fd_seasons_text.split(",") if x.strip()] or default_seasons
            n, msg, log_df = collect_football_data_auto(fd_codes, seasons)
            if n:
                st.success(msg)
            else:
                st.warning(msg)
            st.dataframe(log_df, use_container_width=True)

        with st.expander("고급: 특정 CSV URL 직접 저장"):
            fd_url = st.text_input("CSV URL", placeholder="예: https://www.football-data.co.uk/mmz4281/2526/E0.csv")
            fd_league = st.text_input("리그명", value="")
            fd_season = st.text_input("시즌", value="")
            if st.button("특정 football-data URL 저장", use_container_width=True):
                n, msg = collect_football_data_csv(fd_url, fd_league, fd_season)
                if n:
                    st.success(msg)
                else:
                    st.warning(msg)

    with st.expander("Sportmonks 수집 → source_sportmonks.csv"):
        token_default = get_secret("SPORTMONKS_API_KEY", "")
        sm_token = st.text_input("Sportmonks API Token", value=token_default, type="password")
        c1, c2 = st.columns(2)
        sm_start = c1.date_input("시작일", value=date.today()).isoformat()
        sm_end = c2.date_input("종료일", value=date.today()).isoformat()
        if st.button("Sportmonks 원본 저장", use_container_width=True):
            n, msg = collect_sportmonks(sm_token, sm_start, sm_end)
            if n:
                st.success(msg)
            else:
                st.warning(msg)

    with st.expander("TheSportsDB 수집 → source_thesportsdb.csv"):
        league_id = st.text_input("TheSportsDB League ID", placeholder="예: 4328")
        tsdb_season = st.text_input("시즌", placeholder="예: 2025-2026")
        if st.button("TheSportsDB 원본 저장", use_container_width=True):
            n, msg = collect_thesportsdb(league_id, tsdb_season)
            if n:
                st.success(msg)
            else:
                st.warning(msg)

    with st.expander("CSV 업로드로 source 파일 덮어쓰기/추가"):
        target = st.selectbox("대상 source 파일", SOURCE_FILES)
        mode = st.radio("저장 방식", ["추가", "덮어쓰기"], horizontal=True)
        up = st.file_uploader("CSV 업로드", type=["csv"])
        if up is not None and st.button("업로드 저장", use_container_width=True):
            df = pd.read_csv(up, dtype=str, keep_default_na=False)
            for col in FILES[target]:
                if col not in df.columns:
                    df[col] = ""
            if mode == "추가":
                old = read_csv(target)
                df = pd.concat([old, df[FILES[target]]], ignore_index=True)
            write_csv(target, df)
            st.success(f"{target} 저장 완료: {len(df)}건")


def tab_manual() -> None:
    st.subheader("자료 입력")
    st.write("감독, 부상, 결장, 라인업, 전술 메모를 source_manual.csv에 저장하고 표준화 때 분리합니다.")
    with st.form("manual_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        match_date = c1.date_input("경기일", value=date.today()).isoformat()
        league = c2.text_input("리그")
        data_type = c3.selectbox("자료종류", ["team_status", "injury", "suspension", "lineup", "formation", "memo"])
        home_team = st.text_input("홈팀")
        away_team = st.text_input("원정팀")
        c4, c5 = st.columns(2)
        team = c4.text_input("관련 팀")
        manager = c5.text_input("감독")
        player = st.text_area("선수/핵심선수/예상라인업", height=80)
        c6, c7 = st.columns(2)
        status = c6.text_input("상태", placeholder="부상, 결장, 출장정지, 가능 등")
        formation = c7.text_input("포메이션/전술")
        memo = st.text_area("메모", height=100)
        reliability = st.selectbox("신뢰도", ["manual", "confirmed", "rumor", "low", "high"])
        submitted = st.form_submit_button("source_manual.csv 저장", use_container_width=True)
    if submitted:
        row = {
            "source": "manual",
            "collected_at": now_str(),
            "match_date": match_date,
            "league": league,
            "home_team": home_team,
            "away_team": away_team,
            "data_type": data_type,
            "team": team,
            "manager": manager,
            "player": player,
            "status": status,
            "formation": formation,
            "memo": memo,
            "reliability": reliability,
        }
        append_rows("source_manual.csv", [row])
        st.success("수동 자료 저장 완료")
    show_df("source_manual.csv", height=240)


def tab_hub() -> None:
    st.subheader("허브 / 구글시트 전송")
    st.write("Streamlit cache가 아니라 CSV 결과를 허브/구글시트로 보냅니다. Apps Script 웹앱 URL을 사용합니다.")
    default_url = get_secret("HUB_WEBAPP_URL", "")
    hub_url = st.text_input("Google Apps Script Web App URL", value=default_url, type="password")
    targets = st.multiselect(
        "전송 파일 선택",
        SOURCE_FILES + STANDARD_FILES + ["analysis_scores.csv", "mobile_recommendations.csv"],
        default=["analysis_scores.csv", "mobile_recommendations.csv"],
    )
    if st.button("선택 파일 허브 전송", use_container_width=True):
        for f in targets:
            ok, msg = send_file_to_hub(f, hub_url)
            if ok:
                st.success(f"{f}: {msg}")
            else:
                st.error(f"{f}: {msg}")
    show_df("hub_send_logs.csv", height=260)


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="⚽", layout="wide")
    ensure_files()
    inject_css()
    st.title("⚽ MARU SPORTS ANALYZER")
    st.caption("수집원별 분류 저장 → 표준화 → 분석 → 모바일 추천카드 → 허브/구글시트")

    tabs = st.tabs(["PC 모니터링", "모바일 추천", "수집원 관리", "자료 입력", "허브 전송"])
    with tabs[0]:
        tab_pc_monitoring()
    with tabs[1]:
        tab_mobile()
    with tabs[2]:
        tab_sources()
    with tabs[3]:
        tab_manual()
    with tabs[4]:
        tab_hub()


if __name__ == "__main__":
    main()
