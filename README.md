# MARU SPORTS ANALYZER - Proto Fixture Hub V5 Backend Test

핵심 원칙:
- 라이브스코어는 일정표 기준만 사용합니다.
- 한 사이트에 의존하지 않고 source_* 원본을 분리 저장합니다.
- standard_* 변환 후 분석합니다.
- 추천카드는 예정경기 + 승부식 기준으로만 생성합니다.
- 자동구매/자동결제는 없습니다.
- 허브/구글시트가 아직 설정되지 않아도 백엔드 가상 테스트와 허브 dry-run payload 검사를 할 수 있습니다.

추가된 탭:
- 백엔드 진단
  - 현재 저장자료 진단
  - 가상 백엔드 전체 테스트
  - 부족자료 목록 확인
  - 허브 실제 전송 테스트

Streamlit Secrets 예시:
```toml
GAS_WEBAPP_URL = "https://script.google.com/macros/s/.../exec"
THESPORTSDB_API_KEY = "123"
THESPORTSDB_LEAGUE_IDS = "EPL=4328, English Championship=4329, German Bundesliga=4331"
AUTO_FIXTURE_URLS = ""
```
