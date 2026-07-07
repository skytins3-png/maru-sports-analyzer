from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

KST = timezone(timedelta(hours=9))

DEFAULT_DATE_URL = "https://api.sportmonks.com/v3/football/fixtures/date/{today_dash}?api_token={api_key}&include=participants;league"
DEFAULT_BETWEEN_URL = "https://api.sportmonks.com/v3/football/fixtures/between/{from_dash}/{to_dash}?api_token={api_key}&include=participants;league"

LAST_COLLECTION_INFO: Dict[str, Any] = {
    "source": "not_started",
    "ok": False,
    "message": "아직 수집 전",
    "http_status": "",
    "count": 0,
    "data_count": 0,
    "response_preview": "",
    "safe_final_url": "",
    "updated_at": "",
}


def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def today_dash() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def add_days_dash(days: int) -> str:
    return (datetime.now(KST) + timedelta(days=days)).strftime("%Y-%m-%d")


def _read_secret(name: str, default: str = "") -> str:
    value = os.getenv(name, "")
    if value:
        return value
    try:
        import streamlit as st  # imported lazily only inside Streamlit runtime
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def get_token() -> str:
    return _read_secret("SPORTMONKS_API_TOKEN", _read_secret("SPORTS_API_KEY", ""))


def get_date_url_template() -> str:
    return _read_secret("SKYTOTO_SPORTS_API_URL", DEFAULT_DATE_URL) or DEFAULT_DATE_URL


def _mask_url(url: str, token: str) -> str:
    if token and token in url:
        shown = token[:4] + "…" + token[-4:] if len(token) > 8 else "****"
        return url.replace(token, shown)
    return url


def _preview(obj: Any, limit: int = 1200) -> str:
    try:
        return str(obj)[:limit]
    except Exception:
        return ""


def _team_name(p: Dict[str, Any]) -> str:
    return (
        p.get("name")
        or p.get("short_code")
        or p.get("display_name")
        or p.get("common_name")
        or p.get("team_name")
        or "Unknown"
    )


def _extract_participants(fixture: Dict[str, Any]) -> Tuple[str, str]:
    participants = fixture.get("participants") or []
    if isinstance(participants, dict):
        participants = participants.get("data") or []
    if not isinstance(participants, list):
        participants = []

    home, away = "", ""
    for p in participants:
        if not isinstance(p, dict):
            continue
        loc = str((p.get("meta") or {}).get("location", "")).lower()
        name = _team_name(p)
        if loc == "home":
            home = name
        elif loc == "away":
            away = name

    if (not home or not away) and len(participants) >= 2:
        names = [_team_name(p) for p in participants if isinstance(p, dict)]
        if names:
            home = home or names[0]
        if len(names) > 1:
            away = away or names[1]

    return home or "Home", away or "Away"


def _league(fixture: Dict[str, Any]) -> str:
    league = fixture.get("league") or {}
    if isinstance(league, dict):
        return league.get("name") or league.get("display_name") or league.get("short_code") or "Football"
    return "Football"


def _status(fixture: Dict[str, Any]) -> str:
    state = fixture.get("state") or fixture.get("status") or fixture.get("time_status") or fixture.get("result_info")
    if isinstance(state, dict):
        return state.get("name") or state.get("short_name") or "scheduled"
    return str(state or "scheduled")


