# MARU SPORTS PROTO FIXTURE HUB v13

기존 v12 기능은 제거하지 않고 유지했습니다.

## v13 추가 내용
- Sportmonks Secret 감지
- USE_SLOW_API=Y일 때만 Sportmonks 실제 호출
- 키가 비어 있으면 호출 생략하고 앱 로딩 보호
- HTTP 상태, data 건수, participants 파싱 건수, 저장 건수 기록
- source_sportmonks.csv 저장
- source_livescore_fixtures.csv에도 Sportmonks 일정 병합
- sportmonks_status.csv 생성
- 허브 Payload와 Google Sheet에 sportmonks_status 전송
- 백엔드 진단 탭에 Sportmonks API 단독 테스트 버튼 추가

## 유지 기능
- 전체실행
- TheSportsDB 일정표 자동수집
- football-data 과거자료 자동수집
- standard 변환
- 팀폼/홈원정/상대전적 계산
- 승부식 분석
- 모바일 추천
- 허브 전송
- 구글시트 바로가기
- 부족자료 진단표
- 로그 ZIP
- 상태 리포트

## Secrets 예시
```toml
SPORTMONKS_API_TOKEN = "형님 키"
SPORTMONKS_API_KEY = "형님 키"
SPORTS_API_KEY = "형님 키"

SKYTOTO_SPORTS_API_PROVIDER = "sportmonks"
SKYTOTO_SPORTS_API_URL = "https://api.sportmonks.com/v3/football/fixtures/date/{today_dash}?api_token={api_key}&include=participants;league"
USE_SLOW_API = "Y"

GAS_WEBAPP_URL = "https://script.google.com/macros/s/웹앱주소/exec"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/구글시트ID/edit"
```

키가 없을 때는 `USE_SLOW_API = "N"` 권장.
