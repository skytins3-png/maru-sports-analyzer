import json
from pathlib import Path
from datetime import datetime, timezone, timedelta


KST = timezone(timedelta(hours=9))
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def log_event(event: str, data: dict | None = None):
    row = {
        "time": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST"),
        "event": event,
        "data": data or {},
    }
    path = LOG_DIR / "maru_sports.log"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
