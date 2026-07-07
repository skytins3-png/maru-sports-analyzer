from __future__ import annotations

import os
import requests
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple, Optional

KST = timezone(timedelta(hours=9))
DEFAULT_DATE_URL = "https://api.sportmonks.com/v3/football/fixtures/date/{today_dash}?api_token={api_key}&include=participants;league"
DEFAULT_BETWEEN_URL = "https://api.sportmonks.com/v3/football/fixtures/between/{from_dash}/{to_dash}?api_token={api_key}&include=participants;league"

LAST_COLLECTION_INFO: Dict[str, Any] = {
    "source": "manual_only",
    "ok": False,
    "message": "안전부팅 모드: 앱 시작 시 API 자동수집 안 함. 버튼으로만 테스트.",
    "http_status": "",
    "count": 0,
    "data_count": 0,
    "response_preview": "",
    "safe_final_url": "",
    "updated_at": "",
}


def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def date_dash_offset(days: int) -> str:
    return (datetime.now(KST) + timedelta(days=days)).strftime("%Y-%m-%d")


def today_dash() -> str:
    return date_dash_offset(0)


def _read_secret(name: str, default: str = "") -> str:
    value = os.getenv(name, "")
    if value:
        return value
    try:
        import streamlit as st
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
    return str(obj)[:limit]


def _team_name(p: Dict[str, Any]) -> str:
    return p.get("name") or p.get("short_code") or p.get("display_name") or p.get("common_name") or "Unknown"


def _participants(f: Dict[str, Any]) -> Tuple[str, str]:
    ps = f.get("participants") or []
    if isinstance(ps, dict):
        ps = ps.get("data") or []
    if not isinstance(ps, list):
        ps = []
    home, away = "", ""
    for p in ps:
        if not isinstance(p, dict):
            continue
        loc = str((p.get("meta") or {}).get("location", "")).lower()
        name = _team_name(p)
        if loc == "home":
            home = name
        elif loc == "away":
            away = name
    if (not home or not away) and len(ps) >= 2:
        names = [_team_name(p) for p in ps if isinstance(p, dict)]
        if names:
            home = home or names[0]
        if len(names) > 1:
            away = away or names[1]
    return home or "Home", away or "Away"


def _league(f: Dict[str, Any]) -> str:
    league = f.get("league") or {}
    if isinstance(league, dict):
        return league.get("name") or league.get("display_name") or league.get("short_code") or "Football"
    return "Football"


def normalize_fixture(f: Dict[str, Any], idx: int = 1) -> Dict[str, Any]:
    home, away = _participants(f)
    start = f.get("starting_at") or f.get("starting_at_timestamp") or ""
    kickoff = str(start)
    if isinstance(start, int):
        try:
            kickoff = datetime.fromtimestamp(start, tz=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
        except Exception:
            kickoff = str(start)
    elif isinstance(start, str) and start:
        kickoff = start.replace("T", " ")

    state = f.get("state") or f.get("status") or "scheduled"
    if isinstance(state, dict):
        state = state.get("name") or state.get("short_name") or "scheduled"

    return {
        "match_id": str(f.get("id") or f"SM_{today_dash()}_{idx:03d}"),
        "date": today_dash(),
        "league": _league(f),
        "match_no": str(idx).zfill(3),
        "home_team": home,
        "away_team": away,
        "kickoff_kst": kickoff,
        "status": str(state),
        "data_source": "sportmonks",
        "raw_id": f.get("id", ""),
        "has_participants": bool(f.get("participants")),
    }


def _call_url(url: str, token: str, source_name: str, timeout: int = 15) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    safe_url = _mask_url(url, token)
    try:
        res = requests.get(url, timeout=timeout)
        try:
            payload = res.json()
        except Exception:
            payload = {"text": res.text[:1200]}

        data = []
        if isinstance(payload, dict):
            raw = payload.get("data", [])
            data = raw if isinstance(raw, list) else []
        elif isinstance(payload, list):
            data = payload

        fixtures = []
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


def fetch_sportmonks_between(from_dash: str, to_dash: str, timeout: int = 15) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    global LAST_COLLECTION_INFO
    token = get_token()
    if not token:
        info = {
            "source": "sportmonks_between",
            "ok": False,
            "message": "SPORTMONKS_API_TOKEN 또는 SPORTS_API_KEY 없음",
            "http_status": "",
            "count": 0,
            "data_count": 0,
            "response_preview": "",
            "safe_final_url": "",
            "updated_at": now_kst(),
            "from_dash": from_dash,
            "to_dash": to_dash,
        }
        LAST_COLLECTION_INFO = info
        return [], info

    url = DEFAULT_BETWEEN_URL.format(from_dash=from_dash, to_dash=to_dash, api_key=token)
    fixtures, info = _call_url(url, token, f"sportmonks_between_{from_dash}_{to_dash}", timeout=timeout)
    info["from_dash"] = from_dash
    info["to_dash"] = to_dash
    LAST_COLLECTION_INFO = info
    return fixtures, info


def test_history_range(days_back: int, timeout: int = 15) -> Dict[str, Any]:
    """
    지난 N일 범위가 실제로 몇 경기 받아지는지 테스트.
    예: days_back=7이면 오늘 기준 -7일 ~ 오늘.
    """
    from_dash = date_dash_offset(-abs(int(days_back)))
    to_dash = today_dash()
    fixtures, info = fetch_sportmonks_between(from_dash, to_dash, timeout=timeout)
    return {
        "range_days": abs(int(days_back)),
        "from_dash": from_dash,
        "to_dash": to_dash,
        "fixtures_count": len(fixtures),
        "ok": bool(fixtures),
        "info": info,
        "first_fixture": fixtures[0] if fixtures else {},
    }


def test_history_ranges(days_list=None, timeout: int = 12) -> Dict[str, Any]:
    """
    여러 기간을 차례로 테스트. 너무 무겁지 않게 버튼으로만 실행.
    """
    if days_list is None:
        days_list = [1, 3, 7, 14, 30, 60, 90]
    results = []
    max_ok_days = 0
    for days in days_list:
        result = test_history_range(int(days), timeout=timeout)
        results.append(result)
        if result.get("fixtures_count", 0) > 0:
            max_ok_days = int(days)
    return {
        "tested_at": now_kst(),
        "max_range_with_data": max_ok_days,
        "results": results,
    }


def fetch_sportmonks_fixtures(date_dash: Optional[str] = None, timeout: int = 12) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    호환용 함수. 오늘~7일 미래/현재 테스트에 사용.
    앱 시작 시에는 호출하지 않는다.
    """
    date_dash = date_dash or today_dash()
    return fetch_sportmonks_between(date_dash, date_dash, timeout=timeout)


def run_diagnostic_test() -> Dict[str, Any]:
    token = get_token()
    result = test_history_range(7, timeout=12)
    return {
        "token_detected": bool(token),
        "token_preview": token[:4] + "…" + token[-4:] if token and len(token) > 8 else ("있음" if token else "없음"),
        "fixtures_count": result.get("fixtures_count", 0),
        "info": result.get("info", {}),
        "first_fixture": result.get("first_fixture", {}),
    }


def get_last_collection_info() -> Dict[str, Any]:
    return dict(LAST_COLLECTION_INFO)
