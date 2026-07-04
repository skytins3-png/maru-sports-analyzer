import requests


class SheetHub:
    """
    Google Apps Script Web App으로 데이터를 전달하는 허브.
    GAS_WEBAPP_URL이 없으면 조용히 비활성 처리한다.
    """

    def __init__(self, gas_webapp_url: str = ""):
        self.url = gas_webapp_url or ""

    def push(self, payload: dict, timeout: int = 15):
        if not self.url:
            return False, "GAS_WEBAPP_URL 미설정"

        try:
            res = requests.post(self.url, json=payload, timeout=timeout)
            if 200 <= res.status_code < 300:
                return True, "ok"
            return False, f"HTTP {res.status_code}: {res.text[:200]}"
        except Exception as e:
            return False, str(e)
