# MARU SPORTS ANALYZER - 실버전 테스트 제거 패치

## 제거한 것

- load_sample_fixtures 일반 사용 제거
- 개발자 샘플 미리보기 제거
- TEST / SAMPLE / DUMMY / FAKE / A/B/C 경기 추천 차단
- 과거자료를 추천카드 fixtures로 사용하는 구조 제거
- 앱 시작 시 Football-Data.co.uk 자동 호출 제거

## 실버전 원칙

- 실제 과거자료: cache/history_matches.csv
- 실제 예정경기: cache/upcoming_fixtures.csv
- 추천카드는 예정경기에서만 생성
- 자료 없으면 자료부족/분석불가
- 자동구매/자동결제 없음

## 적용 파일

1. app.py 교체
2. sports/free_football_data_uk.py 추가 또는 교체