def normalize_fixture(fixture: Dict[str, Any], idx: int = 1) -> Dict[str, Any]:
    home, away = _extract_participants(fixture)
    start = fixture.get("starting_at") or fixture.get("starting_at_timestamp") or ""
    kickoff = str(start)
    if isinstance(start, int):
        try:
            kickoff = datetime.fromtimestamp(start, tz=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
        except Exception:
            kickoff = str(start)
    elif isinstance(start, str) and start:
        kickoff = start.replace("T", " ")

    return {
        "match_id": str(fixture.get("id") or fixture.get("fixture_id") or f"SM_{today_dash()}_{idx:03d}"),
        "date": today_dash(),
        "league": _league(fixture),
        "match_no": str(idx).zfill(3),
        "home_team": home,
        "away_team": away,
        "kickoff_kst": kickoff,
        "status": _status(fixture),
        "data_source": "sportmonks",
        "raw_id": fixture.get("id", ""),
        "has_participants": bool(fixture.get("participants")),
    }


def _call_url(url: str, token: str, source_name: str, timeout: int = 20) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    safe_url = _mask_url(url, token)
    try:
        res = requests.get(url, timeout=timeout)
        try:
            payload = res.json()
        except Exception:
            payload = {"text": getattr(res, "text", "")[:1200]}

        data: List[Any] = []
        if isinstance(payload, dict):
            raw = payload.get("data", [])
            data = raw if isinstance(raw, list) else []
        elif isinstance(payload, list):
            data = payload

        fixtures: List[Dict[str, Any]] = []
        if 200 <= res.status_code < 300:
            fixtures = [normalize_fixture(x, i + 1) for i, x in enumerate(data) if isinstance(x, dict)]

        info = {
            "source": source_name,
            "ok": bool(fixtures),
            "message": "수집 성공" if fixtures else ("HTTP 성공, data 0건" if 200 <= res.status_code < 300 else f"HTTP {res.status_code}"),
            "http_status": str(res.status_code),
            "count": len(fixtures),
            "data_count": len(data),
            "response_preview": _preview(payload),
            "safe_final_url": safe_url,
            "updated_at": now_kst(),
        }
        return fixtures, info
    except Exception as e:
        return [], {
            "source": source_name,
            "ok": False,
            "message": f"호출 실패: {e}",
            "http_status": "",
            "count": 0,
            "data_count": 0,
            "response_preview": "",
            "safe_final_url": safe_url,
            "updated_at": now_kst(),
        }


def fetch_sportmonks_fixtures(date_dash: Optional[str] = None, timeout: int = 20) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    global LAST_COLLECTION_INFO
    date_dash = date_dash or today_dash()
    token = get_token()

    if not token:
        info = {
            "source": "sportmonks",
            "ok": False,
            "message": "SPORTMONKS_API_TOKEN 또는 SPORTS_API_KEY 없음",
            "http_status": "",
            "count": 0,
            "data_count": 0,
            "response_preview": "",
            "safe_final_url": "",
            "updated_at": now_kst(),
        }
        LAST_COLLECTION_INFO = info
        return [], info

    try:
        url = get_date_url_template().format(today_dash=date_dash, api_key=token)
    except Exception as e:
        info = {
            "source": "sportmonks_date",
            "ok": False,
            "message": f"URL 템플릿 오류: {e}",
            "http_status": "",
            "count": 0,
            "data_count": 0,
            "response_preview": "",
            "safe_final_url": get_date_url_template(),
            "updated_at": now_kst(),
        }
        LAST_COLLECTION_INFO = info
        return [], info

    fixtures, info = _call_url(url, token, "sportmonks_date", timeout)
    if fixtures:
        LAST_COLLECTION_INFO = info
        return fixtures, info

    between_url = DEFAULT_BETWEEN_URL.format(from_dash=date_dash, to_dash=add_days_dash(7), api_key=token)
    fixtures2, info2 = _call_url(between_url, token, "sportmonks_between_7d", timeout)
    if fixtures2:
        info2["message"] = f"오늘 경기 실패/0건 후 7일 범위 수집 성공. 1차: {info.get('message')}"
        LAST_COLLECTION_INFO = info2
        return fixtures2, info2

    info2["message"] = f"date 실패/0건: {info.get('message')} | between 실패/0건: {info2.get('message')}"
    info2["first_try"] = info
    LAST_COLLECTION_INFO = info2
    return [], info2


def run_diagnostic_test() -> Dict[str, Any]:
    token = get_token()
    fixtures, info = fetch_sportmonks_fixtures(timeout=20)
    return {
        "token_detected": bool(token),
        "token_preview": token[:4] + "…" + token[-4:] if token and len(token) > 8 else ("있음" if token else "없음"),
        "fixtures_count": len(fixtures),
        "info": info,
        "first_fixture": fixtures[0] if fixtures else {},
    }


def get_last_collection_info() -> Dict[str, Any]:
    return dict(LAST_COLLECTION_INFO)
