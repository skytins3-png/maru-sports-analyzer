from __future__ import annotations

import os
import requests
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple, Optional


KST = timezone(timedelta(hours=9))

DEFAULT_FIXTURES_URL = (
    "https://api.sportmonks.com/v3/football/fixtures/date/{today_dash}"
    "?api_token={api_key}&include=participants;league"
)

LAST_COLLECTION_INFO = {
    "source": "sample",
    "ok": False,
    "message": "not started",
    "http_status": "",
    "count": 0,
    "used_url_template": "",
    "updated_at": "",
}


def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def today_dash() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _read_secret(name: str, default: str = "") -> str:
    """
    Streamlit 앱에서는 st.secrets, GitHub Actions에서는 os.environ에서 읽는다.
    """
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


def get_url_template() -> str:
    return _read_secret("SKYTOTO_SPORTS_API_URL", DEFAULT_FIXTURES_URL) or DEFAULT_FIXTURES_URL


def _safe_team_name(participant: Dict[str, Any]) -> str:
    return (
        participant.get("name")
        or participant.get("short_code")
        or participant.get("display_name")
        or participant.get("common_name")
        or participant.get("team_name")
        or "Unknown"
    )


def _extract_participants(fixture: Dict[str, Any]) -> Tuple[str, str]:
    """
    Sportmonks v3 participants include에서 홈/원정 팀을 파싱한다.
    meta.location이 있으면 우선 사용하고, 없으면 순서 기반으로 fallback.
    """
    participants = fixture.get("participants") or []
    home = ""
    away = ""

    if isinstance(participants, dict):
        participants = participants.get("data") or []

    if not isinstance(participants, list):
        participants = []

    for p in participants:
        if not isinstance(p, dict):
            continue
        name = _safe_team_name(p)
        meta = p.get("meta") or {}
        location = str(meta.get("location", "")).lower()
        if location == "home":
            home = name
        elif location == "away":
            away = name

    if (not home or not away) and len(participants) >= 2:
        names = [_safe_team_name(p) for p in participants if isinstance(p, dict)]
        if names:
            home = home or names[0]
        if len(names) > 1:
            away = away or names[1]

    return home or "Home", away or "Away"


def _extract_league(fixture: Dict[str, Any]) -> str:
    league = fixture.get("league") or {}
    if isinstance(league, dict):
        return league.get("name") or league.get("display_name") or league.get("short_code") or "Football"
    return "Football"


def _extract_status(fixture: Dict[str, Any]) -> str:
    state = fixture.get("state") or fixture.get("status") or fixture.get("time_status") or fixture.get("result_info")
    if isinstance(state, dict):
        return state.get("name") or state.get("short_name") or state.get("state") or "scheduled"
    return str(state or "scheduled")


def normalize_fixture(fixture: Dict[str, Any], idx: int = 1) -> Dict[str, Any]:
    home, away = _extract_participants(fixture)
    league = _extract_league(fixture)

    fixture_id = fixture.get("id") or fixture.get("fixture_id") or f"SM_{today_dash()}_{idx:03d}"
    starting_at = fixture.get("starting_at") or fixture.get("starting_at_timestamp") or ""

    kickoff = str(starting_at)
    if isinstance(starting_at, int):
        try:
            kickoff = datetime.fromtimestamp(starting_at, tz=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
        except Exception:
            kickoff = str(starting_at)
    elif isinstance(starting_at, str) and starting_at:
        kickoff = starting_at.replace("T", " ")

    return {
        "match_id": str(fixture_id),
        "date": today_dash(),
        "league": league,
        "match_no": str(idx).zfill(3),
        "home_team": home,
        "away_team": away,
        "kickoff_kst": kickoff,
        "status": _extract_status(fixture),
        "data_source": "sportmonks",
        "raw_id": fixture.get("id", ""),
    }


def fetch_sportmonks_fixtures(date_dash: Optional[str] = None, timeout: int = 15) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Sportmonks fixtures/date 실제 호출.
    실패하거나 data가 비어 있으면 빈 리스트와 상태정보를 반환한다.
    """
    global LAST_COLLECTION_INFO

    date_dash = date_dash or today_dash()
    token = get_token()
    url_template = get_url_template()
    updated_at = now_kst()

    if not token:
        info = {
            "source": "sportmonks",
            "ok": False,
            "message": "SPORTMONKS_API_TOKEN 또는 SPORTS_API_KEY 없음",
            "http_status": "",
            "count": 0,
            "used_url_template": url_template,
            "updated_at": updated_at,
        }
        LAST_COLLECTION_INFO = info
        return [], info

    try:
        url = url_template.format(today_dash=date_dash, api_key=token)
    except Exception as e:
        info = {
            "source": "sportmonks",
            "ok": False,
            "message": f"URL 템플릿 format 실패: {e}",
            "http_status": "",
            "count": 0,
            "used_url_template": url_template,
            "updated_at": updated_at,
        }
        LAST_COLLECTION_INFO = info
        return [], info

    safe_url_template = url_template.replace(token, "***") if token else url_template

    try:
        res = requests.get(url, timeout=timeout)
        http_status = str(res.status_code)

        if not (200 <= res.status_code < 300):
            info = {
                "source": "sportmonks",
                "ok": False,
                "message": f"HTTP {res.status_code}: {res.text[:300]}",
                "http_status": http_status,
                "count": 0,
                "used_url_template": safe_url_template,
                "updated_at": updated_at,
            }
            LAST_COLLECTION_INFO = info
            return [], info

        payload = res.json()
        data = payload.get("data", payload if isinstance(payload, list) else [])

        if not isinstance(data, list):
            data = []

        fixtures = [normalize_fixture(item, i + 1) for i, item in enumerate(data) if isinstance(item, dict)]

        info = {
            "source": "sportmonks",
            "ok": bool(fixtures),
            "message": "Sportmonks 수집 성공" if fixtures else "HTTP 성공, 경기 data 0건",
            "http_status": http_status,
            "count": len(fixtures),
            "used_url_template": safe_url_template,
            "updated_at": updated_at,
        }
        LAST_COLLECTION_INFO = info
        return fixtures, info

    except Exception as e:
        info = {
            "source": "sportmonks",
            "ok": False,
            "message": f"Sportmonks 호출 실패: {e}",
            "http_status": "",
            "count": 0,
            "used_url_template": safe_url_template,
            "updated_at": updated_at,
        }
        LAST_COLLECTION_INFO = info
        return [], info


def get_last_collection_info() -> Dict[str, Any]:
    return dict(LAST_COLLECTION_INFO)
