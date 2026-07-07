from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone, timedelta
from core.cache_manager import CacheManager
from core.safe_logger import log_event


KST = timezone(timedelta(hours=9))


def main():
    cache = CacheManager()
    # 실제 API 연결 전: 결과 저장 구조만 준비
    result_payload = {
        "created_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST"),
        "message": "post match result collector scaffold",
        "auto_purchase": "NO",
        "auto_payment": "NO",
    }
    cache.set("post_match", "latest_results", result_payload)
    log_event("post_match_collect", result_payload)
    print("post_match_collect ok")


if __name__ == "__main__":
    main()
