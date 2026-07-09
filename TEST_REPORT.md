# v21 TEST REPORT

- version: v21-clickable-offline-ticket-mobile
- purpose: 실제 눌리는 모바일 버튼 + 오프라인 수동구매 체크 + 허브 확인
- result: PASS

- [PASS] app.py 문법 검사: 
- [PASS] 함수 중복 검사: []
- [PASS] 모바일 실제 버튼 코드 검사: []
- [PASS] 자동구매/자동결제 활성값 없음: []
- [PASS] 가상 데이터+실제 버튼 토글 테스트 1/10:  "checklist_rows": 6,
  "payload_summary": {
    "app": "MARU SPORTS PROTO FIXTURE HUB",
    "version": "v21-clickable-offline-ticket-mobile",
    "type": "v21_test",
    "analysis_rows": 60,
    "mobile_rows": 60,
    "source_fixtures": 6,
    "stan
- [PASS] 가상 데이터+실제 버튼 토글 테스트 2/10:  "checklist_rows": 6,
  "payload_summary": {
    "app": "MARU SPORTS PROTO FIXTURE HUB",
    "version": "v21-clickable-offline-ticket-mobile",
    "type": "v21_test",
    "analysis_rows": 60,
    "mobile_rows": 60,
    "source_fixtures": 6,
    "stan
- [PASS] 가상 데이터+실제 버튼 토글 테스트 3/10:  "checklist_rows": 6,
  "payload_summary": {
    "app": "MARU SPORTS PROTO FIXTURE HUB",
    "version": "v21-clickable-offline-ticket-mobile",
    "type": "v21_test",
    "analysis_rows": 60,
    "mobile_rows": 60,
    "source_fixtures": 6,
    "stan
- [PASS] 가상 데이터+실제 버튼 토글 테스트 4/10:  "checklist_rows": 6,
  "payload_summary": {
    "app": "MARU SPORTS PROTO FIXTURE HUB",
    "version": "v21-clickable-offline-ticket-mobile",
    "type": "v21_test",
    "analysis_rows": 60,
    "mobile_rows": 60,
    "source_fixtures": 6,
    "stan
- [PASS] 가상 데이터+실제 버튼 토글 테스트 5/10:  "checklist_rows": 6,
  "payload_summary": {
    "app": "MARU SPORTS PROTO FIXTURE HUB",
    "version": "v21-clickable-offline-ticket-mobile",
    "type": "v21_test",
    "analysis_rows": 60,
    "mobile_rows": 60,
    "source_fixtures": 6,
    "stan
- [PASS] 가상 데이터+실제 버튼 토글 테스트 6/10:  "checklist_rows": 6,
  "payload_summary": {
    "app": "MARU SPORTS PROTO FIXTURE HUB",
    "version": "v21-clickable-offline-ticket-mobile",
    "type": "v21_test",
    "analysis_rows": 60,
    "mobile_rows": 60,
    "source_fixtures": 6,
    "stan
- [PASS] 가상 데이터+실제 버튼 토글 테스트 7/10:  "checklist_rows": 6,
  "payload_summary": {
    "app": "MARU SPORTS PROTO FIXTURE HUB",
    "version": "v21-clickable-offline-ticket-mobile",
    "type": "v21_test",
    "analysis_rows": 60,
    "mobile_rows": 60,
    "source_fixtures": 6,
    "stan
- [PASS] 가상 데이터+실제 버튼 토글 테스트 8/10:  "checklist_rows": 6,
  "payload_summary": {
    "app": "MARU SPORTS PROTO FIXTURE HUB",
    "version": "v21-clickable-offline-ticket-mobile",
    "type": "v21_test",
    "analysis_rows": 60,
    "mobile_rows": 60,
    "source_fixtures": 6,
    "stan
- [PASS] 가상 데이터+실제 버튼 토글 테스트 9/10:  "checklist_rows": 6,
  "payload_summary": {
    "app": "MARU SPORTS PROTO FIXTURE HUB",
    "version": "v21-clickable-offline-ticket-mobile",
    "type": "v21_test",
    "analysis_rows": 60,
    "mobile_rows": 60,
    "source_fixtures": 6,
    "stan
- [PASS] 가상 데이터+실제 버튼 토글 테스트 10/10:  "checklist_rows": 6,
  "payload_summary": {
    "app": "MARU SPORTS PROTO FIXTURE HUB",
    "version": "v21-clickable-offline-ticket-mobile",
    "type": "v21_test",
    "analysis_rows": 60,
    "mobile_rows": 60,
    "source_fixtures": 6,
    "stan

## 확인한 것
- 분석보기 버튼: st.button + session_state 토글 구조 확인
- 오프라인 체크 버튼: st.button + session_state 토글 구조 확인
- 허브확인 버튼: st.button + session_state 토글 구조 확인
- 오프라인 체크박스 8개 렌더 확인
- 가상 6경기에서 60건 분석 생성 확인
- 전체 경기판 6건 생성 확인
- prediction_explain 6건 생성 확인
- offline_checklist 6건 생성 확인
- 허브 payload 구조 검사 통과
- auto_buy / auto_payment 값은 NO

## 한계
- 여기서는 Streamlit Cloud 실제 배포 URL을 직접 열어 휴대폰으로 누른 검사는 못 했습니다. 대신 fake Streamlit으로 버튼 클릭 상태와 패널 렌더링을 검증했습니다. 업로드 후 모바일에서 최종 확인해야 합니다.