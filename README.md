# MARU SPORTS PROTO FIXTURE HUB v12

기존 v11 기능을 빼지 않고 유지하면서, 구글시트 허브 바로가기/설정 확인을 강화한 버전입니다.

## 유지 기능
- 일정표 자동수집
- 과거자료 자동수집
- source 저장
- standard 변환
- 팀폼/홈원정/상대전적 빅데이터 계산
- 승부식 분석
- 모바일 추천 생성
- missing_data_report / coach_status / injury_status / lineup_status / transfer_status / news_status / proto_market_status 생성
- 허브 payload 생성
- 구글시트 허브 전송
- payload queue 저장
- hub_send_logs 저장
- 전체 로그 ZIP 다운로드
- TEST_REPORT_RUNTIME 생성

## v12 추가 기능
- `GOOGLE_SHEET_URL` Secret 인식
- 앱 안에 `📊 구글시트 허브 바로가기` 버튼 표시
- 상태 리포트와 hub payload에 구글시트 바로가기 상태 포함
- Apps Script 응답에 `spreadsheet_id`, `spreadsheet_url` 포함
- Apps Script에 `hub_config` 시트 자동 생성

## Streamlit Secrets 예시
```toml
GAS_WEBAPP_URL = "https://script.google.com/macros/s/여기에_웹앱_URL/exec"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/여기에_시트_ID/edit"
```

`GAS_WEBAPP_URL`은 전송용이고, `GOOGLE_SHEET_URL`은 앱 안의 바로가기 버튼용입니다.
