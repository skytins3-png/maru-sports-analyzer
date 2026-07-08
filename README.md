# MARU SPORTS ANALYZER v3-auto

핵심 구조판입니다.

## 원칙
- 자료 사이트 하나 고정 금지
- 수집원별 source CSV 분리 저장
- 분석은 standard CSV만 사용
- 추천카드는 standard_upcoming_fixtures.csv의 예정 경기만 사용
- 과거 경기는 분석 근거일 뿐 추천카드 대상이 아님
- 샘플/TEST/가짜 추천카드 금지
- 자료 부족 시 자료부족/분석불가 표시
- 자동구매/자동결제 없음
- PC는 모니터링, 모바일은 추천카드 확인
- 허브/구글시트 중심 저장

## 파일 구조
- source_football_data.csv
- source_sportmonks.csv
- source_thesportsdb.csv
- source_manual.csv
- standard_history_matches.csv
- standard_upcoming_fixtures.csv
- standard_team_status.csv
- standard_injuries.csv
- standard_lineups.csv
- analysis_scores.csv
- mobile_recommendations.csv
- hub_send_logs.csv
- error_logs.csv

## football-data 자동 탐색
URL을 수동 복사하지 않습니다.
앱이 시즌 후보와 리그 후보를 만들고, 주소가 없거나 시즌이 아니면 자동으로 다음 후보로 넘어갑니다.
football-data.co.uk는 과거 결과 수집원 중 하나일 뿐입니다.

## 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Secrets
선택값:
- SPORTMONKS_API_KEY
- HUB_WEBAPP_URL
