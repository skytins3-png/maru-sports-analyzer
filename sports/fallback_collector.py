from __future__ import annotations
from typing import Dict, Any, List
from sports.history_store import history_summary
from sports.sportmonks_client import test_history_range

def collect_history_with_fallback(days_back: int = 7) -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = []
    sm = test_history_range(days_back, timeout=15)
    steps.append({
        "provider": "sportmonks",
        "ok": sm.get("ok", False),
        "fixtures_count": sm.get("fixtures_count", 0),
        "message": sm.get("info", {}).get("message", ""),
        "http_status": sm.get("info", {}).get("http_status", ""),
    })
    if sm.get("fixtures_count", 0) > 0:
        return {"ok": True, "source": "sportmonks", "message": "Sportmonks 자료 사용 가능", "steps": steps, "sportmonks_result": sm, "history_summary": history_summary()}
    saved = history_summary()
    if saved.get("rows", 0) > 0:
        steps.append({"provider": "local_csv_cache", "ok": True, "fixtures_count": saved.get("rows", 0), "message": "저장된 CSV 과거자료 사용", "http_status": ""})
        return {"ok": True, "source": "local_csv_cache", "message": "Sportmonks가 0건이라 저장된 CSV 자료로 대체", "steps": steps, "history_summary": saved}
    steps.append({"provider": "analysis_guard", "ok": False, "fixtures_count": 0, "message": "사용 가능한 과거자료 없음. CSV 업로드 필요.", "http_status": ""})
    return {"ok": False, "source": "none", "message": "Sportmonks 0건 + 저장된 CSV 없음 → 분석불가", "steps": steps, "history_summary": saved}
