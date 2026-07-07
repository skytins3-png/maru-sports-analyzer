from __future__ import annotations
import os
import requests
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class ApiResult:
    ok: bool
    source: str
    status: str
    data: Any
    error: str = ""

class SportsApiClient:
    def __init__(self, sports_api_key: str = "", odds_api_key: str = "", weather_api_key: str = "", timeout: int = 12):
        self.sports_api_key = sports_api_key or os.getenv("SPORTS_API_KEY", "")
        self.odds_api_key = odds_api_key or os.getenv("ODDS_API_KEY", "")
        self.weather_api_key = weather_api_key or os.getenv("WEATHER_API_KEY", "")
        self.timeout = timeout

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None, source: str = "api") -> ApiResult:
        try:
            res = requests.get(url, params=params or {}, timeout=self.timeout)
            if 200 <= res.status_code < 300:
                try:
                    data = res.json()
                except Exception:
                    data = {"text": res.text[:1000]}
                return ApiResult(True, source, f"HTTP {res.status_code}", data)
            return ApiResult(False, source, f"HTTP {res.status_code}", None, res.text[:500])
        except Exception as e:
            return ApiResult(False, source, "ERROR", None, str(e))

def mask_key(value: str) -> str:
    if not value:
        return "없음"
    if len(value) <= 8:
        return value[:2] + "****"
    return value[:4] + "…" + value[-4:]
