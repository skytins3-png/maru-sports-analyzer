# MARU SPORTS PROTO FIXTURE HUB v11

기존 v10 기능을 빼지 않고, 구글시트 허브에 `missing_data_report`와 현재자료 상태표를 추가한 버전입니다.

## 유지 기능
- 일정표 자동수집
- 과거자료 자동수집
- source 저장
- standard 변환
- 팀폼/홈원정/상대전적 빅데이터 계산
- 승부식 분석
- 모바일 추천 생성
- 허브 payload 생성
- 구글시트 허브 전송
- payload queue 저장
- 전체 로그 ZIP 다운로드

## v11 추가 기능
- `missing_data_report.csv` 생성
- `coach_status.csv`, `injury_status.csv`, `lineup_status.csv`, `transfer_status.csv`, `news_status.csv`, `proto_market_status.csv` 생성
- 구글시트 허브에 위 상태표 전송
- 감독취임일/감독전술/주전부상/결장/예상라인업/영입이적스카우트/뉴스공지/실제 프로토 기준점 여부를 경기별로 표시

## GitHub 루트 업로드 파일
- app.py
- requirements.txt
- README.md
- google_apps_script_hub.gs
- TEST_REPORT.md
