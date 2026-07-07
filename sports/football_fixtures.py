from datetime import datetime, timezone, timedelta
try:
    from sports.sportmonks_client import get_last_collection_info
except Exception:
    def get_last_collection_info():
        return {"source": "manual_only", "ok": False, "message": "Sportmonks 모듈 로드 실패", "count": 0}

KST = timezone(timedelta(hours=9))


def sample_fixtures():
    today = datetime.now(KST).strftime("%Y-%m-%d")
    return [
        {
            "match_id": f"{today}_SAFE_001",
            "date": today,
            "league": "SAFE BOOT",
            "match_no": "001",
            "home_team": "지난자료 수집 테스트",
            "away_team": "버튼으로 확인",
            "kickoff_kst": f"{today} KST",
            "status": "manual_test_required",
            "data_source": "sample_safe_boot",
            "fallback_reason": "앱 시작 시 API 자동호출 안 함",
        }
    ]


def load_sample_fixtures():
    return sample_fixtures()


def load_football_fixtures():
    return load_sample_fixtures()


def get_fixture_collection_info():
    return get_last_collection_info()
