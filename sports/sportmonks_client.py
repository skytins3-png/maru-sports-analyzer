from __future__ import annotations
import os, requests
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple, Optional

KST = timezone(timedelta(hours=9))
DEFAULT_DATE_URL = "https://api.sportmonks.com/v3/football/fixtures/date/{today_dash}?api_token={api_key}&include=participants;league"
DEFAULT_BETWEEN_URL = "https://api.sportmonks.com/v3/football/fixtures/between/{from_dash}/{to_dash}?api_token={api_key}&include=participants;league"

LAST_COLLECTION_INFO = {"source":"sample","ok":False,"message":"not started","http_status":"","count":0,"data_count":0,"response_preview":"","safe_final_url":"","updated_at":""}

def now_kst(): return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
def today_dash(): return datetime.now(KST).strftime("%Y-%m-%d")
def add_days_dash(days:int): return (datetime.now(KST)+timedelta(days=days)).strftime("%Y-%m-%d")

def _read_secret(name, default=""):
    v = os.getenv(name, "")
    if v: return v
    try:
        import streamlit as st
        return str(st.secrets.get(name, default))
    except Exception:
        return default

def get_token():
    return _read_secret("SPORTMONKS_API_TOKEN", _read_secret("SPORTS_API_KEY", ""))

def get_date_url_template():
    return _read_secret("SKYTOTO_SPORTS_API_URL", DEFAULT_DATE_URL) or DEFAULT_DATE_URL

def _mask_url(url, token):
    if token and token in url:
        return url.replace(token, token[:4] + "…" + token[-4:] if len(token)>8 else "****")
    return url

def _safe_preview(obj, limit=900):
    return str(obj)[:limit]

def _team_name(p):
    return p.get("name") or p.get("short_code") or p.get("display_name") or p.get("common_name") or "Unknown"

def _participants(f):
    ps = f.get("participants") or []
    if isinstance(ps, dict): ps = ps.get("data") or []
    if not isinstance(ps, list): ps = []
    home = away = ""
    for p in ps:
        if not isinstance(p, dict): continue
        loc = str((p.get("meta") or {}).get("location","")).lower()
        if loc == "home": home = _team_name(p)
        elif loc == "away": away = _team_name(p)
    if (not home or not away) and len(ps) >= 2:
        names = [_team_name(p) for p in ps if isinstance(p, dict)]
        if names: home = home or names[0]
        if len(names)>1: away = away or names[1]
    return home or "Home", away or "Away"

def _league(f):
    l = f.get("league") or {}
    if isinstance(l, dict):
        return l.get("name") or l.get("display_name") or l.get("short_code") or "Football"
    return "Football"

def _status(f):
    s = f.get("state") or f.get("status") or f.get("time_status") or f.get("result_info")
    if isinstance(s, dict): return s.get("name") or s.get("short_name") or "scheduled"
    return str(s or "scheduled")

def normalize_fixture(f, idx=1):
    h,a = _participants(f)
    start = f.get("starting_at") or f.get("starting_at_timestamp") or ""
    kickoff = str(start)
    if isinstance(start, int):
        try: kickoff = datetime.fromtimestamp(start, tz=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
        except Exception: kickoff = str(start)
    elif isinstance(start, str) and start:
        kickoff = start.replace("T"," ")
    return {
        "match_id": str(f.get("id") or f.get("fixture_id") or f"SM_{today_dash()}_{idx:03d}"),
        "date": today_dash(),
        "league": _league(f),
        "match_no": str(idx).zfill(3),
        "home_team": h,
        "away_team": a,
        "kickoff_kst": kickoff,
        "status": _status(f),
        "data_source": "sportmonks",
        "raw_id": f.get("id",""),
        "has_scores": bool(f.get("scores") or []),
    }

def _call_url(url, token, source_name, timeout=15):
    safe_url = _mask_url(url, token)
    try:
        res = requests.get(url, timeout=timeout)
        try:
            payload = res.json()
        except Exception:
            payload = {"text": res.text[:900]}
        data = []
        if isinstance(payload, dict):
            data = payload.get("data", [])
            if not isinstance(data, list): data = []
        elif isinstance(payload, list):
            data = payload
        info = {
            "source": source_name,
            "ok": 200 <= res.status_code < 300 and bool(data),
            "message": "수집 성공" if data else ("HTTP 성공, data 0건" if 200 <= res.status_code < 300 else f"HTTP {res.status_code}"),
            "http_status": str(res.status_code),
            "count": len(data),
            "data_count": len(data),
            "response_preview": _safe_preview(payload),
            "safe_final_url": safe_url,
            "updated_at": now_kst(),
        }
        if not (200 <= res.status_code < 300):
            return [], info
        fixtures = [normalize_fixture(x, i+1) for i,x in enumerate(data) if isinstance(x, dict)]
        info["count"] = len(fixtures)
        return fixtures, info
    except Exception as e:
        return [], {"source":source_name,"ok":False,"message":f"호출 실패: {e}","http_status":"","count":0,"data_count":0,"response_preview":"","safe_final_url":safe_url,"updated_at":now_kst()}

def fetch_sportmonks_fixtures(date_dash=None, timeout=15):
    global LAST_COLLECTION_INFO
    date_dash = date_dash or today_dash()
    token = get_token()
    if not token:
        info = {"source":"sportmonks","ok":False,"message":"SPORTMONKS_API_TOKEN 또는 SPORTS_API_KEY 없음","http_status":"","count":0,"data_count":0,"response_preview":"","safe_final_url":"","updated_at":now_kst()}
        LAST_COLLECTION_INFO = info
        return [], info
    try:
        date_url = get_date_url_template().format(today_dash=date_dash, api_key=token)
    except Exception as e:
        info = {"source":"sportmonks_date","ok":False,"message":f"URL 템플릿 format 실패: {e}","http_status":"","count":0,"data_count":0,"response_preview":"","safe_final_url":get_date_url_template(),"updated_at":now_kst()}
        LAST_COLLECTION_INFO = info
        return [], info
    fixtures, info = _call_url(date_url, token, "sportmonks_date", timeout)
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

def run_diagnostic_test():
    token = get_token()
    fixtures, info = fetch_sportmonks_fixtures(timeout=20)
    return {
        "token_detected": bool(token),
        "token_preview": token[:4] + "…" + token[-4:] if token and len(token)>8 else ("있음" if token else "없음"),
        "fixtures_count": len(fixtures),
        "info": info,
        "first_fixture": fixtures[0] if fixtures else {},
    }

def get_last_collection_info():
    return dict(LAST_COLLECTION_INFO)
