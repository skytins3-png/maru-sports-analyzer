# MARU SPORTS PROTO FIXTURE HUB v23

버전: `v23-auto-schedule-proto-match`

## 목적

형님이 일정표를 손으로 가져오지 않도록 앱이 오늘~7일 이내 자동수집 일정을 만들고, 기존 프로토 자료와 자동 매칭합니다.

## 핵심 변경

- TheSportsDB `eventsnextleague` 중심 수집을 구매용으로 쓰지 않음
- 오늘~7일 날짜 기준 `eventsday` 자동수집 추가
- 자동수집 일정은 `data/source_livescore_schedule.csv`에 저장
- 기존 프로토 자료는 `source_proto_ticket` / `source_proto_markets`를 자동 사용
- MATCHED 된 경기만 `standard_upcoming_fixtures` 생성
- MATCHED 된 경기만 분석/전체 경기판/오프라인 체크표 생성
- 8월/먼 미래 일정은 구매용/오프라인 체크표 제외
- 자동구매/자동결제 없음 유지

## 사용 흐름

1. GitHub에 v23 파일 덮어쓰기
2. Streamlit Reboot app
3. PC 앱 > 일정표 탭
4. `자동수집+매칭+분석` 실행
5. 모바일 `?mode=mobile` 접속
6. MATCHED 경기만 분석보기/오프라인 체크/허브확인 버튼 사용

## 정확한 한계

- LiveScore.com 직접 스크래핑은 아님
- TheSportsDB/Sportmonks 등 자동수집 가능 자료를 이용한 일정 매칭 구조
- 프로토 실제 경기표/배당 자료가 앱에 없으면 MATCHED 구매용 경기는 0건
- MATCHED 0건이면 오프라인 체크표를 만들지 않음
