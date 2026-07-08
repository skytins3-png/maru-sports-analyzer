# MARU SPORTS ANALYZER - Proto Fixture Hub V1

사진 2장 기준으로 재정리한 구조판입니다.

## 핵심 원칙
- 라이브스코어/토토 화면은 일정표 기준만 사용합니다.
- football-data는 과거 결과 보조 source입니다.
- Sportmonks, TheSportsDB, manual 자료는 각각 source 파일로 분리 저장합니다.
- 분석 엔진은 standard_* 파일만 읽습니다.
- 추천카드는 standard_upcoming_fixtures.csv의 예정 경기에서만 생성합니다.
- 샘플/TEST/가짜 추천카드는 생성하지 않습니다.
- 자료 부족 시 분석불가/자료부족으로 표시합니다.
- 자동구매/자동결제 기능은 없습니다.

## 파일 구조

### source
- source_livescore_fixtures.csv: 일정표 기준 경기 목록
- source_football_data.csv: football-data 과거 결과
- source_sportmonks.csv: Sportmonks 보조자료
- source_thesportsdb.csv: TheSportsDB 보조자료
- source_manual.csv: 감독/부상/라인업/이적/뉴스 메모

### standard
- standard_upcoming_fixtures.csv
- standard_history_matches.csv
- standard_team_form.csv
- standard_coaches.csv
- standard_transfers.csv
- standard_injuries.csv
- standard_lineups.csv
- standard_markets.csv

### output
- analysis_scores.csv
- mobile_recommendations.csv
- hub_send_logs.csv
- error_logs.csv

## 사용 순서
1. 일정표 탭에서 일정 CSV 저장
2. 수집원 관리에서 football-data 과거자료 자동 탐색 저장
3. 자료 입력에서 감독/부상/라인업/영입 등 manual 저장
4. 표준화/분석 탭에서 source → standard 변환
5. 승부식 분석 실행
6. 모바일 추천 확인
7. 허브/구글시트 전송

## GitHub 업로드
루트에 다음 파일을 두면 됩니다.
- app.py
- requirements.txt
- README.md
