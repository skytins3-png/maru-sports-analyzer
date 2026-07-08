# MARU SPORTS PROTO FIXTURE HUB v8 complete test

목표: 일정표 자동수집 → 과거자료 빅데이터 매칭 → 승부식 분석 → 모바일 추천 → 허브/구글시트 전송 또는 payload 큐 저장.

## GitHub 업로드
루트에 아래 3개를 올립니다.

- `app.py`
- `requirements.txt`
- `README.md`

## Streamlit Secrets
구글시트 허브 실제 전송을 하려면 Streamlit Secrets에 아래 중 하나를 넣습니다.

```toml
GAS_WEBAPP_URL = "Apps Script 웹앱 URL"
```

또는

```toml
GOOGLE_SHEET_HUB_URL = "Apps Script 웹앱 URL"
```

URL이 없어도 앱은 `payloads/hub_payload_latest.json`, `payloads/hub_payload_queue.jsonl`에 보낼 데이터를 저장합니다.

## 기본 테스트
앱 안의 `백엔드 진단` 탭에서 `가상 백엔드 전체 테스트`를 누릅니다.

## 로그 다운로드
`PC 모니터링`, `전체실행`, `허브 전송`, `백엔드 진단` 탭에 다음 버튼이 있습니다.

- 상태 리포트 받기
- 전체 로그 ZIP 받기
- 허브 Payload 받기
- 허브 전송 로그 받기
