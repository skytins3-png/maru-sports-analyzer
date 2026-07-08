# MARU SPORTS ANALYZER - PROTO FIXTURE HUB V3 ACTIONS

사진 2장 기준으로 만든 실행형 구조판입니다.

## 핵심 원칙
- 라이브스코어는 일정표 기준만 사용합니다.
- 한 사이트에 의존하지 않습니다.
- football-data는 과거자료 source 보조입니다.
- 감독 취임일, 선수 영입/스카우트, 주전 부상, 결장, 라인업, 뉴스는 manual/source 자료로 보완합니다.
- source_* 원본 저장, standard_* 표준화, analysis/mobile 출력으로 분리합니다.
- 자동구매/자동결제는 없습니다.
- 예정 경기 없으면 추천카드를 만들지 않습니다.

## 탭
- 전체실행
- PC 모니터링
- 일정표
- 승부식
- 수집원 관리
- 자료 입력
- 표준화/분석
- 모바일 추천
- 허브 전송

## 실행 버튼
- 과거자료 자동수집
- source → standard 변환
- 승부식 분석/모바일 생성
- 전체 실행

## GitHub 루트에 올릴 파일
- app.py
- requirements.txt
- README.md
