# MARU SPORTS ANALYZER - Football-Data.co.uk 404 URL 수정 패치

## 문제

화면에 나온 URL:
https://www.football-data.co.uk/mmz4371/2625/D1.csv

이 주소는 404가 납니다.

## 수정

Football-Data.co.uk 최신 CSV 루트를 우선 다음으로 변경합니다.

https://www.football-data.co.uk/mmz4281/2526/E0.csv

또한 사용자가 2625처럼 뒤집어 입력해도 2526을 후보로 같이 테스트합니다.

## 적용 파일

sports/free_football_data_uk.py

기존 파일을 이 파일로 교체하세요.

## 사용법

앱에서 시즌 코드에 2526 입력 후 수집 버튼을 누르세요.
