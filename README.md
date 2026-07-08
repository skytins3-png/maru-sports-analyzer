# MARU SPORTS PROTO FIXTURE HUB v10

기존 v9 기능을 빼지 않고 유지하면서, 구글시트 허브 설정/검사/실제 전송 테스트 화면을 강화한 버전입니다.

## 포함 기능
- 일정표 자동수집
- football-data 과거자료 자동수집
- source 저장
- standard 변환
- 팀폼/홈원정/상대전적 빅데이터 계산
- 승부식 분석
- 모바일 추천 생성
- 허브 payload 생성
- 구글시트 허브 실제 전송/큐 저장
- 로그 ZIP 다운로드
- TEST_REPORT_RUNTIME 생성
- 구글시트 Apps Script 다운로드/설정 안내

## GitHub 업로드
루트에 아래 파일을 올리세요.

- app.py
- requirements.txt
- README.md
- google_apps_script_hub.gs
- TEST_REPORT.md

## Streamlit Secrets
```toml
GAS_WEBAPP_URL = "구글 Apps Script 웹앱 URL"
```
