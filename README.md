# MARU SPORTS PROTO v19

버전: `v19-ticket-matching-premium-mobile`

## 핵심 기준
- 모바일에서 실제로 보기 편한 실사용 화면
- PC는 확인/관리용
- 기존 기능 제거 없음
- 허브 저장 확인 가능
- 전체 경기마다 예상/분석/결과 확인
- 분석 이유는 숨김 처리 후 클릭하면 펼침
- 실물 프로토 승부식 티켓과 대조하기 쉬운 모바일 구조
- 오프라인 수동 구매 체크표 제공
- 자동구매/자동결제 없음

## 모바일 주소
`https://maru-sports-analyzer-lphmsfeyb47kgcrq4aevhs.streamlit.app/?mode=mobile`

## 배포 순서
1. ZIP 안 파일을 GitHub 루트에 덮어쓰기
2. 필요 시 `google_apps_script_hub.gs`를 Apps Script에 덮어쓰기
3. Apps Script 새 버전 배포: `v19 ticket matching premium mobile`
4. Streamlit Reboot app
5. PC에서 전체 실행 + 허브 저장
6. 모바일 주소로 접속해 전체 경기/분석 이유/오프라인 체크표 확인
