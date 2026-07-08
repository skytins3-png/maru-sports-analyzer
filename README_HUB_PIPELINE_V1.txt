# MARU SPORTS ANALYZER - Hub Pipeline V1

## 다음 단계 반영

이 버전은 단순 자료수집 앱이 아니라 다음 흐름을 갖습니다.

1. 수집
2. 사이트별 로그 저장
3. 과거자료 저장
4. 예정경기 읽기
5. 감독/선수/부상 자료 읽기
6. 분석 점수 생성
7. 모바일 추천 저장
8. Google Sheet 허브 URL이 있으면 전송

## 저장 파일

cache/source_logs.csv
cache/history_matches.csv
cache/upcoming_fixtures.csv
cache/team_status.csv
cache/analysis_scores.csv
cache/mobile_recommendations.csv

## Google Sheet 허브

Streamlit secrets에 아래 중 하나를 넣으면 자동 전송합니다.

GAS_WEBAPP_URL
gas_webapp_url
GOOGLE_SHEET_HUB_URL
sheet_hub_url

없으면 로컬 CSV 저장만 합니다.

## 적용 방법

GitHub app.py 전체를 이 ZIP의 app.py로 교체하세요.
