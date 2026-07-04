import json
from pathlib import Path
from datetime import datetime, timezone, timedelta


KST = timezone(timedelta(hours=9))


class CacheManager:
    def __init__(self, base_dir="cache"):
        self.base = Path(base_dir)
        self.base.mkdir(exist_ok=True)

    def _path(self, category: str, key: str) -> Path:
        safe_key = "".join(c for c in key if c.isalnum() or c in ("-", "_")).strip()
        folder = self.base / category
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{safe_key}.json"

    def get(self, category: str, key: str, max_age_seconds: int | None = None):
        path = self._path(category, key)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if max_age_seconds is not None:
                saved_at = data.get("_saved_at")
                if saved_at:
                    dt = datetime.fromisoformat(saved_at)
                    age = (datetime.now(KST) - dt).total_seconds()
                    if age > max_age_seconds:
                        return None
            return data.get("payload", data)
        except Exception:
            return None

    def set(self, category: str, key: str, payload):
        path = self._path(category, key)
        data = {
            "_saved_at": datetime.now(KST).isoformat(),
            "payload": payload,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
